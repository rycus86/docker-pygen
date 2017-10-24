import os

from integrationtest_helper import BaseDockerIntegrationTest


class PyGenIntegrationTest(BaseDockerIntegrationTest):
    def x_test_generate(self):
        self.local_client.images.build(
            path=os.path.join(os.path.dirname(__file__), '..'),
            tag='pygen-build',
            rm=True)

        self.prepare_images('alpine', 'pygen-build')

        self.remote_client.containers.run('alpine', command='sleep 3600', name='remote-testing', detach=True)

        command = [
            '--template "#{% for c in containers %}\n> {{ c.name }}\n{% endfor %}"',
            '--one-shot'
        ]

        output = self.remote_client.containers.run('pygen-build', command=' '.join(command), remove=True,
                                                   volumes=['/var/run/docker.sock:/var/run/docker.sock:ro'])

        self.assertIn('> remote-testing', output)
