import os
import struct
import socket
import enum
import pnet
from binascii import unhexlify
from pnet.bpf import bpf, bpf_stmt, bpf_jump, Op
from .options import DHCPOption, Options


COOKIE = b'c\x82Sc'  # [0x63, 0x82, 0x53, 0x63])


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
    layout = struct.Struct('!BBBB4s2s2s4s4s4s4s6s202x')

    def __init__(self, opcode, buf=None, **kwargs):
        self.opcode = opcode
        self.htype = 1  # Ethernet
        self.hops = 0
        self.xid = kwargs.get('xid')
        self.secs = kwargs.get('secs', b'\x00' * 2)
        self.flags = kwargs.get('flags', b'\x00' * 2)
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
        assert options  # TODO: improve error reporting

        result = cls.layout.unpack_from(payload)
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


def get_vendor_info():
    sysname, _, release, _, machine = os.uname()
    return b'pydhcp4:{}-{}:{}'.format(sysname, release, machine)


def discover(chaddr=None, hostname=None, vendor=None):
    if not hostname:
        hostname = socket.gethostname()
    if not vendor:
        vendor = get_vendor_info()

    options = [
        (DHCPOption.DHCPMessageType, [DHCPMessage.Discover]),
        (DHCPOption.ClientIdentifier, [
            0xff, 0xb9, 0xcc, 0x05, 0x1a, 0x00, 0x01, 0x1d,
            0x49, 0x20, 0x30, 0x00, 0x50, 0xb6, 0x13, 0x48,
            0xef
        ]),
        (DHCPOption.MaximumDHCPMessageSize, [0x05, 0xc0]),
        (DHCPOption.VendorClassIdentifier, vendor.encode('ascii')),
        (DHCPOption.HostName, hostname.encode('ascii')),
        (DHCPOption.ParameterRequestList, [
            0x01, 0x79, 0x21, 0x03, 0x06, 0x0c, 0x0f, 0x1a,
            0x1c, 0x2a, 0x33, 0x36, 0x3a, 0x3b, 0x77
        ])
    ]

    return DHCPPacket(DHCPOpCode.Request,
                      chaddr=chaddr.packed,
                      options=options)


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
