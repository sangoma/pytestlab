# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
# Copyright (C) 2015 Sangoma Technologies Corp.
# All Rights Reserved.

import pytest
import logging
import contextlib2
import socket
from collections import MutableMapping
import lab
from .utils import cached_property
from _pytest.runner import TerminalRepr
from .lock import EnvironmentLock


logger = logging.getLogger(__name__)


class EquipmentLookupError(LookupError):
    pass


class EnvironmentLookupError(LookupError):
    pass


def canonical_name(obj):
    """Attempt to return a sensible name for this object.
    """
    return getattr(obj, "__name__", None) or str(id(obj))


class RolesLookupErrorRepr(TerminalRepr):
    def __init__(self, filename, firstlineno, tblines, errorstring):
        self.tblines = tblines
        self.errorstring = errorstring
        self.filename = filename
        self.firstlineno = firstlineno
        self.argname = None

    def toterminal(self, tw):
        for tbline in self.tblines:
            tw.line(tbline.rstrip())
        for line in self.errorstring.split("\n"):
            tw.line("        " + line.strip(), red=True)
        tw.line()
        tw.line("%s:%d" % (self.filename, self.firstlineno + 1))


class RoleManager(object):
    def __init__(self):
        self.roles2factories = {}

    def register(self, name, factory):
        self.roles2factories[name] = factory

    def build(self, rolename, location, **kwargs):
        ctl = self.roles2factories[rolename](pytest.config, location, **kwargs)
        ctl.name = rolename
        return ctl


class Location(object):
    """A software hosting location contactable via its hostname
    """
    def __init__(self, hostname, facts):
        self.hostname = hostname
        if facts and not isinstance(facts, MutableMapping):
            raise ValueError('facts must be a mapping type')
        self.facts = facts or {}
        self.roles = {}
        self.log = logging.getLogger(hostname)

    def __repr__(self):
        return "{}(hostname={}, facts={})".format(
            type(self).__name__, self.hostname, dict(self.facts))

    def role(self, name, **kwargs):
        """Load and return the software role instance that was registered for
        `name` in the `pytest_lab_addroles` hook from this location.
        The role is cached based on the name and additional arguments.
        """
        config = pytest.config
        key = name, tuple(kwargs.items())
        try:
            return self.roles[key]
        except KeyError:
            self.log.debug("Loading {}@{}".format(name, self.hostname))

        # instantiate the registered role ctl from its factory
        role = pytest.rolemanager.build(name, self, **kwargs)
        role._key = key
        self.roles[key] = role

        # register sw role controllers as pytest plugins
        config.pluginmanager.register(
            role, name="{}@{}".format(name, self.hostname)
        )

        # XXX I propose we change this name to pytest_lab_ctl_loaded
        # much like pytest's pytest_plugin_registered
        config.hook.pytest_lab_role_created.call_historic(
            kwargs=dict(config=config, ctl=role)
        )
        return role

    def _close_role(self, role):
        config = pytest.config
        config.hook.pytest_lab_role_destroyed(config=config, ctl=role)
        try:
            role.close()
        except AttributeError:
            pass
        pytest.env.config.pluginmanager.unregister(plugin=role)

    def destroy(self, role):
        role = self.roles.pop(role._key, None)
        if role:
            self._close_role(role)

    def cleanup(self):
        for role in self.roles.itervalues():
            self._close_role(role)

    @cached_property
    def addrinfo(self):
        'addr info according to a dns lookup.'
        def query_dns(family):
            try:
                info = socket.getaddrinfo(self.hostname, 0, family,
                                          socket.SOCK_STREAM, 0,
                                          socket.AI_ADDRCONFIG)
            except socket.gaierror as e:
                self.log.warning(
                    "Failed to resolve {0} on {2}: {1}".format(
                        self.hostname, e, {socket.AF_INET: 'ipv4',
                                           socket.AF_INET6: 'ipv6'}[family]
                    )
                )
                return None
            return info[0][4][0]

        def lookup():
            for family in (socket.AF_INET, socket.AF_INET6):
                addr = query_dns(family)
                if addr:
                    yield family, addr

        return dict(lookup())

    @cached_property
    def ip_addr(self):
        'ipv4 addr info according to a dns lookup.'
        return self.addrinfo.get(socket.AF_INET)

    @cached_property
    def ip6_addr(self):
        'ipv6 addr info according to a dns lookup.'
        return self.addrinfo.get(socket.AF_INET6)


