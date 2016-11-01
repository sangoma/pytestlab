import pytest
import time
import json
import logging
import docker as dockerpy
import plumbum
import contextlib


pytest_plugins = ("pytester", 'lab')


@pytest.fixture(scope='session')
def docker():
    """An instance of a docker-py ``Client`` connected to the local
    docker daemon.
    """
    try:
        client = dockerpy.Client(base_url='unix://var/run/docker.sock')
        client.images()
    except dockerpy.client.requests.ConnectionError:
        pytest.skip("Could not connect to a local docker daemon")

    client.log = logging.getLogger('docker-py')
    return client


@pytest.fixture(scope='session')
def alpine_ssh(docker):
    """Spin up a container running sshd inside an alpine linux image
    from: https://github.com/sickp/docker-alpine-sshd
    """
    # socket addr we expose locally
    host, port = ('127.0.0.1', 2222)
    name = 'sickp/alpine-sshd'

    @contextlib.contextmanager
    def start(host=host, port=port):
        """Start an alpine-linux container running sshd.
        """
        def create():
            return docker.create_container(
                name,
                host_config=docker.create_host_config(
                    port_bindings={22: (host, port)})
            )

        try:
            container = create()
        except dockerpy.errors.NotFound:
            docker.log.info("Pulling fresh {} image from Docker Hub...".format(
                name))
            for line in docker.pull(name, tag='latest', stream=True):
                print(line)
            container = create()

        try:
            uuid = container['Id']
            docker.log.info("Starting alpine-sshd...")
            docker.start(uuid)

            # wait for sshd to come up
            begin = time.time()
            while time.time() - begin < 5:
                try:
                    plumbum.SshMachine(
                        host, port=port, user='root', password='root')
                except plumbum.machines.session.SSHCommsError:
                    # connection not up yet
                    continue
                break

            yield host, port
        finally:
            # tear down
            docker.log.info("Stopping alpine-sshd...")
            docker.stop(uuid)
            docker.remove_container(uuid)

    return start
