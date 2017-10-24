import re

import docker

from integrationtest_helper import BaseDockerIntegrationTest


class SwarmIntegrationTest(BaseDockerIntegrationTest):
    def x_test_swarm(self):
        output = self.dind_container.exec_run('docker swarm init')

        command = re.sub(r'.*(docker swarm join.*--token [a-zA-Z0-9\-]+.*[0-9.]+:[0-9]+).*', r'\1', output,
                         flags=re.MULTILINE | re.DOTALL)

        # print 'out:', output
        print 'cmd:', command

        second_dind = self.start_dind_container()

        try:
            print second_dind.exec_run(command.replace('\\', ' '))
            print self.dind_container.exec_run('docker node ls')

            self.prepare_images('pygen-build', client=self.remote_client)
            self.prepare_images('pygen-build', client=docker.DockerClient('tcp://%s:%s' %
                                                                          (self.DIND_HOST, self.dind_port(second_dind)),
                                                                          version='auto'))

            print self.dind_container.exec_run('docker service create --name tstsrv --mode global pygen-build '
                                               '--template "#{% for s in services %}-> {{ s.name }}{% endfor %}"')

            print self.dind_container.exec_run('docker service ls')
            print self.dind_container.exec_run('docker service ps tstsrv')

        finally:
            self.local_client.api.remove_container(second_dind.id, force=True)

