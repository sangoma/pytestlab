from __future__ import absolute_import, print_function

import six
import logging
import socket
import select
import posixpath
import etcd
import click
import json
import atexit
import ipaddress

import lab.etcd as _etcd
from pyroute2 import IPRSocket
from pyroute2.netlink.rtnl import RTM_GETADDR
from pyroute2.netlink.rtnl.ifaddrmsg import ifaddrmsg
from pyroute2.netlink.rtnl.ifaddrmsg import IFA_F_DADFAILED


@click.command()
@click.argument('hostname')
@click.option('--discovery-srv', envvar='ETCD_DISCOVERY_SRV',
              metavar='DOMAIN', required=True,
              help='The etcd dns discovery domain')
def cli(hostname, discovery_srv):
    logging.basicConfig()

    # TEMP HACKS
    #-----------------------------------------------------------
    path = posixpath.join('address', *reversed(hostname.split('.')))
    print("RECORDING INTO", path)

    client = _etcd.connect(discovery_srv)
    #-----------------------------------------------------------

    epoll = select.epoll()

    addrs = {}
    client.write(path, addrs)

    def cleanup():
        client.delete(path)
    atexit.register(cleanup)

    def update_etcd(msg):
        event = msg.get('event')

        if event == 'RTM_NEWADDR' or event == 'RTM_DELADDR':
            address = msg.get_attr('IFA_ADDRESS')

            flags = msg.get_attr('IFA_FLAGS')
            if flags and flags & IFA_F_DADFAILED:
                print(" - skipping, dad failed:", address)
                return

            addr = ipaddress.ip_address(six.text_type(address))
            if addr.is_reserved:
                print(" - skipping, reserved:", address)
                return
            elif addr.is_multicast:
                print(" - skipping, multicast:", address)
                return
            elif addr.is_unspecified:
                print(" - skipping, unspecified:", address)
                return
            elif addr.is_loopback:
                print(" - skipping, loopback:", address)
                return
            elif addr.is_link_local:
                print(" - skipping, link local:", address)
                return

            if msg['family'] == socket.AF_INET:
                section = addrs.setdefault('A', [])
            elif msg['family'] != socket.AF_INET:
                section = addrs.setdefault('AAAA', [])
            else:
                print(" - skipping, unknown family:", address)
                return


            if event == 'RTM_NEWADDR' and address not in section:
                section.append(address)
            elif event == 'RTM_DELADDR':
                section.remove(address)
            else:
                return

        print("REPORTING", addrs)
        try:
            client.write(path, json.dumps(addrs))
        except etcd.EtcdException:
            pass  # for now, so we try again


    with IPRSocket() as ipr:
        ipr.bind()

        epoll.register(ipr.fileno(), select.EPOLLIN)

        for msg in ipr.nlm_request(ifaddrmsg(), msg_type=RTM_GETADDR):
            update_etcd(msg)

        while True:
            events = epoll.poll(1)
            for fileno, event in events:
                assert fileno == ipr.fileno()

                for msg in ipr.get():
                    update_etcd(msg)
