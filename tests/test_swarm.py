import six

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

        self.assertEqual(len(services.matching(test_service.id)), 1)

        service = next(iter(services.matching(test_service.id)))

        self.assertEqual(service.id, test_service.id)
        self.assertEqual(service.short_id, test_service.short_id)
        self.assertEqual(service.name, test_service.name)

        for key in ('raw', 'labels', 'ingress', 'networks', 'ports', 'tasks'):
            self.assertIn(key, service)

        self.assertIn(5000, service.ports.tcp)

        ingress = service.ingress

        self.assertEqual(ingress.ports.tcp[0], 8080)
        self.assertGreater(len(ingress.ip_addresses), 0)
        self.assertGreater(len(ingress.gateway), 0)

        self.assertEqual(len(service.networks), 1)

        network = next(iter(service.networks))

        self.assertEqual(network.name, networks[0])
        self.assertGreater(len(network.ip_addresses), 0)
        self.assertGreater(len(network.gateway), 0)
        self.assertGreater(len(network.id), 0)

        self.assertEqual(service.labels['pygen.service.label'], 'on-service')

        self.assertEqual(len(service.tasks), 2)

        for task in service.tasks:
            self.assertEqual(task.name, '%s.%s.%s' % (service.name, task.slot, task.id))
            self.assertEqual(task.labels['pygen.container.label'], 'on-container')
            self.assertEqual(task.labels['com.docker.swarm.service.id'], service.id)
            self.assertEqual(task.labels['com.docker.swarm.service.name'], service.name)
            self.assertEqual(task.labels['com.docker.swarm.task.id'], task.id)
            self.assertEqual(task.labels['com.docker.swarm.node.id'], task.node_id)
            self.assertEqual(task.env.pygen_env_key, 'test_value')

            for net in task.networks:
                for ip_address in net.ip_addresses:
                    if net.is_ingress:
                        self.assertIn(ip_address, ingress.ip_addresses)

                    else:
                        self.assertIn(ip_address, network.ip_addresses)

        self.assertEqual(len(service.tasks.matching(service.name)), 2)

    def test_node_model(self):
        nodes = self.api.nodes()

        self.assertGreater(len(nodes), 0)

        hostname = self.api.client.info()['Name']

        node = nodes.matching(hostname).first_value

        self.assertIsNotNone(node)

        raw = next(iter(n for n in self.api.client.nodes.list() if n.id == node.id))

        self.assertEqual(node.short_id, raw.short_id)
        self.assertEqual(node.version, raw.version)
        self.assertEqual(node.role, raw.attrs['Spec']['Role'])

    def test_restart_service(self):
        test_service = self.start_service()

        self.wait_for_service_running(test_service)

        service = self.api.services().matching(test_service.id).first_value

        self.assertIsNotNone(service)

        previous_task_ids = set(t.id for t in service.tasks)

        self.assertTrue(service.update_service(self.api.client.api, force_update=True))
        
        test_service.reload()

        self.wait_for_service_running(test_service)

        service = self.api.services(desired_task_state='').matching(test_service.id).first_value

        self.assertIsNotNone(service)

        current_task_ids = set(t.id for t in service.tasks)

        six.assertCountEqual(self, current_task_ids, previous_task_ids)

