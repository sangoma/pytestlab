from binascii import unhexlify


class HWAddress(object):
    """Represent and manipulate MAC addresses."""
    def __init__(self, address):
        """
        Args:
            address: A string or integer representing the MAC
        """

        if isinstance(address, bytes) and len(address) == 6:
            self.packed = address
        elif isinstance(address, HWAddress):
            self.packed = address.packed
        else:
            self.packed = unhexlify(address.replace(':', ''))
            assert len(self.packed) == 6

    def __str__(self):
        return ':'.join([format(ord(x), 'x') for x in self.packed])

    def __repr__(self):
        return "HWAddress('{}')".format(self)
