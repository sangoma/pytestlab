"""
Controller base type
Encapsulates basic functionality including logging and DNS lookups
"""
import weakref
import warnings


class ControllerError(Exception):
    pass


class Controller(object):
    '''Base for all Controllers.
    This is a bare bones definition which can be modified as needed.
    '''
    def __init__(self, config, location, **kwargs):
        self.config = config
        self._location = weakref.ref(location)
        self.name = self.__class__.__name__
        self.log = location.log

    def close(self):
        pass

    @property
    def location(self):
        return self._location()

    def __str__(self):
        return "<{}: {!r}>".format(self.__class__.__name__, self.location)

    @property
    def equipment(self):
        warnings.warn('Controller.equipment. Use location attribute instead',
                      category=DeprecationWarning)
        return self.location

    @property
    def hostname(self):
        warnings.warn('Check hostname on location instead',
                      category=DeprecationWarning)
        return self.location.hostname

    @property
    def addrinfo(self):
        warnings.warn('Address information should not be looked up on the controller',
                      category=DeprecationWarning)
        return self.location.addrinfo

    @property
    def ip_addr(self):
        warnings.warn('Use addrinfo instead', category=DeprecationWarning)
        return self.location.ip_addr

    @property
    def ip6_addr(self):
        warnings.warn('Use addrinfo instead', category=DeprecationWarning)
        return self.location.ip6_addr
