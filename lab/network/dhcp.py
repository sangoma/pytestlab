import time
import select
import logging
from pyroute2 import dhcp
from pyroute2.dhcp.dhcp4msg import dhcp4msg
from pyroute2.dhcp.dhcp4socket import DHCP4Socket


logger = logging.getLogger(__name__)


class DHCP(object):
    DHCP_PARAMS = [1, 3, 6, 12, 15, 28]

    def __init__(self, ifname):
        self.sock = DHCP4Socket(ifname)
        self.poll = select.poll()
        self.poll.register(self.sock, select.POLLIN | select.POLLPRI)

        logger.info('Sending DHCPDISCOVER...')
        reply = self.send(dhcp.BOOTREQUEST,
                          {'message_type': dhcp.DHCPDISCOVER,
                           'parameter_list': self.DHCP_PARAMS},
                          expect=dhcp.DHCPOFFER)

        self.server_id = reply['options']['server_id']
        self.yiaddr = reply['yiaddr']

    def send(self, op, options, expect, timeout=2):
        msg = dhcp4msg({
            'op': op,
            'chaddr': self.sock.l2addr,
            'options': options
        })

        start = time.time()
        while time.time() - start <= timeout:
            xid = self.sock.put(msg)['xid']

            for fd, _ in self.poll.poll(timeout):
                assert fd == self.sock.fileno()

                response = self.sock.get()
                if response['xid'] != xid:
                    continue
                if response['options']['message_type'] != expect:
                    raise RuntimeError("DHCP protocol error")
                return response
            time.sleep(0.5)
        else:
            raise RuntimeError('Failed to acquire dhcp lease')

    def request(self, requested_ip=None):
        if not requested_ip:
            requested_ip = self.yiaddr

        logger.info('Sending DHCPREQUEST for %s...', requested_ip)
        return self.send(dhcp.BOOTREQUEST,
                         {'message_type': dhcp.DHCPREQUEST,
                          'requested_ip': requested_ip,
                          'server_id': self.server_id,
                          'parameter_list': self.DHCP_PARAMS},
                         expect=dhcp.DHCPACK)
