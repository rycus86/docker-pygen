import os
import random
import time
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

    @classmethod
    def tearDownClass(cls):
        cls.docker_client.api.close()

    @property
    def is_in_swarm_mode(self):
        return self.docker_client.swarm.attrs

    def setUp(self):
        self.started_containers = []
        self.started_services = []
        self.created_networks = []

    def tearDown(self):
        container_ids = list(c.id for c in self.started_containers)

        for container in self.started_containers:
            try:
                container.remove(force=True)

            except DockerAPIError:
                pass

        for _ in range(10):
            if not self.docker_client.containers.list(filters=dict(id=container_ids)):
                break

            time.sleep(0.2)

        if self.is_in_swarm_mode:
            service_ids = list(s.id for s in self.started_services)

            for service in self.started_services:
                try:
                    service.remove()

                except DockerAPIError:
                    pass

            for _ in range(10):
                if not self.docker_client.services.list(filters=dict(id=service_ids)):
                    break

                time.sleep(0.2)
    
    def remove_networks(self):
        for network in self.created_networks:
            network.remove()

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

            for _ in range(10):
                container.reload()

                if container.status == 'running':
                    if container.id in (c.id for c in self.docker_client.containers.list()):
                        break

                time.sleep(0.2)

        except DockerAPIError:
            container.remove(force=True)
            raise

        return container

    def start_service(self, image=os.environ.get('TEST_IMAGE', 'alpine'), command='sh -c read', **kwargs):
        options = {
            'tty': True,
            'name': 'pygen-swarm-unittest-%s' % random.randint(0x100, 0xFFFF)
        }

        options.update(kwargs)

        service = self.docker_client.services.create(image, command, **options)

        try:
            self.started_services.append(service)

        except DockerAPIError:
            service.remove()
            raise

        return service

    def create_network(self, name, driver='bridge'):
        network = self.docker_client.networks.create(name, driver=driver)

        self.created_networks.append(network)

        return network

    @staticmethod
    def relative(path):
        return relative_path(path)

