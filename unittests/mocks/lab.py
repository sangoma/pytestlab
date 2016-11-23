from __future__ import absolute_import
import json


class Record(object):
    def __init__(self, mockdata, *path):
        self.data = mockdata

    def push(self, data):
        self.data = data

    def asdict(self):
        return self.data


class MockProvider(object):
    name = 'mock'

    def __init__(self, config):
        self.mockdata = config['mockdata']

    @classmethod
    def mock(cls, mockdata):
        return cls({'mockdata': mockdata})

    def get(self, *path):
        return Record(self.mockdata, *path)

    def asdict(self):
        return self.mockdata
