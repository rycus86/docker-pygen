import os
import time
import random
import unittest

import docker
from docker.errors import APIError as DockerAPIError


def relative_path(path):
    return os.path.join(os.path.dirname(__file__), path)


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

    def start_container(self, image=os.environ.get('TEST_IMAGE', 'alpine'), command='sh -c read', **kwargs):
        options = {
            'detach': True,
            'tty': True,
            'name': 'pygen-unittest-%s' % random.randint(0x100, 0xFFFF)
        }

        options.update(kwargs)

        container = self.docker_client.containers.run(image, command, **options)

        try:
            self.started_containers.append(container)

            for _ in xrange(10):
                container.reload()

                if container.status == 'running':
                    if container.id in (c.id for c in self.docker_client.containers.list()):
                        break

                time.sleep(0.2)

        except DockerAPIError:
            container.remove(force=True)
            raise

        return container

    @staticmethod
    def relative(path):
        return relative_path(path)
