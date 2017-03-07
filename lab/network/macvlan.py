#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from builtins import range
from builtins import object
import time
import logging
import socket
import ipaddress
import pyroute2
from .dhcp import DHCP


logger = logging.getLogger(__name__)


def _generate_device_name(prefix):
    with pyroute2.IPDB() as ipdb:
        for idx in range(100):
            name = '{}{}'.format(prefix, idx)
            if name not in ipdb.interfaces:
                return name
        raise RuntimeError('Unable to allocate a {} interface'.format(prefix))


class MacVLan(object):
    """
    The **macvlan** module is useful for giving a second MAC address to
    a network adaptor while having the kernel see it as a new and
    separate device at the higher levels. Useful for pretending you are
    multiple machines.

    The :py:class:`MacVLan` module encapsulates the creation of macvlan
    network devices and the acquisition of an IP over DHCP (the module
    will transparently start a backgrounded `dhcpcd` process). The
    `dhcpcd` invocation will block until an IP is acquired so users of
    this library should be able to rely on an IP being set.

    A context manager is provided for convenience and is the recommended
    way to use this library::

        with MacVLan('eno1', name='test-network', mac='00:19:d1:29:d2:58') as vlan:
            ...

    Will create a new mavlan called ``test-network`` bound to ``eno1`` using
    the provided mac. It will also try and aquire an IP over DHCP.::

        31: test-network@eno1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default
            link/ether 9e:dc:e3:d6:1e:ad brd ff:ff:ff:ff:ff:ff
            inet6 fe80::9cdc:e3ff:fed6:1ead/64 scope link tentative dadfailed
               valid_lft forever preferred_lft forever
    """
    def __init__(self, interface, name='macvlan', dhcp=True):
        self.name = _generate_device_name(name)
        self.dhcp = None

        self.ipdb = pyroute2.IPDB()
        vlan = self.ipdb.create(kind='macvlan',
                                link=self.ipdb.interfaces[interface],
                                ifname=self.name,
                                mode='bridge')
        vlan.up()
        vlan.commit()

        # Start dhcp process if necessary
        if dhcp:
            try:
                self.dhcp = DHCP(vlan)
            except RuntimeError:
                self.close()
                raise

    @property
    def addresses(self):
        """Obtain information about the macvlan to determin its addresses."""
        data = {}

        ipaddrs = self.ipdb.interfaces[self.name].ipaddr
        for addr, prefix in ipaddrs:
            addr = ipaddress.ip_address(addr.decode('utf-8'))
            if addr.is_link_local:
                continue
            elif addr.version == 4:
                data.setdefault(socket.AF_INET, []).append(addr)
            elif addr.version == 6:
                data.setdefault(socket.AF_INET6, []).append(addr)

        return data

    def get_address(self, family, timeout=10):
        start = time.time()
        while time.time() - start <= timeout:
            # If we don't have an address listed first, its likely
            # because SLAAC and DAD haven't completed yet, lets try
            # again in a bit
            addrs = self.addresses.get(family, None)
            if addrs:
                return addrs[0]
            time.sleep(1)

        family_name = 'ipv4' if family == socket.AF_INET else 'ipv6'
        raise RuntimeError("Failed to get find a suitable {} address for "
                           "the macvlan".format(family_name))

    @property
    def exists(self):
        return self.ipdb and self.name in self.ipdb.interfaces

    def close(self):
        """Delete the macvlan.

        Generally, using the context manager is preferable to having to
        call this manually.
        """
        if self.dhcp:
            self.dhcp.close()
            self.dhcp = None

        if self.ipdb:
            if self.exists:
                try:
                    iface = self.ipdb.interfaces[self.name]
                    if iface.get('ipdb_scope') != 'create':
                        iface.remove().commit()
                except KeyError:
                    pass

            self.ipdb.release()
            self.ipdb = None

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_val, trace):
        if not exception_type:
            self.close()
