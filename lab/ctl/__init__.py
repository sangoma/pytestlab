#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Built-in software role controllers.
"""
from builtins import object
from ..comms import connection


class SSHMixin(object):
    """Provides `plumbum` remote SSH and paramiko SFTP connections as
    properties. Expected to be mixed with the base `Controller`.
    """
    def __init__(self, config, location, **kwargs):
        super(SSHMixin, self).__init__(config, location, **kwargs)

    ssh = connection('ssh')
    sftp = connection('sftp')