class EnvManager(object):
    def __init__(self, config):
        self.config = config
        self.name = config.option.env

        if self.name == 'mock':
            providers = []
        else:
            providers = lab.load_backends(None)

        self.env = lab.Environment(self.name, providers)
        self.lock = None

        # TODO: need something more robust
        if self.name != 'mock':
            if not self.env.view:
                raise EnvironmentLookupError()

        # XXX a hack to get a completely isolated setup for now
        if providers and providers[0] == 'files':
            self.lock = EnvironmentLock.aquire(config.option.user,
                                               config.option.env,
                                               config.option.discovery_srv,
                                               config.option.wait_on_lock)

        config.hook.pytest_lab_addroles.call_historic(
            kwargs=dict(config=self.config, rolemanager=pytest.rolemanager)
        )

        # local cache
        self.locations = {}

    def manage(self, hostname, facts=None):
        """Manage a new software hosting location by `hostname`.
        `facts` is an optional dictionary of data.
        """
        try:
            location = self.locations[hostname]
        except KeyError:
            location = Location(hostname, facts)
            self.locations[hostname] = location
        else:
            if dict(location.facts) != facts:
                location.facts.update(facts)

        return location

    def __getitem__(self, rolename):
        """Return all locations hosting a role with ``rolename`` in a list.
        """
        equipment = self.env.get(rolename)
        if not equipment:
            raise EquipmentLookupError("Equipment {} not found"
                                       .format(rolename))

        # NOTE: for equipment models their `name` should be a hostname
        return [self.manage(eq.name, facts=eq) for eq in equipment]

    def find(self, rolename):
        """Lookup and return a list of all role instance ctls registered with
        ``rolename`` from all equipment in the test environment.
        """
        locations = self[rolename]
        return [loc.role(rolename) for loc in locations]

    def find_one(self, rolename):
        """Find and return the first role instance registered with ``rolename``
        in the test environment.
        """
        return self.find(rolename)[0]

    def cleanup(self):
        try:
            for location in self.locations.itervalues():
                location.cleanup()
        finally:
            if self.lock:
                self.lock.release()


def pytest_namespace():
    return {'env': None,
            'rolemanager': RoleManager(),
            'EquipmentLookupError': EquipmentLookupError}


def pytest_addhooks(pluginmanager):
    from . import hookspec
    pluginmanager.add_hookspecs(hookspec)


def pytest_addoption(parser):
    group = parser.getgroup('environment')
    group.addoption('--env', action='store', required=True,
                    help='Test environment name')
    group.addoption('--user', action='store',
                    help='Explicit user to lock the test environment with')
    group.addoption('--wait-on-lock', action='store_true',
                    help='Tell pytest to wait for dut to unlock')


def pytest_configure(config):
    pytest.env = EnvManager(config)
    config.pluginmanager.register(pytest.env, 'environment')
    config.add_cleanup(pytest.env.cleanup)


@pytest.fixture(scope='session')
def dut_host(dut_ctl):
    'Retreive the hostname str for the current dut'
    host = dut_ctl.hostname
    assert host
    return host


@pytest.fixture(scope='session')
def dut_ip(dut_ctl, addr_family):
    return dut_ctl.addrinfo[addr_family]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    excinfo = call.excinfo
    if excinfo:
        exc = excinfo.value or 'Model not found'
        if call.excinfo and call.excinfo.errisinstance(EnvironmentLookupError):
            rep.longrepr = RolesLookupErrorRepr('foo.py', 0, [], exc.message)
        elif call.excinfo and call.excinfo.errisinstance(EquipmentLookupError):
            rep.longrepr = RolesLookupErrorRepr('foo.py', 0, [], exc.message)
