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


class EtcdProvider(object):
    name = 'etcd'

    def __init__(self, *path, **kwargs):
        domain = kwargs.get('domain', None)
        if not domain:
            raise RuntimeError('No discovery domain specified')

        self.path = posixpath.join('lab', 'sangoma', 'v1', *path)
        try:
            records = srvlookup.lookup('etcd-server', domain=domain)
        except srvlookup.SRVQueryFailure as e:
            raise ProviderError("Failed to find etcd-server SRV record")

        try:
            self.client = etcd.Client(host=records[0].host, port=2379)
            self.result = self.client.read(self.path)
        except etcd.EtcdKeyNotFound as e:
            self.result = None
        except etcd.EtcdException as e:
            raise ProviderError("Failed to connect to etcd: {}".format(e))

    @property
    def data(self):
        return self.result.value if self.result else None

    def push(self, data):
        if self.result:
            self.result.value = data
            self.client.update(self.result)
        else:
            self.client.write(self.path, data)
