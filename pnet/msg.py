import struct
from ipaddress import IPv4Address
from .utils import HWAddress


class ParseError(RuntimeError):
    """Failed to unpack structure."""


TYPES = {
    'uint8': 'B',
    'uint16': 'H',
    'be16': '>H',
    'ip4addr': {
        'format': '4s',
        'decode': IPv4Address,
        'encode': lambda addr: addr.packed
    },
    'l2addr': {
        'format': '6s',
        'decode': HWAddress,
        'encode': lambda addr: addr.packed
    }
}


def csum(*data):
    # TODO: Use iterator to avoid copying
    data = b''.join(data)

    if len(data) % 2:
        data += b'\x00'

    csum = sum(struct.unpack('!H', data[x:x+2])[0]
               for x in range(0, len(data), 2))

    csum = (csum >> 16) + (csum & 0xffff)
    csum += csum >> 16
    return ~csum & 0xffff


class msg(dict):
    buf = None
    fields = ()
    _fields_names = ()

    def __init__(self, content=None, offset=0, buf=None):
        content = content or {}
        dict.__init__(self, content)
        self._register_fields()
        self.offset = offset
        # NOTE: we assume this is zeroed
        self.buf = memoryview(buf or bytearray(0x100))
        if content and not self.buf.readonly:
            self._encode()

    @classmethod
    def parse(cls, buf, offset=0):
        self = cls(buf=buf, offset=offset)
        try:
            self._decode()
        except struct.error as e:
            raise ParseError(str(e))
        return self

    def _register_fields(self):
        self._fields_names = tuple([x[0] for x in self.fields])

    def _get_routine(self, mode, fmt):
        fmt = TYPES.get(fmt, fmt)
        if isinstance(fmt, dict):
            return (fmt['format'], fmt.get(mode, lambda x: x))
        else:
            return (fmt, lambda x: x)

    def _decode(self):
        self.offset = 0
        for field in self.fields:
            name, sfmt = field[:2]
            fmt, routine = self._get_routine('decode', sfmt)
            size = struct.calcsize(fmt)
            value = struct.unpack_from(fmt, self.buf, self.offset)
            if len(value) == 1:
                value = value[0]
            self[name] = routine(value)
            self.offset += size

    def _encode(self):
        self.offset = 0
        for field in self.fields:
            name, fmt = field[:2]
            default = b'\x00' if len(field) <= 2 else field[2]
            fmt, routine = self._get_routine('encode', fmt)

            size = struct.calcsize(fmt)
            if self[name] is None:
                # Assume we have an empty buffer
                if not isinstance(default, bytes):
                    struct.pack_into(fmt, self.buf, self.offset, default)
            else:
                value = routine(self[name])
                if not isinstance(value, (set, tuple, list)):
                    value = [value]
                struct.pack_into(fmt, self.buf, self.offset, *value)

            self.offset += size

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            if key in self._fields_names:
                return None
            raise

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        # TODO: smell...
        if not self.buf.readonly:
            self._encode()

    def tobytes(self):
        return self.buf[:self.offset].tobytes()

    def __bytes__(self):
        return self.tobytes()

    @property
    def payload(self):
        return self.buf[self.offset:]

    @payload.setter
    def payload(self, data):
        self.buf[self.offset:] = data
