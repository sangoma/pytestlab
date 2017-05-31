#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from builtins import object
import importlib
import pytest
from lab import utils, config_v1


class Data(object):
    def __init__(self):
        self.rootdir = '.'

    def find(self, *filenames):
        _, result, _ = utils.getcfg([self.rootdir], filenames)
        return result


class Roles(object):
    def __init__(self):
        self.data = None
        self.loaded = {}
        self.config = None

    def load(self, config, zone=None):
        self.data = config_v1.Union(config, zone=zone)

    def __getitem__(self, key):
        if not self.data:
            self.config.hook.pytest_lab_map.call_historic(
                kwargs=dict(config=self.config, roles=self)
            )

        if not self.data:
            raise KeyError(key)

        role = self.loaded.get(key)
        if not role:
            roledata = next(self.data[key].itervalues())
            role = self.config.hook.pytest_lab_load_role(config=self.config, identifier=roledata.key, facts=roledata.kwargs)
            role.name = key  # XXX: backwards compatability hack
            self.loaded[key] = role

            self.config.hook.pytest_lab_role_created.call_historic(
                kwargs=dict(config=self.config, name=key, role=role)
            )
        return role

    def __delitem__(self, key):
        assert self.data
        del self.loaded[key]


class Dispatcher(object):
    def __getitem__(self, key):
        return self.config.hook.pytest_lab_dispatch(config=self.config, identifier=key)


@pytest.hookimpl
def pytest_namespace():
    return {'roles': Roles(),
            'dispatch': Dispatcher(),
            'data': Data()}


@pytest.hookimpl
def pytest_addhooks(pluginmanager):
    from . import hookspec
    pluginmanager.add_hookspecs(hookspec)


@pytest.hookimpl
def pytest_addoption(parser):
    group = parser.getgroup('environment')
    group.addoption('--env', action='store')
    group.addoption('--zone', action='store')


@pytest.hookimpl
def pytest_load_initial_conftests(early_config, parser, args):
    rootdir = utils.get_common_ancestor(args)
    pytest.data.rootdir = rootdir


@pytest.hookimpl
def pytest_configure(config):
    pytest.dispatch.config = config
    pytest.roles.config = config


def pytest_lab_map(config, roles):
    labconfig = pytest.data.find('lab2.yaml')
    if not labconfig:
        return

    environments, zones = config_v1.load(labconfig)
    envname = config.getoption('--env')
    zonename = config.getoption('--zone')

    environment = environments.get(envname, {})

    if not zonename:
        env_zones = environment.get('zones')
        if env_zones:
            zonename = env_zones[0]

    zone = zones.get(zonename, {})

    roles.load(
        environment.get('roles', {}),
        zone.get('roles', {})
    )


@pytest.hookimpl
def pytest_lab_load_role(config, identifier, facts):
    modulepath, _, factory = identifier.rpartition('.')

    try:
        module = importlib.import_module(modulepath)
    except ImportError:
        return

    __virtual__ = getattr(module, '__virtual__', None)
    if __virtual__:
        __virtual__()

    __lock__ = getattr(module, '__lock__', None)
    if __lock__:
        lock_identifier = __lock__(**facts)
        config.hook.pytest_lab_aquire_lock(config=config, identifier=lock_identifier)


    pytest.log.info('Loading {}'.format(identifier))
    return getattr(module, factory)(**facts)


@pytest.hookimpl
def pytest_lab_dispatch(config, identifier):
    try:
        modulepath, _, factory = identifier.rpartition('.')
        module = importlib.import_module(modulepath)
        return getattr(module, factory)
    except ImportError:
        pass


@pytest.fixture(scope='session')
def dut_host(dut_ctl):
    'Retreive the hostname str for the current dut'
    host = dut_ctl.hostname
    assert host
    return host


@pytest.fixture(scope='session')
def dut_ip(dut_ctl, addr_family):
    return dut_ctl.addrinfo[addr_family]
