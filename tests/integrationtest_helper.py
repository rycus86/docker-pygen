import os
import time
import unittest

import docker
import requests


class BaseDockerIntegrationTest(unittest.TestCase):
    DIND_VERSION = '17.03.1-ce' # None

    @classmethod
    def setUpClass(cls):
        assert cls.DIND_VERSION is not None
        print 'setting up with', cls.DIND_VERSION

        cls.local_client = docker.DockerClient(os.environ.get('DOCKER_ADDRESS'))

        assert cls.local_client.version() is not None

        cls.dind_container = cls.local_client.containers.run('docker:%s-dind' % cls.DIND_VERSION,
                                                             name='pygen-dind',
                                                             ports={'2375': None},
                                                             privileged=True, detach=True)
        
        try:
            for _ in range(10):
                cls.dind_container.reload()

                if cls.dind_container.status == 'running':
                    if cls.dind_container.id in (c.id for c in cls.local_client.containers.list()):
                        break

                time.sleep(0.2)

            cls.dind_port = cls.dind_container.attrs['NetworkSettings']['Ports']['2375/tcp'][0]['HostPort']
        
            for _ in range(25):
                try:
                    response = requests.get('http://docker.for.mac.localhost:%s/version' % cls.dind_port)
                    if response and response.status_code == 200:
                        break

                except requests.exceptions.RequestException:
                    pass

                time.sleep(0.2)

            cls.remote_client = docker.DockerClient('tcp://docker.for.mac.localhost:%s' % cls.dind_port)

            assert cls.remote_client.version() is not None

        except:
            cls.dind_container.remove(force=True)

            raise

    @classmethod
    def tearDownClass(cls):
        cls.remote_client.api.close()

        cls.dind_container.remove(force=True)

        cls.local_client.api.close()

    def prepare_images(self, *images):
        for tag in images:
            image = self.local_client.images.get(tag)

            for _ in self.remote_client.images.load(image.save().stream()):
                pass
            
            if ':' in tag:
                name, tag = tag.split(':')

            else:
                name, tag = tag, None

            self.remote_client.images.get(image.id).tag(name, tag=tag)

    def x_test_hello(self):
        self.assertEqual(self.dind_container.status, 'running')
        
        self.prepare_images('alpine', 'portainer/portainer', 'node:7-alpine')

        print 'run:', self.remote_client.containers.run('alpine',
                                                        command='echo "From Alpine"', name='pygen-dind-testing',
                                                        remove=True)

        print 'run:', self.remote_client.containers.run('portainer/portainer',
                                                        command='--version', name='pygen-dind-testing2',
                                                        remove=True)

        print 'run:', self.remote_client.containers.run('node:7-alpine',
                                                        command='node -v', name='pygen-dind-testing3',
                                                        remove=True)

    def __str__(self):
        return '%s {%s}' % (super(BaseDockerIntegrationTest, self).__str__(), self.DIND_VERSION)


if __name__ == '__main__':
    current_dir = os.path.dirname(__file__)

    loader = unittest.TestLoader()

    package_tests = loader.discover(start_dir=current_dir, pattern='it_*.py')
    
    # suite = unittest.TestLoader().loadTestsFromTestCase(BaseDockerIntegrationTest)
    # suite = unittest.TestSuite(tests=package_tests)
    suite = unittest.TestSuite()
    
    dind_versions = ('17.06-dind', '17.03.1-ce-dind')

    for package_test in package_tests:
        for package_suite in package_test:
            for case in package_suite:
                for dind_version in dind_versions:
                    #import copy
                    #c = copy.copy(case)
                    #c.DIND_VERSION = dind_version
                    #ct = copy.copy(type(case))
                    #ct.DIND_VERSION = dind_version
                    #c = ct(getattr(case, '_testMethodName'))
                    class IntegrationTest(type(case)):
                        DIND_VERSION = dind_version

                    suite.addTest(IntegrationTest(getattr(case, '_testMethodName')))

                # suite.addTest(xcls(getattr(case, '_testMethodName')))

    unittest.TextTestRunner(verbosity=2).run(suite)

