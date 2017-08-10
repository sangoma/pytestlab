import os
import sys
import struct
import socket
import enum
import pnet
from binascii import unhexlify
from pnet.bpf import bpf, bpf_stmt, bpf_jump, Op
from .options import DHCPOption, Options


COOKIE = b'c\x82Sc'  # [0x63, 0x82, 0x53, 0x63])


if sys.version_info >= (3, 0):
    ord = lambda x: x


class DHCPOpCode(enum.IntEnum):
    Request = 1
    Reply = 2


class DHCPMessage(enum.IntEnum):
    Discover = 1
    Offer = 2
    Request = 3
    Decline = 4
    ACK = 5
    NAK = 6
    Release = 7
    Inform = 8


class DHCPPacket:
    layout = struct.Struct('!BBBB4sHH4s4s4s4s6s202x')

    def __init__(self, opcode, buf=None, **kwargs):
        self.opcode = opcode
        self.htype = 1  # Ethernet
        self.hops = 0
        self.xid = kwargs.get('xid')
        self.secs = kwargs.get('secs', 0)
        self.flags = kwargs.get('flags', 0)
        self.ciaddr = kwargs.get('ciaddr', b'\x00' * 4)
        self.yiaddr = kwargs.get('yiaddr', b'\x00' * 4)
        self.siaddr = kwargs.get('siaddr', b'\x00' * 4)
        self.giaddr = kwargs.get('giaddr', b'\x00' * 4)
        self.chaddr = pnet.HWAddress(kwargs['chaddr'])
        self.options = Options(kwargs.get('options', []))
        if not self.xid:
            self.xid = os.urandom(4)

    @classmethod
    def parse(cls, payload):
        _, _, options = payload.tobytes().partition(COOKIE)
        if not options:
            raise pnet.ParseError('Failed to find DHCP cookie')

        try:
            result = cls.layout.unpack_from(payload)
        except struct.error as e:
            raise ParseError(str(e))

        self = cls(
            result[0],
            xid=result[4],
            secs=result[5],
            flags=result[6],
            ciaddr=result[7],
            yiaddr=result[8],
            siaddr=result[9],
            giaddr=result[10],
            chaddr=result[11],
            options=Options.parse(memoryview(options))
        )

        self.htype = result[1]
        self.hops = result[3]
        return self

    def tobytes(self):
        chaddr = self.chaddr.packed
        header = self.layout.pack(
            self.opcode,  # 0
            self.htype,  # 1
            len(chaddr),  # 2
            self.hops,  # 3
            self.xid,  # 4:8
            self.secs,  # 8:10
            self.flags,  # 10:12
            self.ciaddr,  # 12:16
            self.yiaddr,  # 16:20
            self.siaddr,  # 20:24
            self.giaddr,  # 24:28
            chaddr  # 28:44
        )
        payload = b''.join((header, COOKIE, self.options.tobytes()))
        return payload.ljust(272, b'\x00')

    def __bytes__(self):
        return self.tobytes()

    @property
    def message_type(self):
        options = dict(self.options)
        payload = options[DHCPOption.DHCPMessageType].tobytes()
        return DHCPMessage(ord(payload[0]))


def get_vendor_info():
    sysname, _, release, _, machine = os.uname()
    return 'pydhcp4:{}-{}:{}'.format(sysname, release, machine)


def get_client_id(chaddr):
    return struct.pack('!B6s', 1, chaddr.packed)


def bootp_filter(port=68):
    return bpf([
        # Check the udp port number
        bpf_stmt([Op.LD, Op.H, Op.ABS], 0x24),
        bpf_jump([Op.JMP, Op.JEQ, Op.K], port, 0, 7),

        # Check ip fragment offset is 0 to verify TCP
        bpf_stmt([Op.LD, Op.H, Op.ABS], 0x14),
        bpf_jump([Op.JMP, Op.JSET, Op.K], 0x1fff, 5, 0),

        # Check tcp protocol field
        bpf_stmt([Op.LD, Op.B, Op.ABS], 0x17),
        bpf_jump([Op.JMP, Op.JEQ, Op.K], socket.IPPROTO_UDP, 0, 3),

        # Check ethertype field for IPv4
        bpf_stmt([Op.LD, Op.H, Op.ABS], 0x0c),
        bpf_jump([Op.JMP, Op.JEQ, Op.K], pnet.ETH_P_IP, 0, 1),

        bpf_stmt([Op.RET, Op.K], 0xffffffff),
        bpf_stmt([Op.RET, Op.K], 0),
    ])
