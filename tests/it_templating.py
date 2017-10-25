from integrationtest_helper import BaseDockerIntegrationTest


class TemplatingIntegrationTest(BaseDockerIntegrationTest):
    def setUp(self):
        super(TemplatingIntegrationTest, self).setUp()
        self.build_project()
        self.prepare_images('alpine', 'pygen-build')

    def test_containers(self):
        c1 = self.remote_client.containers.run('alpine', command='sleep 3600',
                                               name='c1',
                                               labels={'pygen.target': 'T1'},
                                               detach=True)

        c2 = self.remote_client.containers.run('alpine', command='sleep 3600',
                                               name='c2',
                                               environment=['PYGEN_TARGET=T2'],
                                               detach=True)

        template = """
        {% for c in containers %}
          ID={{ c.id }} Name={{ c.name }}
        {% endfor %}
        
        T1={{ containers.matching('T1').first.name }}
        T2={{ containers.matching('T2').first.name }}
        """

        self.dind_container.exec_run(['tee', '/tmp/template'], stdin=True, socket=True).sendall(template)

        command = [
            '--template /tmp/template',
            '--one-shot'
        ]

        output = self.remote_client.containers.run('pygen-build', command=' '.join(command), remove=True,
                                                   volumes=['/var/run/docker.sock:/var/run/docker.sock:ro',
                                                            '/tmp/template:/tmp/template:ro'])

        self.assertIn('ID=%s Name=c1' % c1.id, output)
        self.assertIn('ID=%s Name=c2' % c2.id, output)
        self.assertIn('T1=c1', output)
        self.assertIn('T2=c2', output)

    def test_services(self):
        command = self.init_swarm()

        with self.with_dind_container() as second_dind:

            with self.with_dind_container() as third_dind:

                self.prepare_images('alpine', client=self.dind_client(second_dind))
                self.prepare_images('alpine', client=self.dind_client(third_dind))

                second_dind.exec_run(command)
                third_dind.exec_run(command)

                service = self.remote_client.services.create('alpine', 'sleep 3600', name='pygen_svc', mode='global')

                template = """
                {% for s in all_services %}
                S={{ s.id }}-{{ s.name }}
                {% for t in s.tasks %}
                T={{ t.id }}-{{ t.service_id }}
                {% endfor %}
                {% endfor %}
                """

                self.dind_container.exec_run(['tee', '/tmp/template'], stdin=True, socket=True).sendall(template)

                command = [
                    '--template /tmp/template',
                    '--one-shot'
                ]

                output = self.remote_client.containers.run('pygen-build', command=' '.join(command), remove=True,
                                                           volumes=['/var/run/docker.sock:/var/run/docker.sock:ro',
                                                                    '/tmp/template:/tmp/template:ro'])

                self.assertIn('S=%s-pygen_svc' % service.id, output)

                for task in service.tasks():
                    self.assertIn('T=%s-%s' % (task['ID'], service.id), output)

    def test_networks(self):
        network = self.remote_client.networks.create('pygen-net')

        c1 = self.remote_client.containers.run('alpine', command='sleep 3600',
                                               network=network.name,
                                               detach=True)

        c2 = self.remote_client.containers.run('alpine', command='sleep 3600',
                                               network=network.name,
                                               detach=True)

        template = """
        {% set c1 = containers.matching('$c1').first %}
        {% set c2 = containers.matching('$c2').first %}
        N1={{ c1.networks.matching(c2).first.name }}
        N2={{ c1.networks.matching('$network_name').first.id }}
        N3={{ c2.networks.matching('$network_id').first.id }}
        """

        variables = {
            '$c1': c1.id,
            '$c2': c2.id,
            '$network_id': network.id,
            '$network_name': network.name
        }

        for key, value in variables.items():
            template = template.replace(key, value)

        self.dind_container.exec_run(['tee', '/tmp/template'], stdin=True, socket=True).sendall(template)

        command = [
            '--template /tmp/template',
            '--one-shot'
        ]

        output = self.remote_client.containers.run('pygen-build', command=' '.join(command), remove=True,
                                                   volumes=['/var/run/docker.sock:/var/run/docker.sock:ro',
                                                            '/tmp/template:/tmp/template:ro'])

        self.assertIn('N1=%s' % network.name, output)
        self.assertIn('N2=%s' % network.id, output)
        self.assertIn('N3=%s' % network.id, output)

    def test_nodes(self):
        command = self.init_swarm()

        with self.with_dind_container() as second_dind:

            with self.with_dind_container() as third_dind:

                second_dind.exec_run(command)
                third_dind.exec_run(command)

                template = """
                {% for n in nodes %}
                N={{ n.id }}-{{ n.role }}
                {% endfor %}
                """

                self.dind_container.exec_run(['tee', '/tmp/template'], stdin=True, socket=True).sendall(template)

                command = [
                    '--template /tmp/template',
                    '--one-shot'
                ]

                output = self.remote_client.containers.run('pygen-build', command=' '.join(command), remove=True,
                                                           volumes=['/var/run/docker.sock:/var/run/docker.sock:ro',
                                                                    '/tmp/template:/tmp/template:ro'])

                managers = self.remote_client.nodes.list(filters={'role': 'manager'})
                workers = self.remote_client.nodes.list(filters={'role': 'worker'})

                for node in managers:
                    self.assertIn('N=%s-manager' % node.id, output)

                for node in workers:
                    self.assertIn('N=%s-worker' % node.id, output)

