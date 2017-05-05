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
from builtins import object
import os
import string
import py
import py.path


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


def exists(path, ignore=EnvironmentError):
    try:
        return path.check()
    except ignore:
        return False


def get_common_ancestor(args):
    # args are what we get after early command line parsing (usually
    # strings, but can be py.path.local objects as well)
    common_ancestor = None
    for arg in args:
        if str(arg)[0] == "-":
            continue
        p = py.path.local(arg)
        if common_ancestor is None:
            common_ancestor = p
        else:
            if p.relto(common_ancestor) or p == common_ancestor:
                continue
            elif common_ancestor.relto(p):
                common_ancestor = p
            else:
                shared = p.common(common_ancestor)
                if shared is not None:
                    common_ancestor = shared
    if common_ancestor is None:
        common_ancestor = py.path.local()
    elif not common_ancestor.isdir():
        common_ancestor = common_ancestor.dirpath()
    return common_ancestor


def getcfg(args, inibasenames):
    args = [x for x in args if not str(x).startswith("-")]
    if not args:
        args = [py.path.local()]
    for arg in args:
        arg = py.path.local(arg)
        for base in arg.parts(reverse=True):
            for inibasename in inibasenames:
                p = base.join(inibasename)
                if exists(p):
                    #iniconfig = LabConfig(p)
                    return base, p, {}
    return None, None, None
