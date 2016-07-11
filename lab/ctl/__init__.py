"""
Built-in software role controllers.
"""
from sangoma.ssh import get_ssh, get_sftp


class SSHMixin(object):
    """Provides `plumbum` remote SSH and paramiko SFTP connections as
    properties. Expected to be mixed with the base `Controller`.
    """
    @property
    def ssh(self):
        if not getattr(self, '_ssh', None) or not self._ssh._session.alive():
            self._ssh = get_ssh(self._equipment())
        return self._ssh

    @property
    def sftp(self):
        if not getattr(self, '_sftp', None) or not self._sftp.get_channel().active:
            self._sftp = get_sftp(self._equipment())
        return self._sftp
