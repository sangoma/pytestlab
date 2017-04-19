#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
This module contains the following networkng helpers:

- ip address generator for the localhost
- best route calculator
"""
from __future__ import print_function
from __future__ import absolute_import
from builtins import str
from builtins import next
from builtins import range
import pyroute2
import pyroute2.iproute
import plumbum
from .ping import ping_cmds
from . import utils
from .utils import *

# re-exports
from pyroute2 import NetlinkError
from .macvlan import MacVLan


def find_best_route(dst_host, dev_list=None, version=4):
    '''
    Return the best IP and interface in a 'IpDevice' named tuple
    Use in order to reach a given destination IP

    Parameters
    ----------
    dst_host : string
        hostname or ip for which a socket addr is needed
    dev_list : list of strings, optional
        list of interface names to consider
    version : int, optional
        version number of IP protocol to use. Useful when providing
        a hostname as the dst_host to enforce IP version.

    Returns
    -------
    ifacename, ipaddr: tuple of (<interface name>, <ipaddr>)
    '''
    dst_host = utils.check_ipaddr(dst_host, version=version)[0]
    family = utils.version_to_family(version)

    RT_TABLE_MAIN = 254

    with pyroute2.IPDB() as ipdb:
        # We have to do it manually for now because the ipdb.routes API
        # to too buggy at the moment.
        routes = ipdb.nl.get_routes(family=family, dst=str(dst_host),
                                    table=RT_TABLE_MAIN)

        try:
            route = routes[0]
        except IndexError:
            raise RuntimeError('No suitable route found')

        rta_oif = route.get_attr('RTA_OIF')
        interface = ipdb.interfaces[rta_oif]

        for addr in utils.iter_addrs(interface):
            if addr.version == version and not addr.is_link_local:
                return interface['ifname'], addr.ip


def ip_ifaces(version=4):
    '''return the list of ips corresponding to each NIC'''
    with pyroute2.IPDB() as ipdb:
        for ifname, data in ipdb.by_name.items():
            for addr in utils.iter_addrs(data):
                if addr.version == version and not addr.is_link_local:
                    yield ifname, addr


def ping(addr):
    '''
    Ping an IPv4 address

    Parameters
    ----------
    addr : str, IPv4 or v6  address you want to ping in dotted decimal
    '''
    ping = ping_cmds[utils.get_addr_version(addr)]
    try:
        print(ping('-c', '1', addr, timeout=1))
    except (plumbum.ProcessExecutionError, plumbum.ProcessTimedOut):
        return False
    return True
