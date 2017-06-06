#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from builtins import object
import importlib
import pytest
from lab import config_v1


class RoleNotFound(LookupError):
    pass


class Roles(object):
    def __init__(self, config):
        self.config = config
        self.data = None
        self.loaded = {}

        self.config.hook.pytest_lab_map.call_historic(
            kwargs=dict(config=self.config, roles=self)
        )

    def load(self, config, zone=None):
        self.data = config_v1.Union(config, zone=zone)

    def enumerate(self, keys):
        try:
            for key in keys:
                result = self.loaded.get(key)
                if result:
                    yield result
        except TypeError:
            result = self.loaded.get(keys)
            if result:
                yield result

    def get(self, key, default=None):
        self.loaded.get(key, default)

    def aquire(self, key):
        if not self.data:
            raise RoleNotFound(key)

        role = self.loaded.get(key)
        if not role:
            roledata = next(self.data[key].itervalues())
            role = self.config.hook.pytest_lab_load_role(
                config=self.config,
                identifier=roledata.key,
                facts=roledata.kwargs
            )

            role.name = key  # XXX: backwards compatability hack
            self.loaded[key] = role

            self.config.hook.pytest_lab_role_created.call_historic(
                kwargs=dict(config=self.config, name=key, role=role)
            )
        return role

    def __delitem__(self, key):
        assert self.data
        del self.loaded[key]

    @pytest.hookimpl
    def pytest_namespace(self):
        return {'roles': self,
                'RoleNotFound': RoleNotFound}

    @pytest.hookimpl
    def pytest_lab_load_role(self, config, identifier, facts):
        modulepath, _, factory = identifier.rpartition('.')

        try:
            module = importlib.import_module(modulepath)
        except ImportError:
            return

        virtual = getattr(module, '__virtual__', None)
        if virtual:
            virtual()

        lock = getattr(module, '__lock__', None)
        if lock:
            lock_identifier = lock(factory, **facts)
            config.hook.pytest_lab_aquire_lock(config=config,
                                               identifier=lock_identifier)

        pytest.log.info('Loading {}'.format(identifier))
        return getattr(module, factory)(**facts)


class Dispatcher(object):
    def __init__(self, config):
        self.config = config

    def __getitem__(self, key):
        return self.config.hook.pytest_lab_dispatch(config=self.config, identifier=key)

    @pytest.hookimpl
    def pytest_namespace(self):
        return {'dispatch': self}

    @pytest.hookimpl
    def pytest_lab_dispatch(self, config, identifier):
        try:
            modulepath, _, factory = identifier.rpartition('.')
            module = importlib.import_module(modulepath)
            return getattr(module, factory)
        except ImportError:
            pass


@pytest.hookimpl
def pytest_addhooks(pluginmanager):
    from . import hookspec
    pluginmanager.add_hookspecs(hookspec)


@pytest.hookimpl
def pytest_configure(config):
    config.pluginmanager.register(Roles(config))
    config.pluginmanager.register(Dispatcher(config))


@pytest.fixture(scope='session')
def dut_host(dut_ctl):
    'Retreive the hostname str for the current dut'
    host = dut_ctl.hostname
    assert host
    return host


@pytest.fixture(scope='session')
def dut_ip(dut_ctl, addr_family):
    return dut_ctl.addrinfo[addr_family]
