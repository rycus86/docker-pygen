import os
import time

import api
from unittest_helper import BaseDockerTestCase


class DockerStateTest(BaseDockerTestCase):
    api = None

    def setUp(self):
        super(DockerStateTest, self).setUp()
        self.api = api.DockerApi()

    def tearDown(self):
        super(DockerStateTest, self).tearDown()
        self.api.close()

    def test_lists_containers(self):
        test_container = self.start_container()
        test_container_id = test_container.id

        containers = self.api.containers()

        self.assertGreater(len(containers), 0)
        self.assertIn(test_container_id, tuple(c.id for c in containers))

        test_container.stop(timeout=1)

        state = self.api.state

        self.assertNotIn(test_container_id, tuple(c.id for c in state.containers))
        self.assertIn(test_container_id, tuple(c.id for c in state.all_containers))

        test_container.remove(force=True)

        state = self.api.state

        self.assertNotIn(test_container_id, tuple(c.id for c in state.containers))
        self.assertNotIn(test_container_id, tuple(c.id for c in state.all_containers))

    def test_returns_container_information(self):
        test_container = self.start_container(labels={'test.label': 'Sample Label', 'test.version': '1.0.x'},
                                              environment={'TEST_COMMAND': 'test-command.sh', 'WITH_EQUALS': 'e=mc^2'},
                                              ports={'9002': None})

        containers = self.api.containers()

        self.assertGreater(len(containers), 0)
        self.assertIn(test_container.id, tuple(c.id for c in containers))

        container = next(x for x in containers if x.id == test_container.id)
        test_container.reload()

        self.assertEqual(test_container, container.raw)
        self.assertEqual(os.environ.get('TEST_IMAGE', 'alpine'), container.image)
        self.assertEqual('running', container.status)
        self.assertEqual(test_container.id, container.id)
        self.assertEqual(test_container.short_id, container.short_id)
        self.assertEqual(test_container.name, container.name)
        self.assertIn('test.label', container.labels)
        self.assertIn('test.version', container.labels)
        self.assertEqual('Sample Label', container.labels['test.label'])
        self.assertEqual('1.0.x', container.labels['test.version'])
        self.assertIn('TEST_COMMAND', container.env)
        self.assertIn('WITH_EQUALS', container.env)

        self.assertEqual('test-command.sh', container.env['TEST_COMMAND'])
        self.assertEqual('e=mc^2', container.env['WITH_EQUALS'])
        self.assertEqual('test-command.sh', container.env.test_command)
        self.assertEqual('e=mc^2', container.env.with_equals)

        self.assertEqual(9002, container.ports.tcp.first)

        self.assertEqual(next(iter(test_container.attrs['NetworkSettings']['Networks'].values())).get('IPAddress'),
                         container.networks.first.ip_address)

        for key in ('raw', 'image', 'status', 'id', 'short_id', 'name', 'labels', 'env', 'networks', 'ports'):
            self.assertIn(key, container)
            self.assertEqual(container[key], getattr(container, key))

    def test_container_health(self):
        self.start_container(healthcheck={
                'Test': ['CMD-SHELL', 'exit 0'],
                'Interval': 500000000
            })

        self.start_container(healthcheck={
                'Test': ['CMD-SHELL', 'exit 0'],
                'Interval': 500000000
            })

        self.start_container(healthcheck={
                'Test': ['CMD-SHELL', 'exit 1'],
                'Interval': 500000000
            })

        self.start_container(healthcheck={
                'Test': ['CMD-SHELL', 'sleep 30'],
                'Interval': 5000000000,
                'StartPeriod': 10000000000
            })

        time.sleep(2)  # give the healthcheck a little time to settle
        
        containers = self.api.containers()

        self.assertEqual(len(containers.healthy), 2)
        self.assertEqual(len(containers.with_health('healthy')), 2)
        self.assertEqual(len(containers.with_health('unhealthy')), 1)
        self.assertEqual(len(containers.with_health('starting')), 1)

