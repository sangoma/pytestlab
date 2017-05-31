import time
import threading
import os
import posixpath
import socket
import pytest
import etcd
import logging
from collections import namedtuple, OrderedDict, defaultdict
from dns import rdatatype, resolver


SRV = namedtuple('SRV', 'host,port,priority,weight')

logger = logging.getLogger(__name__)


class ResourceLocked(Exception):
    """Attempt to lock a resource already locked by an external test session.
    """


class SRVQueryFailure(Exception):
    """Exception that is raised when the DNS query has failed."""
    def __str__(self):
        return 'SRV query failure: {}'.format(self.args[0])


def build_result_set(answer):
    resource_map = defaultdict(list)
    for resource in answer.response.additional:
        target = resource.name.to_text()
        resource_map[target].extend(record.address
                                    for record in resource.items
                                    if record.rdtype == rdatatype.A)

    for resource in answer:
        target = resource.target.to_text()
        if target in resource_map:
            for address in resource_map[target]:
                yield SRV(address, resource.port, resource.priority,
                          resource.weight)
        else:
            yield SRV(target.rstrip('.'), resource.port, resource.priority,
                      resource.weight)


def query_etcd_server(discovery_srv):
    fqdn = '.'.join(('_etcd-server', '_tcp', discovery_srv))

    try:
        answer = resolver.query(fqdn, 'SRV')
    except (resolver.NoAnswer,
            resolver.NoNameservers,
            resolver.NotAbsolute,
            resolver.NoRootSOA,
            resolver.NXDOMAIN) as error:
        raise SRVQueryFailure(error.__class__.__name__)

    return sorted(build_result_set(answer),
                  key=lambda r: (r.priority, -r.weight, r.host))


def find_etcd(discovery_srv):
    err = None
    for record in query_etcd_server(discovery_srv):
        try:
            return etcd.Client(host=record.host, port=2379)
        except Exception as _:
            err = _

    if err:
        raise err
    raise RuntimeError("What happened?")


def makekey(name):
    return posixpath.join('lab', 'locks', name)


def get_lock_id(user=None):
    return '@'.join((user or os.environ.get("USER", "anonymous"),
                     socket.getfqdn()))


class EtcdLocker(object):
    Lock = namedtuple('Lock', 'key,data,ttl')

    def __init__(self, discovery_srv):
        self.etcd = find_etcd(discovery_srv)
        self.locks = {}

    def read(self, key):
        try:
            return self.etcd.read(makekey(key))
        except etcd.EtcdKeyNotFound:
            return None

    def write(self, key, ttl, **data):
        lock = self.Lock(makekey(key), data, ttl)

        self.etcd.write(lock.key, lock.data, ttl=lock.ttl, prevexists=False)
        self.locks[key] = lock

    def refresh(self, key):
        lock = self.locks[key]
        self.etcd.write(lock.key, lock.data, ttl=lock.ttl, refresh=True)

    def release(self, key):
        lock = self.locks.pop(key)
        try:
            self.etcd.delete(lock.key)
        except etcd.EtcdKeyNotFound:
            pass


class Locker(object):
    def __init__(self, config, backend, ttl=30):
        self.config = config
        self.backend = backend
        self.ttl = ttl
        self._thread = None
        self._stop = threading.Event()

    def aquire(self, key, user=None):
        record = self.backend.read(key)

        if record and record.ttl:
            logger.error('{} is locked by {}, waiting {} seconds for lock '
                         'to expire...'.format(key, record.value, record.ttl + 1))
            start = time.time()
            while time.time() - start < record.ttl + 1:
                record = self.backend.read(key)
                if not record:
                    break
                time.sleep(0.5)

        if record:
            raise ResourceLocked(
                '{} is currently locked by {}'.format(key, record.value))

        # acquire
        lockid = get_lock_id(user)
        logger.info("{} is acquiring lock for {}".format(lockid, key))
        self.backend.write(key, self.ttl, id=lockid)
        logger.debug("Locked {}:{}".format(key, lockid))

        # start keep-alive
        if not self._thread or not self._thread.is_alive():
            def keepalive_worker():
                while not self._stop.wait(self.ttl // 2):
                    for key in list(self.backend.locks):
                        logger.debug("Relocking {}".format(key))
                        self.backend.refresh(key)

            self._thread = threading.Thread(target=keepalive_worker)
            logger.critical("Starting keep-alive thread...")
            self._thread.start()

        return key, lockid

    def release(self, key):
        self.backend.relaese(key)

    def release_all(self):
        self._stop.set()
        for key in list(self.backend.locks):
            self.backend.release(key)

    @pytest.hookimpl
    def pytest_unconfigure(self, config):
        self.release_all()

    @pytest.hookimpl
    def pytest_lab_aquire_lock(self, config, identifier):
        self.aquire(identifier)
        return True

    @pytest.hookimpl
    def pytest_lab_release_lock(self, config, identifier):
        self.release(identifier)
        return True


@pytest.hookimpl
def pytest_configure(config):
    etcd = EtcdLocker('qa.sangoma.local')
    config.pluginmanager.register(Locker(config, etcd))
