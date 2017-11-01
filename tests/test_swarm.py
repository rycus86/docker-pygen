import os
import time

import six
from docker.types import Resources, SecretReference

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

        self._wait_for_tasks(test_service, count=2)

        service = self.api.services(desired_task_state='').matching(test_service.id).first_value

        self.assertIsNotNone(service)

        current_task_ids = set(t.id for t in service.tasks)

        for task_id in previous_task_ids:
            self.assertIn(task_id, current_task_ids)

        self.assertGreater(len(current_task_ids), len(previous_task_ids))

        for task_id in current_task_ids:
            if task_id in previous_task_ids:
                self.assertNotEqual(service.tasks.matching(task_id).first.desired_state, 'running')

            else:
                self.assertIn(service.tasks.matching(task_id).first.desired_state, ('ready', 'running'))

    def test_restart_retains_settings(self):
        test_network = self.create_network('pygen-swarm-test', driver='overlay')
        test_secret = self.create_secret('pygen-secret', 'TopSecret')

        test_service = self.start_service(image=os.environ.get('TEST_IMAGE', 'alpine'),
                                          command='sh',
                                          args=['-c', 'sleep 3600'],
                                          constraints=['node.role==manager'],
                                          container_labels={'pygen.container.label': 'label-on-container'},
                                          endpoint_spec={
                                              'Ports':
                                                  [{
                                                      'Protocol': 'tcp',
                                                      'PublishedPort': 8080,
                                                      'TargetPort': 5000
                                                  }]
                                          },
                                          env=['PYGEN_CONTAINER_ENV=env-on-container'],
                                          hostname='pygen-swarm-test-512',
                                          labels={'pygen.service.label': 'label-on-service'},
                                          mode={'Replicated': {'Replicas': 2}},
                                          mounts=['/var:/hostvar:ro'],
                                          networks=[test_network.id],
                                          resources=Resources(mem_limit=8128128),
                                          restart_policy=dict(condition='on-failure', delay=3),
                                          secrets=[SecretReference(secret_id=test_secret.id,
                                                                   secret_name=test_secret.name)],
                                          stop_grace_period=1,
                                          update_config=dict(parallelism=12, delay=7),
                                          user='root',
                                          workdir='/hostvar')

        self.wait_for_service_running(test_service)

        initial_service = self.api.services(desired_task_state='').matching(test_service.id).first_value

        def verify_all(service):
            self.assertIsNotNone(service)
            self.assertGreaterEqual(len(service.tasks), 2)
            self.assertEqual(service.image, test_service.attrs['Spec']['TaskTemplate']['ContainerSpec']['Image'])
            self.assertEqual(service.name, test_service.name)
            self.assertEqual(len(service.raw.attrs['Spec']['EndpointSpec']['Ports']), 1)
            self.assertEqual(service.raw.attrs['Spec']['EndpointSpec']['Ports'][0]['TargetPort'], 5000)
            self.assertEqual(service.raw.attrs['Spec']['EndpointSpec']['Ports'][0]['PublishedPort'], 8080)
            self.assertEqual(service.raw.attrs['Spec']['Labels'], {'pygen.service.label': 'label-on-service'})
            self.assertEqual(service.raw.attrs['Spec']['UpdateConfig']['Delay'], 7)
            self.assertEqual(service.raw.attrs['Spec']['UpdateConfig']['Parallelism'], 12)
            self.assertIn('Replicated', service.raw.attrs['Spec']['Mode'])
            self.assertEqual(service.raw.attrs['Spec']['Mode']['Replicated']['Replicas'], 2)
            self.assertIn(test_network.id, (n['Target'] for n in service.raw.attrs['Spec']['Networks']))

            task_template = service.raw.attrs['Spec']['TaskTemplate']

            self.assertEqual(task_template['Placement']['Constraints'], ['node.role==manager'])
            self.assertEqual(task_template['ContainerSpec']['Command'], ['sh'])
            self.assertEqual(task_template['ContainerSpec']['Args'], ['-c', 'sleep 3600'])
            self.assertEqual(len(task_template['ContainerSpec']['Secrets']), 1)
            self.assertEqual(task_template['ContainerSpec']['Secrets'][0]['SecretID'], test_secret.id)
            self.assertEqual(task_template['ContainerSpec']['Secrets'][0]['SecretName'], test_secret.name)
            self.assertEqual(task_template['ContainerSpec']['Secrets'][0]['File']['Name'], test_secret.name)
            six.assertRegex(self, task_template['ContainerSpec']['Image'], '^%s' % os.environ.get('TEST_IMAGE', 'alpine'))
            self.assertEqual(task_template['ContainerSpec']['Hostname'], 'pygen-swarm-test-512')
            self.assertEqual(task_template['ContainerSpec']['Labels'], {'pygen.container.label': 'label-on-container'})
            self.assertEqual(task_template['ContainerSpec']['User'], 'root')
            self.assertEqual(task_template['ContainerSpec']['Env'], ['PYGEN_CONTAINER_ENV=env-on-container'])
            self.assertEqual(len(task_template['ContainerSpec']['Mounts']), 1)
            self.assertEqual(task_template['ContainerSpec']['Mounts'][0]['Source'], '/var')
            self.assertEqual(task_template['ContainerSpec']['Mounts'][0]['Target'], '/hostvar')
            self.assertTrue(task_template['ContainerSpec']['Mounts'][0]['ReadOnly'])
            self.assertEqual(task_template['ContainerSpec']['StopGracePeriod'], 1)
            self.assertEqual(task_template['ContainerSpec']['Dir'], '/hostvar')
            self.assertTrue(task_template['RestartPolicy']['Condition'], 'on-failure')
            self.assertTrue(task_template['RestartPolicy']['Delay'], 3)
            self.assertTrue(task_template['Resources']['Limits']['MemoryBytes'], 8128128)

        verify_all(initial_service)

        initial_service.update_service(self.api.client.api, force_update=True)

        self._wait_for_tasks(test_service, 4)

        current_service = self.api.services(desired_task_state='').matching(test_service.id).first_value

        self.assertGreater(current_service.version, initial_service.version)
        self.assertNotEqual(set(t.id for t in current_service.tasks), set(t.id for t in initial_service.tasks))

        verify_all(current_service)

    def test_running_state_is_set_once_healthy(self):
        import docker

        create_kwargs = docker.models.services._get_create_service_kwargs('create', dict(
                                          image=os.environ.get('TEST_IMAGE', 'alpine'),
                                          command='sh',
                                          args=['-c', 'sleep 10']))

        create_kwargs['task_template']['ContainerSpec']['Healthcheck'] = {
            'Test': [ 'CMD-SHELL', 'exit 0' ],
            'Interval': 1000000000,
            'StartPeriod': 3000000000
        }

        test_service_id = self.api.client.api.create_service(**create_kwargs)
        try:
            test_service = self.api.client.services.get(test_service_id)
        
            healthy = time.time()

            for event in self.api.events(decode=True):
                if event.get('status', '') == 'health_status: healthy':
                    healthy = time.time()
                    break

                if healthy - time.time() > 10:
                    self.fail('Container did not become healthy')

            while True:
                state = self.api.state
                status = state.services.first.tasks.first.status

                if status == 'running':
                    healthy = time.time() - healthy
                    break

                time.sleep(0.01)

            self.assertLess(healthy, 0.5)

            state = self.api.state

            self.assertEqual(len(state.services), 1)
            self.assertEqual(len(state.services.first.tasks), 1)
            self.assertEqual(state.services.first.tasks.first.status, 'running')

        finally:
            self.api.client.api.remove_service(test_service_id)

    @staticmethod
    def _wait_for_tasks(raw_service, count):
        raw_service.reload()

        for _ in range(50):
            if len(raw_service.tasks()) < count:
                time.sleep(0.2)
