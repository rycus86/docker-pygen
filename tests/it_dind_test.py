from integrationtest_helper import BaseDockerIntegrationTest


class DinDTest(BaseDockerIntegrationTest):
    def test_alpine(self):
        self.prepare_images('alpine')

        output = self.remote_client.containers.run('alpine',
                                                   command='echo "From Alpine"',
                                                   name='pygen-dind-testing-alpine',
                                                   remove=True)

        self.assertEqual(output.strip(), 'From Alpine')

    def test_node(self):
        self.prepare_images('node:7-alpine')

        output = self.remote_client.containers.run('node:7-alpine',
                                                   command='node -e \'console.log("Hello Node")\'',
                                                   name='pygen-dind-testing-node',
                                                   remove=True)

        self.assertEqual(output.strip(), 'Hello Node')

