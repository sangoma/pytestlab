"""
Networking utility functions.
These should be as minimal as possible to enable remote execution.
"""
import errno
import logging
import socket
import itertools
import contextlib

try:
    # for RPC via execnet this module may not be installed at the far end (py2)
    import ipaddress

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
        return ipaddress.ip_address(addr).version

    def check_ipaddr(dst, version=4):
        '''
        Receive a hostname or IP address string and return a validated
        IP and fqdn if either can be found
        '''
        family = version_to_family(version)
        for res in socket.getaddrinfo(dst, 0, family, socket.SOCK_STREAM, 0,
                                      socket.AI_PASSIVE | socket.AI_CANONNAME):
            family, socktype, proto, canonname, sa = res
            try:
                addr = ipaddress.ip_address(unicode(sa[0]))
            except NameError:
                addr = ipaddress.ip_address(sa[0])
            return addr, canonname

    def iter_addrs(data):
        for ipaddr in data['ipaddr']:
            yield ipaddress.ip_interface('{}/{}'.format(*ipaddr))

except ImportError:
    logging.getLogger('lab.network.utils').warning(
        "Some network utils are not available; no `ipaddress` could be found")


def version_to_family(version):
    if version == 4:
        return socket.AF_INET
    elif version == 6:
        return socket.AF_INET6
    return ValueError("Version isn't either 4 or 6")


def get_sock_addr(host, port=0, family=None, version=None, sockmod=socket):
    '''Get and return free socket address from the system.

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


# legacy alias
get_new_sock = get_sock_addr


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
