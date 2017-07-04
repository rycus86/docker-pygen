import random
import unittest

import docker
from docker.errors import APIError as DockerAPIError


class BaseDockerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docker_client = docker.DockerClient()

        version = cls.docker_client.version()

        assert version is not None
        assert 'Version' in version
        assert 'ApiVersion' in version

    def setUp(self):
        self.started_containers = []

    def tearDown(self):
        for container in self.started_containers:
            try:
                container.remove(force=True)

            except DockerAPIError:
                pass

    def start_container(self, image='alpine', command='sh -c read', **kwargs):
        options = {
            'detach': True,
            'tty': True,
            'name': 'pygen-unittest-%s' % random.randint(0x100, 0xFFFF)
        }

        options.update(kwargs)

        container = self.docker_client.containers.create(image, command, **options)

        try:
            container.start()

            self.started_containers.append(container)

        except DockerAPIError:
            container.remove(force=True)
            raise

        return container
