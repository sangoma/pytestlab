from __future__ import absolute_import

import posixpath
import srvlookup
import etcd
from .common import ProviderError


def connect(domain):
    try:
        records = srvlookup.lookup('etcd-server', domain=domain)
    except srvlookup.SRVQueryFailure as e:
        raise RuntimeError("Failed to find etcd-server SRV record")

    try:
        return etcd.Client(host=records[0].host, port=2379)
    except etcd.EtcdException as e:
        raise RuntimeError("Failed to connect to etcd: {}".format(e))


class Record(object):
    def __init__(self, client, *path):
        self.client = client
        self.path = posixpath.join('lab', 'sangoma', 'v1', *path)

        try:
            self.result = self.client.read(self.path)
        except etcd.EtcdKeyNotFound:
            self.result = None

    @property
    def data(self):
        return self.result.value if self.result else None

    def push(self, data):
        if self.result:
            self.result.value = data
            self.client.update(self.result)
        else:
            self.client.write(self.path, data)


class EtcdProvider(object):
    name = 'etcd'

    def __init__(self, config):
        domain = config.get('discovery-srv', None)
        if not domain:
            raise RuntimeError('No discovery domain specified')

        try:
            records = srvlookup.lookup('etcd-server', domain=domain)
        except srvlookup.SRVQueryFailure as e:
            raise ProviderError("Failed to find etcd-server SRV record")

        try:
            self.client = etcd.Client(host=records[0].host, port=2379)
        except etcd.EtcdException as e:
            raise ProviderError("Failed to connect to etcd: {}".format(e))

    def get(self, *path):
        return Record(self.client, *path)
