#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
RPC controls
"""
import inspect
import importlib
from builtins import object
from contextlib import contextmanager
import pytest
from ..comms import connection
from rpyc.utils.zerodeploy import DeployedServer
import execnet


class RPyCCtl(object):
    """Per location ``rpyc`` control.
    Offers connection factory methods as well as a cached master connection.
    """
    ssh = connection('ssh')

    def __init__(self, config, location, venvpath=None, **kwargs):
        self.config = config
        self.location = location
        self.venvpath = venvpath  # the default
        self._venvs2rpycs = {}
        self._ssh2zdservers = {}

    def close(self):
        for conn in self._venvs2rpycs.values():
            conn.close()

    def get_rpyc(self, venvpath=None, pythonpath=None, ssh=None):
        """Return a new ``rpyc`` classic connection to the Python interpreter
        found at ``pythonpath`` or the virtualenv at ``venvpath``.
        """
        # last place we look is for a class attr
        venvpath = venvpath or self.location.facts.get('venvpath', getattr(
            self, 'venvpath', None))
        if venvpath and pythonpath is None:
            pythonpath = self.ssh.path(venvpath).join('bin/python/')

        ssh = ssh or self.ssh
        server = self._ssh2zdservers.get(ssh)
        if not server:
            server = DeployedServer(ssh, python_executable=pythonpath)
            self._ssh2zdservers[ssh] = server

        conn = server.classic_connect()

        # need this ref otherwise the server will tear down
        conn._zero_deploy_server = server
        return conn

    def from_venvpath(self, venvpath):
        conn = self._venvs2rpycs.get(venvpath)
        if not conn:
            conn = self.get_rpyc(venvpath=venvpath)
            # this adds a ref to the new rpyc conn
            self._venvs2rpycs[venvpath] = conn
        return conn

    @contextmanager
    def splitbrain(self, venvpath=None, conn=None):
        from rpyc.experimental.splitbrain import (splitbrain,
                                                  disable_splitbrain)
        conn = conn or self.from_venvpath(venvpath)
        with splitbrain(conn):
            yield
        disable_splitbrain()

    def get_pymods(self, modnames, venvpath=None):
        """Return a dict of ``rpyc`` proxied python modules by name.

        Any pre-existing ``rpyc`` connection for ``venvpath`` will be used.
        """
        mods = {}
        rpyc = self.from_venvpath(venvpath)
        for name in modnames:
            # getattr triggers an import
            mods[name] = getattr(rpyc.modules, name)

        return mods

    def get_pymod(self, modname, venvpath=None):
        """Return an ``rpyc`` proxied python modules by name.
        """
        return self.get_pymods([modname], venvpath=venvpath)[modname]


REMOTE_EXEC_CHECK = "if __name__ == '__channelexec__':"


class Execnet(object):
    def __init__(self, config, location, **kwargs):
        self.config = config
        self.location = location
        self.gw = self.from_location(location)
        self._modsrc = {}

    def makespec(self, location):
        # build gw spec
        spec = {}
        spec['id'] = "@".join((self.__class__.__name__, location.hostname))
        # ssh spec
        facts = location.facts
        user = facts.get('user', facts.get('login', 'root'))
        sshspec = "{user}@{hostname}".format(user=user,
                                             hostname=location.hostname)
        keyfile = facts.get('keyfile')
        if keyfile:
            sshspec = "-i {} ".format(keyfile) + sshspec
        elif facts.get('password'):
            raise NotImplementedError("No execnet-ssh password support yet")
        spec['ssh'] = sshspec
        return spec

    def from_location(self, location):
        return self.from_specdict(self.makespec(location))

    def from_specdict(self, spec):
        return execnet.makegateway('//'.join(
            "=".join((key, val)) for key, val in spec.items())
        )

    def exec(self, expr):
        """Remote execute code at this location and return a channel instance
        """
        return self.gw.remote_exec(expr)

    def _get_mod_src(self, module):
        modpath = module.__name__
        try:
            return self._modsrc[modpath]
        except KeyError:
            src = inspect.getsource(module)
            self._modsrc[modpath] = src
            return src

    def invoke(self, func, **kwargs):
        """Invoke a locally defined function at the remote location.

        The function's containing module's source is collected and transferred
        to the remote system and the function is invoked in that module
        namespace.
        """
        modpath = func.__module__
        module = importlib.import_module(modpath)
        src = self._get_mod_src(module)
        # append func call a end of module source
        invoke_line = " "*4 + "channel.send({}({}))".format(
            func.__name__, ', '.join(
                ("{}={}".format(k, repr(v)) for k, v in kwargs.items())))
        channel = self.gw.remote_exec(
            src + REMOTE_EXEC_CHECK + invoke_line)
        return channel.receive()


@pytest.hookimpl
def pytest_lab_addroles(rolemanager):
    rolemanager.register('rpyc', RPyCCtl)
    rolemanager.register('execnet', Execnet)
