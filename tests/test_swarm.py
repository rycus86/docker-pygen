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
        super(DockerSwarmTest, self).tearDown()

        if not self.swarm_was_running:
            self.docker_client.swarm.leave(force=True)
        
        self.remove_networks()
        self.api.close()

    def test_swarm(self):
        endpoint_spec = {
            'Ports': 
                [{
                    'Protocol': 'tcp',
                    'PublishedPort': 8080,
                    'TargetPort': 5000
                }]
            }

        networks = [
            self.create_network('pygen-swarm-test', driver='overlay').name
        ]

        test_service = self.start_service(endpoint_spec=endpoint_spec, networks=networks)

        services = self.api.services()

        print(services)

        # test_service.update(name=test_service.name, mode={'Replicated': {'Replicas': 4}})
