import pytest
from lab.comms import connection
from lab.ssh import SSHCommsError, ProcessExecutionError

pytest_plugins = ('lab')


class MyCtl(object):
    def __init__(self, config, location, **kwargs):
        self.config = config
        self.location = location

    ssh = connection('ssh')


class Plugin:
    """Plugin namespace.
    """
    @staticmethod
    def pytest_lab_addroles(config, rolemanager):
        rolemanager.register('myctl', MyCtl)


@pytest.fixture
def myctl(pytestconfig):
    pytestconfig.pluginmanager.register(Plugin)
    return pytest.env.manage(
        'localhost', facts={'port': 2222, 'password': 'root'}
    ).role('myctl')


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
