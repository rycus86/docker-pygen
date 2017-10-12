import os
import time
import unittest

import docker


class BaseDockerIntegrationTest(unittest.TestCase):
    DIND_VERSION = '17.03.1-ce' # None

    @classmethod
    def setUpClass(cls):
        assert cls.DIND_VERSION is not None

        cls.local_client = docker.DockerClient(os.environ.get('DOCKER_ADDRESS'))

        assert cls.local_client.version() is not None

        cls.dind_container = cls.local_client.containers.run('docker:%s-dind' % cls.DIND_VERSION,
                                                             name='pygen-dind',
                                                             ports={'2375': None},
                                                             privileged=True, detach=True)
        print 'dind:', cls.dind_container
        # TODO error handling + cleanup 
        for _ in range(10):
            cls.dind_container.reload()

            if cls.dind_container.status == 'running':
                if cls.dind_container.id in (c.id for c in cls.local_client.containers.list()):
                    break

            time.sleep(0.2)

        cls.dind_port = cls.dind_container.attrs['NetworkSettings']['Ports']['2375/tcp'][0]['HostPort']
        
        time.sleep(5)  # FIXME wait until DinD starts

        print 'connecting to: tcp://localhost:%s' % cls.dind_port
        cls.remote_client = docker.DockerClient('tcp://docker.for.mac.localhost:%s' % cls.dind_port)

        assert cls.remote_client.version() is not None

    @classmethod
    def tearDownClass(cls):
        cls.remote_client.api.close()

        cls.dind_container.remove(force=True)

        cls.local_client.api.close()

    def test_hello(self):
        self.assertEqual(self.dind_container.status, 'running')


# suite = unittest.TestLoader().loadTestsFromTestCase(BaseDockerIntegrationTest)
# unittest.TextTestRunner(verbosity=2).run(suite)

