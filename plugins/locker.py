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


SRV = namedtuple('SRV', ['host', 'port', 'priority', 'weight'])

logger = logging.getLogger(__name__)


class SRVQueryFailure(Exception):
    """Exception that is raised when the DNS query has failed."""
    def __str__(self):
        return 'SRV query failure: %s' % self.args[0]


def _build_resource_to_address_map(answer):
    """Return a dictionary that maps resource name to address.
    The response from any DNS query is a list of answer records and
    a list of additional records that may be useful.  In the case of
    SRV queries, the answer section contains SRV records which contain
    the service weighting information and a DNS resource name which
    requires further resolution.  The additional records segment may
    contain A records for the resources.  This function collects them
    into a dictionary that maps resource name to an array of addresses.
    :rtype: dict
    """
    mapping = defaultdict(list)
    for resource in answer.response.additional:
        target = resource.name.to_text()
        mapping[target].extend(record.address
                               for record in resource.items
                               if record.rdtype == rdatatype.A)
    return mapping


def _build_result_set(answer):
    """Return a list of SRV instances for a DNS answer.
    :rtype: list of srvlookup.SRV
    """
    resource_map = _build_resource_to_address_map(answer)
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

    results = _build_result_set(answer)
    return sorted(results, key=lambda r: (r.priority, -r.weight, r.host))


def connect_to_etcd(discovery_srv):
    err = None
    for record in query_etcd_server(discovery_srv):
        try:
            return etcd.Client(host=record.host, port=2379)
        except Exception as _:
            err = _

    if err:
        raise err
    raise RuntimeError("What happened?")


class EtcdLocker(object):
    def __init__(self, discovery_srv):
        self.etcd = connect_to_etcd(discovery_srv)
        self.locks = dict()

    def _makekey(self, name):
        return name if name in self.locks else posixpath.join('lab', 'locks', name)

    def read(self, key):
        try:
            return self.etcd.read(key)
        except etcd.EtcdKeyNotFound:
            return None

    def release(self, name):
        key = self._makekey(name) if name not in self.locks else name
        lockid = self.locks.pop(key, None)
        # only release a lock if we own it
        if lockid:
            logger.info("{} is releasing lock for {}".format(lockid, name))
            try:
                self.etcd.delete(key)
            except etcd.EtcdKeyNotFound:
                pass

    def release_all(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join()

    def test(self, name):
        return self._makekey(name) in self.locks



def get_lock_id(user=None):
    return '@'.join((user or os.environ.get("USER", "anonymous"),
                     socket.getfqdn()))


class Locker(object):
    def __init__(self, config):
        self.config = config
        self.locker = EtcdLocker('qa.sangoma.local')

    def lock(self, name, user=None, timeout=None):
        """Acquire a resource lock for this test session by ``name``.
        If ``timeout`` is None, wait up to one ttl period before erroring.
        """
        key = self.locker._makekey(name)

        # no re-entry allowed
        if key in self.locker.locks:
            raise TooManyLocks(
                "{} has already been locked by this test session".format(
                    name))

        # check if in use
        msg = self.locker.read(key)

        if msg:
            timeout = timeout if timeout is not None else msg.ttl + 1
            logger.error('{} is locked by {}, waiting {} seconds for lock '
                         'to expire...'.format(name, msg.value, timeout))
            start = time.time()
            while time.time() - start < timeout:
                msg = self.locker.read(key)
                if not msg:
                    break
                time.sleep(0.5)

        if msg:
            raise ResourceLocked(
                '{} is currently locked by {}'.format(name, msg.value))

        # acquire
        lockid = get_lock_id(user)
        logger.info("{} is acquiring lock for {}".format(lockid, name))
        self.locker.etcd.write(key, lockid, ttl=180)  # self.ttl?
        logger.debug("Locked {}:{}".format(key, lockid))

        # start keep-alive
        if not self._thread or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._keepalive)
            self._thread.start()

        self.locks[key] = lockid
        return key, lockid


@pytest.hookimpl
def pytest_namespace():
    etcd = EtcdLocker('qa.sangoma.local')
    return {'locker': Locker(etcd)}


@pytest.hookimpl
def pytest_configure(config):
    pytest.locker.config = config


@pytest.hookimpl
def pytest_lab_lock(config, identifier):
    pytest.log.info("ATTEMPTING TO LOCK {}".format(identifier))
    pytest.locker.lock(identifier)
