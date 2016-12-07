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


class EnvironmentLocked(Exception):
    pass


def find_etcd_server(domain):
    assert domain, '--discovery-srv flag needs to be set'
    records = srvlookup.lookup('etcd-server', domain=domain)
    return etcd.Client(host=records[0].host, port=2379)


class ResourceLocker(object):
    def __init__(self, env, discovery_srv, ttl=60):
        self.env = env
        self.etcd = find_etcd_server(discovery_srv)
        # self.envpath = posixpath.join('lab', env, 'lock')
        self.locks = OrderedDict()
        self.ttl = ttl

        # provision keep-alive worker
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._worker)

    def acquire(self, path, wait=True, user=None):
        # check if in use
        msg = self._readkey(self._makekey(path))
        if wait and msg:
            logger.error('{} is locked by {}, waiting {} seconds for lock '
                         'to expire...'.format(path, msg.value, msg.ttl))
            time.sleep(msg.ttl + 1)

        msg = self._readkey(self._makekey(path))
        if msg:
            raise EnvironmentLocked(
                '{} is currently locked by {}'.format(path, msg.value))

        # acquire
        key = self._makekey(path)
        lockid = '{}@{}'.format(user or os.environ["USER"], socket.getfqdn())
        self.etcd.write(key, lockid, ttl=self.ttl)
        logger.debug("Locked {}:{} for {}".format(key, lockid, self.env))

        # start keep-alive
        if not self._thread.is_alive():
            self._thread.start()

        self.locks[key] = lockid
        return path, lockid

    def _makekey(self, path):
        return posixpath.join('lab', 'locks', path)

    def _readkey(self, key):
        try:
            return self.etcd.read(key)
        except etcd.EtcdKeyNotFound:
            return None

    def _worker(self):
        logger.debug("Starting keep-alive thread...")
        while not self._stop.wait(self.ttl / 2):
            for key, lockid in self.locks.items():
                logger.debug(
                    "Relocking {}:{} for {}".format(key, lockid, self.env))
                self.etcd.write(key, lockid, ttl=self.ttl)

        for key in self.locks:
            self.release(key)

    def release(self, path):
        key = self._makekey(path) if path not in self.locks else path
        self.locks.pop(key)
        try:
            self.etcd.delete(key)
        except etcd.EtcdKeyNotFound:
            pass

    def release_all(self):
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join()

    def is_locked(self, path):
        return self._makekey(path) in self.locks
