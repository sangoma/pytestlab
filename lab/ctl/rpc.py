#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
RPC controls
"""
from builtins import object
import pytest
from ..comms import connection
from rpyc.utils.zerodeploy import DeployedServer


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

    def get_pymods(self, modnames, venvpath=None):
        """Return a dict of ``rpyc`` proxied python modules by name.

        Any pre-existing ``rpyc`` connection for ``venvpath`` will be used.
        """
        mods = {}
        # if venvpath is not None:
        # this adds a ref to the new rpyc conn
        rpyc = self._venvs2rpycs.get(venvpath)
        if not rpyc:
            rpyc = self.get_rpyc(venvpath=venvpath)
            self._venvs2rpycs[venvpath] = rpyc

        for name in modnames:
            # getattr triggers an import
            mods[name] = getattr(rpyc.modules, name)

        return mods

    def get_pymod(self, modname, venvpath=None):
        """Return an ``rpyc`` proxied python modules by name.
        """
        return self.get_pymods([modname], venvpath=venvpath)[modname]


@pytest.hookimpl
def pytest_lab_addroles(rolemanager):
    rolemanager.register('rpyc', RPyCCtl)
