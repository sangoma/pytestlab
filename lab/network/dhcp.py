#
# Copyright 2017 Sangoma Technologies Inc.
#
from builtins import object
import time
import select
import logging
import threading
from pyroute2 import dhcp
from pyroute2.dhcp.dhcp4msg import dhcp4msg
from pyroute2.dhcp.dhcp4socket import DHCP4Socket


logger = logging.getLogger(__name__)

DHCP_PARAMS = [1, 3, 6, 12, 15, 28]


class DHCP(object):
    def __init__(self, iface):
        self.iface = iface
        self.yiaddr = None

        self.sock = DHCP4Socket(self.iface.ifname)
        self.poll = select.poll()
        self.poll.register(self.sock, select.POLLIN | select.POLLPRI)

        self._ready_event = threading.Event()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._lease)
        self._thread.daemon = True
        self._thread.start()
        if not self._ready_event.wait(10.0):
            raise RuntimeError('Failed to get DHCP lease')

        logger.info('Setting {} on {}...'.format(self.yiaddr,
                                                 self.iface.ifname))
        self.iface.add_ip(self.yiaddr, mask=self.subnet_mask)
        self.iface.commit()

    def close(self):
        self._stop_event.set()
        self._send(dhcp.BOOTREQUEST,
                   {'message_type': dhcp.DHCPRELEASE,
                    'requested_ip': self.yiaddr,
                    'server_id': self.server_id,
                    'parameter_list': DHCP_PARAMS})

    def _lease(self):
        logger.info('Sending DHCPDISCOVER on {}...'.format(self.iface.ifname))
        reply = self._send(dhcp.BOOTREQUEST,
                           {'message_type': dhcp.DHCPDISCOVER,
                            'parameter_list': DHCP_PARAMS},
                           expect=dhcp.DHCPOFFER)

        self.server_id = reply['options']['server_id']
        self.yiaddr = reply['yiaddr']

        while True:
            logger.info('Sending DHCPREQUEST on {}...'
                        .format(self.iface.ifname))

            reply = self._send(dhcp.BOOTREQUEST,
                               {'message_type': dhcp.DHCPREQUEST,
                                'requested_ip': self.yiaddr,
                                'server_id': self.server_id,
                                'parameter_list': DHCP_PARAMS},
                               expect=dhcp.DHCPACK)

            self.server_id = reply['options']['server_id']
            self.yiaddr = reply['yiaddr']
            self.subnet_mask = reply['options']['subnet_mask']

            self._ready_event.set()
            lease_time = reply['secs']

            # If there's either no leasetime, or the stop event has
            # been set before our renew timeout, renew our lease
            if not lease_time:
                logger.debug('No lease time on DHCP lease!')
                return
            elif self._stop_event.wait(lease_time // 2):
                logger.debug('Leaving DHCP renewal loop!')
                return

    def _send(self, op, options, expect=None, timeout=2):
        msg = dhcp4msg({
            'op': op,
            'chaddr': self.sock.l2addr,
            'options': options
        })

        if not expect:
            self.sock.put(msg)
            return

        start = time.time()
        while time.time() - start <= timeout:
            xid = self.sock.put(msg)['xid']

            for fd, _ in self.poll.poll(timeout):
                assert fd == self.sock.fileno()

                response = self.sock.get()
                if response['xid'] != xid:
                    continue
                if response['options']['message_type'] != expect:
                    raise RuntimeError('DHCP protocol error')
                return response
            time.sleep(0.5)
        else:
            raise RuntimeError('Failed to acquire dhcp lease')
