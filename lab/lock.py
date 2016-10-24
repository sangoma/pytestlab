import pytest
import time
import os
import posixpath
import socket
import threading
import srvlookup
import etcd


class EnvironmentLocked(Exception):
    pass


def find_etcd_server(domain):
    assert domain, '--discovery-srv flag needs to be set'
    records = srvlookup.lookup('etcd-server', domain=domain)
    return etcd.Client(host=records[0].host, port=2379)


class EnvironmentLock(threading.Thread):
    def __init__(self, env, domain, lockmsg, wait=False, ttl=60):
        self.etcd = find_etcd_server(domain)
        self.lockpath = posixpath.join('sangoma', 'lab', env, 'lock')

        msg = self._readkey()
        while msg:
            pytest.log.error('{} is locked by {}, waiting {} seconds for lock '
                             'to expire...'.format(env, msg.value, msg.ttl))
            time.sleep(msg.ttl + 1)
            msg = self._readkey()
            if msg and not wait:
                raise EnvironmentLocked('{} is currently locked '
                                        'by {}'.format(env, msg.value))

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._worker,
                                        args=(lockmsg, ttl))
        self._thread.start()

    def _readkey(self):
        try:
            return self.etcd.read(self.lockpath)
        except etcd.EtcdKeyNotFound:
            return None

    def _worker(self, lockmsg, ttl):
        self.etcd.write(self.lockpath, lockmsg, ttl=ttl)
        while not self._stop.wait(ttl / 2):
            self.etcd.write(self.lockpath, lockmsg, ttl=ttl)

        try:
            self.etcd.delete(self.lockpath)
        except etcd.EtcdKeyNotFound:
            pass

    def release(self):
        self._stop.set()
        self._thread.join()

    @classmethod
    def aquire(cls, user, env, discovery_srv, wait):
        lockmsg = '{}@{}'.format(user or os.environ["USER"], socket.getfqdn())
        return cls(env, discovery_srv, lockmsg, wait)
