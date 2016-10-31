"""
Built-in software role controllers.
"""
from ..comms import connection
from rpyc.utils.zerodeploy import DeployedServer


class SSHMixin(object):
    """Provides `plumbum` remote SSH and paramiko SFTP connections as
    properties. Expected to be mixed with the base `Controller`.
    """
    def __init__(self, config, location, **kwargs):
        super(SSHMixin, self).__init__(config, location, **kwargs)

    ssh = connection('ssh')
    sftp = connection('sftp')


class RPyCMixin(SSHMixin):
    """Provides ``rpyc`` connection factory methods as well as a cached master
    connection.
    """
    def __init__(self, config, location, **kwargs):
        super(RPyCMixin, self).__init__(config, location, **kwargs)
        self._venvs2rpycs = {}
        self._ssh2zdservers = {}

    def close(self):
        super(SSHMixin, self).close()
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
