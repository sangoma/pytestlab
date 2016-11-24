# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright (C) 2013  Sangoma Technologies Corp.
# All Rights Reserved.
#
# Author(s)
# Tyler Goodlet <tgoodlet@sangoma.com>
# Travis Semczyszyn <tsemczyszyn@sangoma.com>
#
# This code is Sangoma Technologies Confidential Property.
# Use of and access to this code is covered by a previously executed
# non-disclosure agreement between Sangoma Technologies and the Recipient.
# This code is being supplied for evaluation purposes only and is not to be
# used for any other purpose.

"""
This module contains the following networkng helpers:

- ip address generator for the localhost
- best route calculator
"""
import ipaddress
import errno
import socket
import itertools
import contextlib
import pyroute2
import pyroute2.iproute
import plumbum
from ping import ping_cmds

# re-exports
from .macvlan import MacVLan


def version_to_family(version):
    if version == 4:
        return socket.AF_INET
    elif version == 6:
        return socket.AF_INET6
    return ValueError("Version isn't either 4 or 6")


def resolver(host, version=4):
    '''A simple resolver interface

    Parameters
    ----------
    host : str, hostname to look up
    version : int, IP version number (default: 4)

    Returns
    -------
    ip : str, ip address of the given hostname
    '''
    return check_ipaddr(host, version)[0].compressed


def get_addr_version(addr):
    '''Check the IP version of a given address

    Paramaters
    ----------
    addr : str, IP address (version 4 or 6)

    Returns
    -------
    version : Int, the IP version (4 or 6)
    '''
    return ipaddress.ip_address(addr.decode('utf-8')).version


def check_ipaddr(dst, version=4):
    '''
    Receive a hostname or IP address string and return a validated
    IP and fqdn if either can be found
    '''
    family = version_to_family(version)
    for res in socket.getaddrinfo(dst, 0, family, socket.SOCK_STREAM, 0,
                                  socket.AI_PASSIVE | socket.AI_CANONNAME):
        family, socktype, proto, canonname, sa = res
        addr = ipaddress.ip_address(sa[0].decode('utf-8'))
        return addr, canonname.decode('utf-8')


def iter_addrs(data):
    for ipaddr in data['ipaddr']:
        yield ipaddress.ip_interface(u'{}/{}'.format(*ipaddr))


def ip_ifaces(version=4):
    '''return the list of ips corresponding to each NIC'''
    with pyroute2.IPDB() as ipdb:
        for ifname, data in ipdb.by_name.items():
            for addr in iter_addrs(data):
                if addr.version == version and not addr.is_link_local:
                    yield ifname, addr


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
    dst_host = check_ipaddr(dst_host, version=version)[0]
    family = version_to_family(version)

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

        for addr in iter_addrs(interface):
            if addr.version == version and not addr.is_link_local:
                return interface['ifname'], addr.ip


# FIXME: should really be get_sock_address
def get_new_sock(host, port=0, family=None, version=None, sockmod=socket):
    '''
    Get and return free socket address from the system.

    Parameters
    ----------
    host : string
        hostname or ip for which a socket addr is needed
    port : int, optional
        port number to bind. default is to request a random port from
        the system.
    sockmod: module
        local or remote (i.e. via rpyc) python built-in `socket` module
        implementation

    Returns
    -------
    ip, port[, s] : string, int [, socket instance]
    '''

    if not family:
        family = version_to_family(version) if version else socket.AF_UNSPEC

    err = None
    for res in sockmod.getaddrinfo(host, port, family, socket.SOCK_DGRAM, 0,
                                   socket.AI_PASSIVE):
        family, socktype, proto, _, sa = res
        sock = None
        try:
            sock = sockmod.socket(family, socktype, proto)
            with contextlib.closing(sock):
                sock.bind(sa)
                return sock.getsockname()[:2]
        except socket.error as _:
            err = _
            sock = None

    if err is not None:
        raise err
    raise socket.error("getaddrinfo returns an empty list")


# use a range recommended here:
# http://www.cs.columbia.edu/~hgs/rtp/faq.html#ports
_rtp_port_gen = itertools.cycle(range(16382, 32767, 4))


def new_rtp_socket(host, version=4):
    '''
    Get and return free socket address from the system in the rtp
    range 16382 <= port < 32767.

    Parameters
    ----------
    host : string
        hostname or ip for which a socket addr is needed

    Returns
    -------
    ip, port : string, int

    Notes
    -----
    Due to common usage with SIPp (which uses every rtp port
    and that port + 2) we have the rule that we skip forward
    by two on evey second call since N+2, (N+1)+2, will be
    already taken up and the next available will be (N+1)+2+1
    '''
    err = None
    for _ in range(5):
        try:
            return get_new_sock(
                host, port=next(_rtp_port_gen), version=version)
        except socket.error as e:
            # If we failed to bind, lets try again. Otherwise reraise
            # the error immediately as its something much more serious.
            if e.errno != errno.EADDRINUSE:
                raise
            err = e
    raise err


def ping(addr):
    '''
    Ping an IPv4 address

    Parameters
    ----------
    addr : str, IPv4 or v6  address you want to ping in dotted decimal
    '''
    ping = ping_cmds[get_addr_version(addr)]
    try:
        print(ping('-c', '1', addr, timeout=1))
    except (plumbum.ProcessExecutionError, plumbum.ProcessTimedOut):
        return False
    return True
