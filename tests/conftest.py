from __future__ import absolute_import
import gc
import time
import pytest
import plumbum
import contextlib
from .mocks import lab as mocklab


pytest_plugins = ['lab', 'pytester', mocklab.__name__]


@pytest.fixture(scope='session')
def alpine_ssh(docker):
    """Spin up a container running sshd inside an alpine linux image
    from: https://github.com/sickp/docker-alpine-sshd
    """
    # socket addr we expose locally
    host, port = ('127.0.0.1', 2222)

    @contextlib.contextmanager
    def start(host=host, port=port):
        """Start an alpine-linux container running sshd.
        """
        with docker.image('sickp/alpine-sshd', ports={22: (host, port)},
                          networks=['testlab']):
            # wait for sshd to come up
            begin = time.time()
            while time.time() - begin < 5:
                try:
                    plumbum.SshMachine(host, port=port, user='root',
                                       password='root')
                except plumbum.machines.session.SSHCommsError:
                    # connection not up yet, cleanup the previous
                    # connection. Otherwise we'll leak file
                    # descriptors like crazy
                    gc.collect()
                    continue
                break

            yield host, port

    return start
