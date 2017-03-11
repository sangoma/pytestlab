#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys
import pytest


def monkey_patch_support_for_python2():
    from future import standard_library
    standard_library.install_aliases()

    try:
        # Monkey patch the backported ipaddress module with
        # alternative versions that accept string addresses, in
        # addition to unicode addresses, in python2 code.
        #
        # This keep compatibility simple. Slightly complicated by the
        # fact that some of these classes inherit from each other.
        import ipaddress

        def python2_compat(cls, bases=()):
            def __init__(self, address, *args, **kwargs):
                if isinstance(address, basestring):
                    address = address.decode('utf-8')
                return cls.__init__(self, address, *args, **kwargs)

            return type(cls.__name__, (cls,) + bases, {'__init__': __init__})

        ipaddress.IPv4Network = python2_compat(ipaddress.IPv4Network)
        ipaddress.IPv4Address = python2_compat(ipaddress.IPv4Address)
        ipaddress.IPv4Interface = python2_compat(ipaddress.IPv4Interface,
                                                 bases=(ipaddress.IPv4Address,))

        ipaddress.IPv6Network = python2_compat(ipaddress.IPv6Network)
        ipaddress.IPv6Address = python2_compat(ipaddress.IPv6Address)
        ipaddress.IPv6Interface = python2_compat(ipaddress.IPv6Interface,
                                                 bases=(ipaddress.IPv6Address,))
    except ImportError:
        pass


@pytest.hookimpl(hookwrapper=True)
def pytest_load_initial_conftests(early_config, parser, args):
    # Monkey patch imports for python2 before any conftests are loaded
    if sys.version_info[0] < 3:
        monkey_patch_support_for_python2()
    yield
