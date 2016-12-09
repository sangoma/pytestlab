import time
import os
import posixpath
import socket
import threading
import srvlookup
import etcd
import logging
from collections import OrderedDict


logger = logging.getLogger('pytestlab')


class ResourceLocked(Exception):
    """Attempt to lock a resource already locked by an external test session.
    """


class TooManyLocks(Exception):
    """This resource has already been locked by the current test session."""


def find_etcd_server(domain):
    assert domain, '--discovery-srv flag needs to be set'
    records = srvlookup.lookup('etcd-server', domain=domain)
    return etcd.Client(host=records[0].host, port=2379)


def get_lock_id(user=None):
    return '{}@{}'.format(user or os.environ["USER"], socket.getfqdn())


class ResourceLocker(object):
    def __init__(self, env, discovery_srv, ttl=60):
        self.env = env
        self.discovery_srv = discovery_srv
        self.etcd = find_etcd_server(discovery_srv)
        self.locks = OrderedDict()
        self.ttl = ttl

        # provision keep-alive worker
        self._stop = threading.Event()
        self._thread = None

    def acquire(self, name, user=None, timeout=None):
        """Acquire a resource lock for this test session by ``name``.
        If ``timeout`` is None, wait up to one ttl period before erroring.
        """
        key = self._makekey(name)

        # no re-entry allowed
        if key in self.locks:
            raise TooManyLocks(
                "{} has already been locked by this test session".format(
                    name))

        # check if in use
        msg = self._readkey(key)

        if msg:
            timeout = timeout if timeout is not None else msg.ttl + 1
            logger.error('{} is locked by {}, waiting {} seconds for lock '
                         'to expire...'.format(name, msg.value, timeout))
            start = time.time()
            while time.time() - start < timeout:
                msg = self._readkey(key)
                if not msg:
                    break
                time.sleep(0.5)

        if msg:
            raise ResourceLocked(
                '{} is currently locked by {}'.format(name, msg.value))

        # acquire
        lockid = get_lock_id(user)
        logger.info("{} is acquiring lock for {}".format(lockid, name))
        self.etcd.write(key, lockid, ttl=self.ttl)
        logger.debug("Locked {}:{} for {}".format(key, lockid, self.env))

        # start keep-alive
        if not self._thread or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._keepalive)
            self._thread.start()

        self.locks[key] = lockid
        return key, lockid

    def _makekey(self, name):
        return name if name in self.locks else posixpath.join(
            'lab', 'locks', name)

    def _readkey(self, key):
        try:
            return self.etcd.read(key)
        except etcd.EtcdKeyNotFound:
            return None

    def _keepalive(self):
        logger.debug("Starting keep-alive thread...")
        while not self._stop.wait(self.ttl / 2):
            for key, lockid in self.locks.items():
                logger.debug(
                    "Relocking {}:{} for {}".format(key, lockid, self.env))
                self.etcd.write(key, lockid, ttl=self.ttl)

        for key in self.locks:
            self.release(key)

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

    def is_locked(self, name):
        return self._makekey(name) in self.locks
