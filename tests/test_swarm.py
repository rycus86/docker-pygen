from api import DockerApi
from unittest_helper import BaseDockerTestCase


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

    def test_swarm_model(self):
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

        test_service = self.start_service(endpoint_spec=endpoint_spec, networks=networks,
                                          mode={'Replicated': {'Replicas': 2}},
                                          container_labels={'pygen.container.label': 'on-container'},
                                          labels={'pygen.service.label': 'on-service'},
                                          env={'PYGEN_ENV_KEY': 'test_value'})

        self.wait_for_service_running(test_service)

        services = self.api.services()

        self.assertEqual(len(services), 1)

        service = next(iter(services))

        self.assertEqual(service.id, test_service.id)
        self.assertEqual(service.short_id, test_service.short_id)
        self.assertEqual(service.name, test_service.name)

        for key in ('raw', 'labels', 'ingress', 'networks', 'ports', 'tasks'):
            self.assertIn(key, service)

        self.assertIn(5000, service.ports.tcp)

        ingress = service.ingress

        self.assertEqual(ingress.ports.tcp[0], 8080)
        self.assertGreater(len(ingress.gateway), 0)

        # On Travis CI (probably on older Docker API) we don't get IP addresses for the ingress network
        # self.assertGreater(len(ingress.ip_addresses), 0)

        self.assertEqual(len(service.networks), 1)

        network = next(iter(service.networks))

        self.assertEqual(network.name, networks[0])
        self.assertGreater(len(network.ip_addresses), 0)
        self.assertGreater(len(network.gateway), 0)
        self.assertGreater(len(network.id), 0)

        self.assertEqual(service.labels['pygen.service.label'], 'on-service')

        self.assertEqual(len(service.tasks), 2)

        for task in service.tasks:
            self.assertEqual(task.labels['pygen.container.label'], 'on-container')
            self.assertEqual(task.env.pygen_env_key, 'test_value')

            for net in task.networks:
                for ip_address in net.ip_addresses:
                    if net.is_ingress:
                        self.assertIn(ip_address, ingress.ip_addresses)

                    else:
                        self.assertIn(ip_address, network.ip_addresses)
