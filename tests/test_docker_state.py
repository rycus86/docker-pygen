import random
import unittest

import docker
from docker.errors import APIError as DockerAPIError

import api


class DockerStateTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.docker_client = docker.DockerClient()

        version = cls.docker_client.version()

        assert version is not None
        assert 'Version' in version
        assert 'ApiVersion' in version

    def start_container(self, image, command, **kwargs):
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

    def setUp(self):
        self.api = api.DockerApi()
        self.started_containers = []

    def tearDown(self):
        for container in self.started_containers:
            try:
                container.remove(force=True)

            except DockerAPIError:
                pass

    def test_lists_containers(self):
        test_container = self.start_container('alpine', 'sh -c read')

        containers = self.api.list()

        self.assertGreater(len(containers), 0)
        self.assertIn(test_container.id, map(lambda x: x.id, containers))

    def test_returns_container_information(self):
        test_container = self.start_container('alpine', 'sh -c read',
                                              labels={'test.label': 'Sample Label', 'test.version': '1.0.x'},
                                              environment={'TEST_COMMAND': 'test-command.sh', 'WITH_EQUALS': 'e=mc^2'})

        containers = self.api.list()

        self.assertGreater(len(containers), 0)
        self.assertIn(test_container.id, map(lambda x: x.id, containers))

        container = next(x for x in containers if x.id == test_container.id)

        self.assertEqual(test_container, container.raw)
        self.assertEqual('alpine', container.image)
        self.assertEqual('running', container.status)
        self.assertEqual(test_container.id, container.id)
        self.assertEqual(test_container.short_id, container.short_id)
        self.assertEqual(test_container.name, container.name)
        self.assertDictEqual({'test.label': 'Sample Label', 'test.version': '1.0.x'}, container.labels)
        self.assertDictContainsSubset({'TEST_COMMAND': 'test-command.sh', 'WITH_EQUALS': 'e=mc^2'}, container.env)

        for key in ('raw', 'image', 'status', 'id', 'short_id', 'name', 'labels', 'env'):
            self.assertIn(key, container)
            self.assertEqual(container[key], getattr(container, key))
