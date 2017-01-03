import pytest
import mock
from lab import comms
from lab.ssh import SSHCommsError, ProcessExecutionError


pytest_plugins = ('lab')


class MyCtl(object):
    def __init__(self, config, location, **kwargs):
        self.config = config
        self.location = location

    ssh = comms.connection('ssh')


class Plugin:
    """Plugin namespace.
    """
    @pytest.hookimpl
    @staticmethod
    def pytest_lab_addroles(config, rolemanager):
        rolemanager.register('myctl', MyCtl)


@pytest.fixture(scope='session')
def localhost(pytestconfig):
    pytestconfig.pluginmanager.register(Plugin)
    return pytest.env.manage(
        'localhost', facts={'port': 2222, 'password': 'root'})


@pytest.fixture
def myctl(localhost):
    return localhost.role('myctl')


@pytest.fixture
def custom_conn():
    """Add a custom connection to a ctl to verify the api works
    as expected.
    """
    kwargs = {'user': 'root', 'password': 'doggy'}
    inst = mock.MagicMock()
    factory = mock.MagicMock(return_value=inst)
    comms.register(
        name='mock',
        factory=factory,
        # always is up
        is_up=lambda driver: driver,
        magic_methods=['__getitem__'],
        **kwargs
    )
    conn = comms.connection('mock')
    MyCtl.mock = conn
    yield conn, factory, inst, kwargs
    del MyCtl.mock


def test_custom_proxied_connection(custom_conn, localhost):
    conn, factory, inst, kwargs = custom_conn

    assert conn.key in comms._registry

    # verify factory calling and lazy loading
    assert not conn._proxies
    myctl = localhost.role('myctl')  # pytest getattrs the world...
    factory.assert_called_once_with(localhost, **kwargs)
    assert conn._proxies[localhost].driver is inst

    # verify attr proxying
    myctl.mock.test()
    inst.test.assert_called_once_with()

    # verify magic method proxying
    myctl.mock['key']
    inst.__getitem__.called_once_with('key')


def test_reliable_ssh(myctl, alpine_ssh):
    # no host up
    with pytest.raises(SSHCommsError):
        ls = myctl.ssh['ls']

    with alpine_ssh():
        # docker host is up
        ls = myctl.ssh['ls']
        assert ls('/')

    with pytest.raises(ProcessExecutionError):
        ls('/')

    # simulate temporary network outage to host
    with alpine_ssh():
        myctl.ssh['ls']
        ls('/')

    # network is "down" here

    with alpine_ssh():
        myctl.ssh['ls']
        assert ls('-a', '/')
