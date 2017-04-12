from __future__ import print_function
from __future__ import absolute_import
from builtins import object
import json
import logging
import requests
import contextlib
import docker as dockerpy
import pytest


class Docker(object):
    def __init__(self, client):
        self.client = client
        self.log = logging.getLogger('docker-py')

    def pull(self, name, tag='latest'):
        """Pull an image of the given name and return it. Similar to
        the docker pull command. """
        for status in self.client.api.pull(name, tag=tag, stream=True):
            data = json.loads(status)
            if 'id' in data:
                self.log.info("{id}: {status}".format(**data))
            else:
                self.log.info(data['status'])

    @contextlib.contextmanager
    def image(self, name, command=None, **kwargs):
        """Launch a detached docker image, pulling it first if
        necessary. Returns a context manager that stops and removed
        the image upon closing. """
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


@pytest.fixture(scope='session')
def docker():
    """An small wrapper around the docker-py ``Client`` api.
    """
    try:
        client = dockerpy.from_env()
        client.ping()
        return Docker(client)
    except requests.ConnectionError:
        pytest.skip("Could not connect to a local docker daemon")
