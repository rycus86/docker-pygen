import os
import random
import time
import unittest

import docker
from docker.errors import APIError as DockerAPIError
from docker.errors import NotFound as DockerNotFound

from compose.config.config import ConfigFile, ConfigDetails
from compose.config.config import load as load_config
from compose.project import Project


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
        self.started_containers = list()
        self.started_services = list()
        self.started_compose_projects = list()
        self.created_networks = list()

    def tearDown(self):
        self.remove_containers()
        self.remove_services()
        self.remove_compose_projects()

    def remove_containers(self):
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

        del self.started_containers[:]

    def remove_services(self):
        if not self.is_in_swarm_mode:
            return

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

        del self.started_services[:]

    def remove_compose_projects(self):
        for project in self.started_compose_projects:
            project.down(False, True, True)

        del self.started_compose_projects[:]
    
    def remove_networks(self):
        for network in self.created_networks:
            try:
                network.remove()

            except DockerNotFound:
                pass  # that's OK, it's already gone somehow

        del self.created_networks[:]

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

    @staticmethod
    def wait_for_service_running(service):
        for _ in range(50):
            tasks = service.tasks()

            if tasks and all(t.get('Status').get('State') == 'running' for t in tasks):
                break

            time.sleep(0.2)

    def start_compose_project(self, name, directory, composefile_name, composefile_contents=None):
        if composefile_contents:
            with open(relative_path('%s/%s' % (directory, composefile_name)), 'w') as composefile:
                composefile.write(composefile_contents)

        config = ConfigFile.from_filename(relative_path('%s/%s' % (directory, composefile_name)))
        details = ConfigDetails(relative_path(directory), [config])
        project = Project.from_config(name, load_config(details), self.docker_client.api)

        self.started_compose_projects.append(project)

        project.up(detached=True)
        
        if composefile_contents:
            os.remove(relative_path('%s/%s' % (directory, composefile_name)))

        return project

    def create_network(self, name, driver='bridge'):
        network = self.docker_client.networks.create(name, driver=driver)

        self.created_networks.append(network)

        return network

    @staticmethod
    def relative(path):
        return relative_path(path)

