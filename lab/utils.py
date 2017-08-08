#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Handy utilities
"""
from builtins import map
import os
import string


PATTERN = string.ascii_letters + string.digits + '_' + '.'


def encode_char(c):
    if c == os.sep:
        return '-'
    if c in PATTERN:
        return c
    return '\\x{:x}'.format(ord(c))


def encode_path(path):
    """Encode paths for use as file names the same way systemd does:

      "Some unit names reflect paths existing in the file system namespace.
      Example: a device unit dev-sda.device refers to a device with the
      device node /dev/sda in the file system namespace. If this applies, a
      special way to escape the path name is used, so that the result is
      usable as part of a filename. Basically, given a path, "/" is
      replaced by "-", and all other characters which are not ASCII
      alphanumerics are replaced by C-style "\x2d" escapes (except that "_"
      is never replaced and "." is only replaced when it would be the first
      character in the escaped path). The root directory "/" is encoded as
      single dash, while otherwise the initial and ending "/" are removed
      from all paths during transformation. This escaping is reversible."
    """
    # strip any initial/ending '/'
    name = path.strip('/') if len(path) > 1 else path
    name = ''.join(map(encode_char, name))
    if name[0] == '.':
        name = '\\x{:x}'.format(ord('.')) + name[1:]
    return name
