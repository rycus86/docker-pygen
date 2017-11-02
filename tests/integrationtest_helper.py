import copy
import os
import re
import sys
import time
import unittest

import docker
import requests


class BaseDockerIntegrationTest(unittest.TestCase):
    DIND_HOST = os.environ.get('DIND_HOST', 'localhost')
    DIND_VERSION = os.environ.get('DIND_VERSION')

    def setUp(self):
        assert self.DIND_VERSION is not None

        self.local_client = docker.DockerClient(os.environ.get('DOCKER_ADDRESS'))

        assert self.local_client.version() is not None

        self.dind_container = self.start_dind_container()

        self.remote_client = docker.DockerClient('tcp://%s:%s' % (self.DIND_HOST, self.dind_port(self.dind_container)),
                                                 version='auto')

        self.dind_containers = [self.dind_container]

    def tearDown(self):
        self.remote_client.api.close()

        self.dind_container.remove(force=True, v=True)

        self.local_client.api.close()

    def start_dind_container(self):
        container = self.local_client.containers.run('docker:%s-dind' % self.DIND_VERSION,
                                                     command='--storage-driver=overlay',
                                                     name='pygen-dind-%s' % int(time.time()),
                                                     ports={'2375': None},
                                                     privileged=True, detach=True)

        try:
            for _ in range(10):
                container.reload()

                if container.status == 'running':
                    if container.id in (c.id for c in self.local_client.containers.list()):
                        break

                time.sleep(0.2)

            port = self.dind_port(container)

            for _ in range(25):
                try:
                    response = requests.get('http://%s:%s/version' % (self.DIND_HOST, port))
                    if response and response.status_code == 200:
                        break

                except requests.exceptions.RequestException:
                    pass

                time.sleep(0.2)

            remote_client = self.dind_client(container)

            assert remote_client.version() is not None

            return container

        except Exception:
            container.remove(force=True, v=True)

            raise

    def dind_port(self, container):
        return container.attrs['NetworkSettings']['Ports']['2375/tcp'][0]['HostPort']

    def dind_client(self, container):
        return docker.DockerClient('tcp://%s:%s' % (self.DIND_HOST, self.dind_port(container)),
                                   version='auto')

    def prepare_images(self, *images, **kwargs):
        remote_client = kwargs.get('client', self.remote_client)

        for tag in images:
            image = self.local_client.images.get(tag)

            remote_client.images.load(image.save().stream())

            if ':' in tag:
                name, tag = tag.split(':')

            else:
                name, tag = tag, None

            remote_client.images.get(image.id).tag(name, tag=tag)

    def build_project(self, tag='pygen-build'):
        self.local_client.images.build(
            path=os.path.join(os.path.dirname(__file__), '..'),
            tag=tag,
            rm=True)

    def with_dind_container(self):
        base = self

        class DindContext(object):
            def __init__(self):
                self.container = None

            def __enter__(self):
                self.container = base.start_dind_container()
                base.dind_containers.append(self.container)
                return self.container

            def __exit__(self, exc_type, exc_val, exc_tb):
                base.dind_containers.remove(self.container)
                self.container.remove(force=True, v=True)

        return DindContext()

    def init_swarm(self):
        output = self.dind_container.exec_run('docker swarm init')

        return re.sub(r'.*(docker swarm join.*--token [a-zA-Z0-9\-]+.*[0-9.]+:[0-9]+).*', r'\1', output,
                      flags=re.MULTILINE | re.DOTALL).replace('\\', ' ')

    @staticmethod
    def wait(seconds):
        time.sleep(seconds)

    @staticmethod
    def wait_for_service_start(service, num_tasks, max_wait=30):
        for _ in range(max_wait * 2):
            if len(service.tasks()) >= num_tasks:
                if all(task['Status']['State'] == 'running'
                       for task in service.tasks(filters={'desired-state': 'running'})):
                    break

            time.sleep(0.5)

    def get_service_logs(self, service, stdout=True, stderr=False):
        logs = list()

        if self.is_below_version('17.05'):
            for remote_container in self.dind_containers:
                client = self.dind_client(remote_container)

                for container in client.containers.list(filters={'name': service.name}):
                    logs.extend(''.join(char for char in container.logs(stdout=stdout, stderr=stderr)).splitlines())

        else:
            logs.extend(''.join(item for item in service.logs(stdout=stdout, stderr=stderr)).splitlines())

        return filter(len, map(lambda x: x.strip(), logs))

    @staticmethod
    def suppress_stderr():
        std_err = sys.stderr
        dev_null = open(os.path.devnull, 'wb')

        class SuppressStderr(object):
            def __enter__(self):
                sys.stderr = dev_null

            def __exit__(self, exc_type, exc_val, exc_tb):
                sys.stderr = std_err

        return SuppressStderr()

    def is_below_version(self, version):
        return map(int, self.DIND_VERSION.split('.')) < map(int, version.split('.'))

    def __str__(self):
        return '%s {%s}' % (super(BaseDockerIntegrationTest, self).__str__(), self.DIND_VERSION)


def load_tests(loader, tests, pattern):
    current_dir = os.path.dirname(__file__)

    package_tests = loader.discover(start_dir=current_dir, pattern='it_*.py')

    suite = unittest.TestSuite()

    # dind_versions = ('17.09', '17.07', '17.06', '17.05', '17.04', '17.03',
    #                  '1.13', '1.12', '1.11', '1.10', '1.9', '1.8')
    dind_versions = ('17.09', '17.06', '17.03', '1.12')

    version_overrides = os.environ.get('DIND_VERSIONS', os.environ.get('DIND_VERSION'))
    if version_overrides:
        dind_versions = tuple(version_overrides.split(','))

    for package_test in package_tests:
        for package_suite in package_test:
            for case in package_suite:
                for dind_version in dind_versions:
                    test_copy = copy.copy(case)
                    test_copy.DIND_VERSION = dind_version
                    suite.addTest(test_copy)

    return suite
