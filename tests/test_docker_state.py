import os
import api
from unittest_helper import BaseDockerTestCase


class DockerStateTest(BaseDockerTestCase):
    def setUp(self):
        super(DockerStateTest, self).setUp()
        self.api = api.DockerApi()

    def test_lists_containers(self):
        test_container = self.start_container()

        containers = self.api.list()

        self.assertGreater(len(containers), 0)
        self.assertIn(test_container.id, map(lambda x: x.id, containers))

    def test_returns_container_information(self):
        test_container = self.start_container(labels={'test.label': 'Sample Label', 'test.version': '1.0.x'},
                                              environment={'TEST_COMMAND': 'test-command.sh', 'WITH_EQUALS': 'e=mc^2'},
                                              ports={'9002': None})

        containers = self.api.list()

        self.assertGreater(len(containers), 0)
        self.assertIn(test_container.id, map(lambda x: x.id, containers))

        container = next(x for x in containers if x.id == test_container.id)
        test_container.reload()

        self.assertEqual(test_container, container.raw)
        self.assertEqual(os.environ.get('TEST_IMAGE', 'alpine'), container.image)
        self.assertEqual('running', container.status)
        self.assertEqual(test_container.id, container.id)
        self.assertEqual(test_container.short_id, container.short_id)
        self.assertEqual(test_container.name, container.name)
        self.assertDictContainsSubset({'test.label': 'Sample Label', 'test.version': '1.0.x'}, container.labels)
        self.assertDictContainsSubset({'TEST_COMMAND': 'test-command.sh', 'WITH_EQUALS': 'e=mc^2'}, container.env)
        self.assertIn(next(iter(test_container.attrs['NetworkSettings']['Networks'].values())).get('IPAddress'),
                      container.network.ip_addresses)

        for key in ('raw', 'image', 'status', 'id', 'short_id', 'name', 'labels', 'env', 'network'):
            self.assertIn(key, container)
            self.assertEqual(container[key], getattr(container, key))
