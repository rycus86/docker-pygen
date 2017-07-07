import unittest

from api import DockerApi
from unittest_helper import BaseDockerTestCase


@unittest.skip('Swarm/Service models are not ready yet')
class DockerSwarmTest(BaseDockerTestCase):
    def setUp(self):
        super(DockerSwarmTest, self).setUp()
        self.api = DockerApi()

        self.swarm_was_running = len(self.docker_client.swarm.attrs)

        if not self.swarm_was_running:
            self.docker_client.swarm.init()

    def tearDown(self):
        if not self.swarm_was_running:
            self.docker_client.swarm.leave(force=True)

        self.api.close()
        super(DockerSwarmTest, self).tearDown()

    def test_swarm(self):
        test_service = self.docker_client.services.create('alpine', 'sh -c read', name='pygen-test-swarm')

        services = self.api.services()

        print(services)

        # test_service.update(name=test_service.name, mode={'Replicated': {'Replicas': 4}})
