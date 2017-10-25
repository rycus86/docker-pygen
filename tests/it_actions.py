from integrationtest_helper import BaseDockerIntegrationTest


class ActionIntegrationTest(BaseDockerIntegrationTest):
    def setUp(self):
        super(ActionIntegrationTest, self).setUp()
        self.build_project()
        self.prepare_images('alpine', 'pygen-build')

    def test_restart_container(self):
        target = self.remote_client.containers.run('alpine', name='t1', stop_signal='SIGKILL',
                                                   command='sh -c "date +%s ; sleep 3600"',
                                                   detach=True)

        initial_logs = target.logs().strip()

        self.assertGreater(len(initial_logs), 0)

        command = [
            '--template #ok',
            '--restart t1',
            '--one-shot'
        ]

        self.remote_client.containers.run('pygen-build', command=' '.join(command), remove=True,
                                          volumes=['/var/run/docker.sock:/var/run/docker.sock:ro'])

        newer_logs = target.logs().strip()

        self.assertIn(initial_logs, newer_logs)
        self.assertGreater(len(newer_logs), len(initial_logs))

    def test_signal_container(self):
        command = 'sh -c "echo \'Starting...\'; trap \\"echo \'Signalled\'\\" SIGHUP && read"'
        target = self.remote_client.containers.run('alpine', name='t2', command=command, tty=True, detach=True)

        initial_logs = target.logs().strip()

        self.assertIn('Starting...', initial_logs)
        self.assertNotIn('Signalled', initial_logs)

        command = [
            '--template "#{% for c in containers %}{{ c.name }}{% endfor %}"',
            '--signal t2 HUP',
            '--one-shot'
        ]

        self.remote_client.containers.run('pygen-build', command=' '.join(command), remove=True,
                                          volumes=['/var/run/docker.sock:/var/run/docker.sock:ro'])

        newer_logs = target.logs().strip()

        self.assertIn('Signalled', newer_logs)

    def test_restart_service(self):
        command = self.init_swarm()

        with self.with_dind_container() as second_dind:
            
            self.prepare_images('alpine', client=self.dind_client(second_dind))

            second_dind.exec_run(command)

            service = self.remote_client.services.create('alpine',
                                                         name='target-svc',
                                                         mode='global',
                                                         command='sh -c "date +%s ; sleep 3600"',
                                                         stop_grace_period=1)

            import time
            time.sleep(2)

            print 'logs:'
            for line in service.logs(stdout=True):
                print line

