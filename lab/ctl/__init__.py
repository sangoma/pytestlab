"""
Built-in software role controllers.
"""
from ..comms import connection


class SSHMixin(object):
    """Provides `plumbum` remote SSH and paramiko SFTP connections as
    properties. Expected to be mixed with the base `Controller`.
    """
    def __init__(self, config, location, **kwargs):
        super(SSHMixin, self).__init__(config, location, **kwargs)

    ssh = connection('ssh')
    sftp = connection('sftp')
