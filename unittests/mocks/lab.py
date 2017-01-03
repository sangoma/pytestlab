from __future__ import absolute_import
from builtins import object
import sys
import pytest


pytest_plugins = ['lab']


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

    def get(self, *path, **kwargs):
        return Record(self.mockdata, *path)

    def asdict(self):
        return dict(self.mockdata)


_mock_provider = MockProvider.mock({
    'dut': [
        'dut.example.com'
    ],
    'example': [
        'example1.example.com',
        'example2.example.com'
    ]
})


class ProviderPlugin:
    @pytest.hookimpl
    def pytest_lab_add_providers(self, config, providermanager):
        providermanager.add('mock', MockProvider)
        return 'mock', {'mockdata': _mock_provider.asdict()}


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Always register a mock provider plugin as soon as possible.
    """
    config.pluginmanager.register(ProviderPlugin())


@pytest.fixture
def mock_provider():
    """Emulate an env provider backend.
    """
    return _mock_provider.mock(_mock_provider.asdict())


@pytest.fixture
def testplugin():
    """This plugin module.
    """
    return sys.modules[__name__]
