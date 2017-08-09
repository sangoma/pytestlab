#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import plumbum


# More recent versions iputils merged the two ping commands. Attempt to
# support both the older and newer versions
try:
    _ping = plumbum.local['ping']
except plumbum.CommandNotFound:
    ping_cmds = {}
else:
    try:
        _ping6 = plumbum.local['ping6']
        _ping4 = _ping
    except plumbum.CommandNotFound:
        _ping6 = _ping['-6']
        _ping4 = _ping['-4']

    ping_cmds = {4: _ping4, 6: _ping6}
