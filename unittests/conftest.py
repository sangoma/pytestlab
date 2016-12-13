import gc
import json
import time
import pytest
import logging
import docker as dockerpy
import requests
import plumbum
import contextlib
from .mocks import lab as mocklab


pytest_plugins = ['lab', 'pytester', mocklab.__name__]


@pytest.fixture(scope='session')
def docker():
    """An small wrapper around the docker-py ``Client`` api.
    """
    class Docker(object):
        def __init__(self, client):
            self.client = client
            self.log = logging.getLogger('docker-py')

        def pull(self, name, tag='latest'):
            """Pull an image of the given name and return it. Similar
            to the docker pull command.
            """
            for status in self.client.api.pull(name, tag=tag, stream=True):
                data = json.loads(status)
                if 'id' in data:
                    self.log.info("{id}: {status}".format(**data))
                else:
                    self.log.info(data['status'])

        @contextlib.contextmanager
        def image(self, name, command=None, **kwargs):
            """Launch a detached docker image, pulling it first if
            necessary. Returns a context manager that stops and
            removed the image upon closing.
            """
            containers = self.client.containers

            try:
                container = containers.create(name, command, **kwargs)
            except dockerpy.errors.NotFound:
                self.pull(name)
                container = containers.create(name, command, **kwargs)

            short_id = container.short_id
            self.log.info("Starting {} {}...".format(name, short_id))
            container.start()

            try:
                yield container
            finally:
                self.log.info("Stopping {} {}...".format(name, short_id))
                container.stop()
                container.remove()

    try:
        client = dockerpy.from_env()
        client.ping()
        return Docker(client)
    except requests.ConnectionError:
        pytest.skip("Could not connect to a local docker daemon")


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
        with docker.image('sickp/alpine-sshd', ports={22: (host, port)}):
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
