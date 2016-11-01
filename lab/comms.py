"""
Communication drivers and connection management.
"""
import logging
from lab.ssh import get_ssh, get_sftp


log = logging.getLogger(name='lab.comms')


_registry = {
    'ssh': {
        'factory': lambda location: get_ssh(location),
        'is_up': lambda ssh: ssh._session.alive(),
        'magic_methods': ['__getitem__']
    },
    'sftp': {
        'factory': lambda location: get_sftp(location),
        'is_up': lambda sftp: sftp.get_channel().active,
    },
}


def register(name, factory, is_up, **kwargs):
    data = {'factory': factory, 'is_up': is_up}
    data.update(kwargs)
    _registry[name] = data
    log.debug("Registered comms driver {} with {}".format(
        name, data))


class Reliable(object):
    """A reliable connection proxy which attempts to re-establish an
    underlying connection to a location if it goes down.
    """
    def __init__(self, location, factory, is_up, **kwargs):
        self.location = location
        self.factory = factory
        # predicate which returns True if our underlying connection is up
        self.is_up = is_up
        self.kwargs = kwargs
        # cached connection
        self._driver = None

    @property
    def driver(self):
        if self._driver is None or not self.is_up(self._driver):
            self._driver = self.factory(self.location, **self.kwargs)
            log.debug("Reconnected driver {}".format(self._driver))

        return self._driver

    def __repr__(self):
        clsname = type(self).__name__
        return object.__repr__(self).replace(
            clsname, '{}({})'.format(clsname, repr(self.driver)))

    def __getattr__(self, attr):
        return getattr(self.driver, attr)

    def __dir__(self):
        return sorted(set(dir(type(self.driver)) + list(
            self.driver.__dict__.keys())))


def reliable_proxy(location, key):
    """Create reliable proxy instance for a communications driver according to
    the registry.
    """
    data = _registry[key]
    return type(
        'ReliableProxy',
        (Reliable,),
        {name: lambda proxy, *args:
            getattr(type(proxy.driver), name)(proxy.driver, *args)
         for name in data.pop('magic_methods', [])}
    )(location, **data)


class connection(object):
    """A descriptor for declaring connection types on role controllers
    which does lazy loading of a ``Reliable`` proxy wrapper.
    """
    def __init__(self, key, **kwargs):
        if key not in _registry:
            raise KeyError(
                "No comms driver for {} has been registered".format(key))
        self.key = key
        self._proxy = None

    def __get__(self, ctl, type=None):
        if ctl is None:
            return self

        if self._proxy is None:
            self._proxy = reliable_proxy(ctl.location, self.key)

        return self._proxy
