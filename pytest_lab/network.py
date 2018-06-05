#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
High level networking helpers
"""
from builtins import next
from builtins import zip
from builtins import range
import socket
import errno
import pytest
import contextlib2
from lab import network
from pytest_lab.roles import RoleNotFound


@pytest.fixture(scope='session')
def best_route(dut_host, ip_ver):
    return network.find_best_route(dut_host, version=ip_ver)


@pytest.fixture(scope='session')
def primary_iface(best_route):
    'return the local net iface with the best route to the dut'
    return best_route[0]


@pytest.fixture(scope='session')
def src_ip(best_route):
    'return the local net iface with the best route to the dut'
    return best_route[1].compressed


@pytest.fixture(scope='session')
def addr_family(request, dut_ctl):
    '''The address family to determine the mode - ipv4 or ipv6 - to run
    tests under'''
    if request.param == socket.AF_INET6:
        if socket.AF_INET6 not in dut_ctl.addrinfo:
            pytest.fail("IPv6 mode not supported on DUT")
        elif not next(network.ip_ifaces(version=6), None):
            pytest.fail("No IPv6 interfaces configured")

    return request.param


@pytest.fixture(scope='session')
def ip_ver(addr_family):
    '''Convenience for functions that need 4 or 6'''
    if addr_family == socket.AF_INET:
        return 4
    else:
        return 6


def vlan_handle_error(err):
    '''Error handler for vlan creation failure, for friendlier error
    messages.'''
    if err.code == errno.EINVAL:
        pytest.skip('Primary interface does not support creating '
                    'macvlans, are you trying to connect over a VPN?')
    raise err


@pytest.fixture(scope='class')
def vlan(primary_iface):
    '''Create a macvlan device'''
    try:
        with network.MacVLan(primary_iface) as vlan:
            yield vlan
    except network.NetlinkError as err:
        vlan_handle_error(err)


@pytest.fixture
def vlan_set(primary_iface):
    "constructor to create a variable set of macvlan interfaces"

    with contextlib2.ExitStack() as stack:
        def inner(count):
            try:
                return [stack.enter_context(network.MacVLan(primary_iface))
                        for _ in range(count)]
            except network.NetlinkError as err:
                vlan_handle_error(err)

        yield inner


@pytest.fixture(scope='class')
def vlan_addr(vlan, addr_family):
    '''Return the correct ip address for the macvlan interface'''
    return vlan.get_address(addr_family)[0].compressed


@pytest.fixture(scope='class')
def vlan_mask(vlan, addr_family):
    '''Return the correct network mask for the macvlan interface'''
    return vlan.get_address(addr_family)[1]
