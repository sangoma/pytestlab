#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from builtins import object
import time
import select
import socket
import fcntl
import struct
import logging
import threading
import ipaddress
import errno
import pnet
from pnet import udphdr, ethhdr, ip4hdr, dhcp4
from pnet.bpf import attach_filter
from pnet.dhcp4 import DHCPPacket, DHCPMessage, DHCPOption, DHCPOpCode, bootp_filter


SIOCGIFHWADDR = 0x8927

logger = logging.getLogger(__name__)


def get_ifreq(sock, ifname):
    ifreq = struct.pack('256s', ifname.encode('ascii')[:15])
    return fcntl.ioctl(sock.fileno(), SIOCGIFHWADDR, ifreq)


def generate_packet(src, data):
    min_size = ethhdr.min_size + ip4hdr.min_size + udphdr.min_size
    packet = bytearray(len(data) + min_size)

    eth = ethhdr({'src': src,
                  'dst': pnet.HWAddress(u'ff:ff:ff:ff:ff:ff'),
                  'type': pnet.ETH_P_IP},
                 buf=packet)

    ip4 = ip4hdr({'dst': ipaddress.IPv4Address(u'255.255.255.255'),
                  'proto': socket.IPPROTO_UDP,
                  'len': len(data) + ip4hdr.min_size + udphdr.min_size},
                 buf=eth.payload)

    udp = udphdr({'sport': 68,
                  'dport': 67,
                  'len': len(data) + udphdr.min_size},
                 buf=ip4.payload)

    udp['csum'] = pnet.ipv4_checksum(ip4, udp, data)
    udp.payload = data
    return packet


class DHCP4Socket(object):
    def __init__(self, ifname):
        self.ifname = ifname
        self.poll = select.epoll()
        self.sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW,
                                  socket.htons(pnet.ETH_P_ALL))
        self.poll.register(self.sock, select.POLLIN | select.POLLPRI |
                           select.POLLHUP | select.POLLERR)
        attach_filter(self.sock, bootp_filter())
        self.sock.setblocking(0)
        self.sock.bind((ifname, 3))

        ifreq = get_ifreq(self.sock, ifname)
        self.src = pnet.HWAddress(ifreq[18:24])

    def send(self, packet, src=None, expect=None, interval=2, retry=3,
             timeout=10):
        src = src or self.src
        msg = generate_packet(src, packet.tobytes())

        if not expect:
            self.sock.send(msg)
            return

        def recv_all():
            while True:
                try:
                    payload, addr = self.sock.recvfrom(0x1000)
                    eth = ethhdr.parse(payload)
                    ip4 = ip4hdr.parse(eth.payload)
                    udp = udphdr.parse(ip4.payload)
                    reply = DHCPPacket.parse(udp.payload)
                except socket.error as e:
                    if e.errno != errno.EAGAIN:
                        raise e
                    return None
                except pnet.ParseError:
                    continue

                if reply.xid != packet.xid:
                    continue
                elif reply.message_type != expect:
                    raise RuntimeError('DHCP protocol error')
                return reply

        starttime = time.time()
        for _ in range(retry - 1):
            self.sock.send(msg)

            loop_starttime = time.time()
            waitfor = interval
            while waitfor > 0:
                for fd, _ in self.poll.poll(waitfor):
                    assert fd == self.sock.fileno()
                    reply = recv_all()
                    if reply:
                        return reply

                waitfor -= time.time() - loop_starttime

        waitfor = timeout - (time.time() - starttime)
        if waitfor > 0:
            self.sock.send(msg)

            for fd, _ in self.poll.poll(waitfor):
                assert fd == self.sock.fileno()
                return recv_all()

        raise RuntimeError('Failed to acquire dhcp lease')


def build_options(message_type, chaddr, requested_ip=None,
                  hostname=None, vendor=None):
    if not hostname:
        hostname = socket.gethostname()
    if not vendor:
        vendor = dhcp4.get_vendor_info()

    common = [
        (DHCPOption.DHCPMessageType, [message_type]),
        (DHCPOption.ClientIdentifier, dhcp4.get_client_id(chaddr)),
        (DHCPOption.MaximumDHCPMessageSize, [0x05, 0xc0]),
        (DHCPOption.VendorClassIdentifier, vendor.encode('ascii')),
        (DHCPOption.HostName, hostname.encode('ascii')),
        (DHCPOption.ParameterRequestList, [
            DHCPOption.SubnetMask,
            DHCPOption.Router,
            DHCPOption.IPAddressLeaseTime,
            DHCPOption.ServerIdentifier,
            DHCPOption.RenewalTimeValue,
            DHCPOption.RebindingTimeValue,
        ])
    ]

    if requested_ip:
        if isinstance(requested_ip, ipaddress.IPv4Address):
            requested_ip = requested_ip.packed
        common.append((DHCPOption.RequestedIPAddress, requested_ip))

    return common


class DHCP4(object):
    def __init__(self, iface):
        self.iface = iface
        self.sock = DHCP4Socket(iface.ifname)

        self._yiaddr = None
        self._subnet_mask = None
        self._ready_event = threading.Event()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._lease)
        self._thread.daemon = True
        self._thread.start()
        if not self._ready_event.wait(10.0):
            raise RuntimeError('Failed to get DHCP lease')

        logger.info('Setting {} on {}...'.format(self.yiaddr,
                                                 self.iface.ifname))
        self.iface.add_ip(self.yiaddr.compressed,
                          mask=self.subnet_mask.compressed)
        self.iface.commit()

    def _discover(self, src=None):
        logger.info('Sending DHCP4 discover on {}...'.format(self.iface.ifname))
        chaddr = src or self.sock.src
        options = build_options(DHCPMessage.Discover, chaddr)
        packet = DHCPPacket(DHCPOpCode.Request, chaddr=chaddr, options=options)
        return self.sock.send(packet, src=src, expect=DHCPMessage.Offer)

    def _request(self, yiaddr, src=None):
        logger.info('Sending DHCP4 request on {}...'.format(self.iface.ifname))
        chaddr = src or self.sock.src
        options = build_options(DHCPMessage.Request, chaddr, requested_ip=yiaddr)
        packet = DHCPPacket(DHCPOpCode.Request, chaddr=chaddr, options=options)
        return self.sock.send(packet, src=src, expect=DHCPMessage.ACK)

    def _release(self, yiaddr, src=None):
        logger.info('Sending DHCP4 release on {}...'.format(self.iface.ifname))
        chaddr = src or self.sock.src
        options = build_options(DHCPMessage.Release, chaddr, requested_ip=yiaddr)
        packet = DHCPPacket(DHCPOpCode.Request, chaddr=chaddr, options=options)
        self.sock.send(packet, src=src)

    def _lease(self):
        offer = self._discover()
        self._yiaddr = offer.yiaddr

        while True:
            reply = self._request(self._yiaddr)
            options = dict(reply.options)

            self._yiaddr = reply.yiaddr
            self._subnet_mask = options[DHCPOption.SubnetMask].tobytes()
            self._ready_event.set()

            # TODO: fix
            lease_time = reply.secs

            # If there's either no leasetime, or the stop event has
            # been set before our renew timeout, renew our lease
            if not lease_time:
                logger.debug('No lease time on DHCP lease!')
                return
            elif self._stop_event.wait(lease_time // 2):
                logger.debug('Leaving DHCP renewal loop!')
                return

    def close(self):
        self._stop_event.set()
        self._release(self._yiaddr)

    @property
    def yiaddr(self):
        return ipaddress.IPv4Address(self._yiaddr)

    @property
    def subnet_mask(self):
        return ipaddress.IPv4Address(self._subnet_mask)
