import struct
import ctypes
import socket
import enum


SO_ATTACH_FILTER = 26


class Op(enum.IntEnum):
    # Instruction classes
    LD = 0x00
    LDX = 0x01
    ST = 0x02
    STX = 0x03
    ALU = 0x04
    JMP = 0x05
    RET = 0x06
    MISC = 0x07
    # ld/ldx fields
    W = 0x00
    H = 0x08
    B = 0x10
    IMM = 0x00
    ABS = 0x20
    IND = 0x40
    MEM = 0x60
    LEN = 0x80
    MSH = 0xa0
    # alu/jmp fields */
    ADD = 0x00
    SUB = 0x10
    MUL = 0x20
    DIV = 0x30
    OR = 0x40
    AND = 0x50
    LSH = 0x60
    RSH = 0x70
    NEG = 0x80
    MOD = 0x90
    XOR = 0xa0
    JA = 0x00
    JEQ = 0x10
    JGT = 0x20
    JGE = 0x30
    JSET = 0x40
    K = 0x00
    X = 0x08


def bpf_jump(ops, k, jt, jf):
    code = 0
    for op in ops:
        code |= op.value
    return struct.pack('HBBI', code, jt, jf, k)


def bpf_stmt(ops, k):
    return bpf_jump(ops, k, 0, 0)


class bpf(list):
    def tobytes(self):
        return b''.join(self)

    def __bytes__(self):
        return self.tobytes()

    def compile(self):
        buf = ctypes.create_string_buffer(self.tobytes())
        return struct.pack('HL', len(self), ctypes.addressof(buf)), buf


def attach_filter(sock, bpf):
    bpf_repr, program = bpf.compile()
    sock.setsockopt(socket.SOL_SOCKET, SO_ATTACH_FILTER, bpf_repr)
    return program
