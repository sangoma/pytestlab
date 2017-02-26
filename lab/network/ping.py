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
    ping_cmds = {4: plumbum.local['ping'],
                 6: plumbum.local['ping6']}
except plumbum.CommandNotFound:
    ping_cmds = {4: plumbum.local['ping']['-4'],
                 6: plumbum.local['ping']['-6']}
