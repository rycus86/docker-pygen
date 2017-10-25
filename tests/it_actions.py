import time

from integrationtest_helper import BaseDockerIntegrationTest


def skip_below_version(version):
    def decorator(f):
        def wrapper(self, *args, **kwargs):
            if map(int, self.DIND_VERSION.split('.')) < map(int, version.split('.')):
                self.skipTest(reason='Skipping %s on version %s (< %s)' % (f.__name__, self.DIND_VERSION, version))
            else:
                f(self, *args, **kwargs)
        return wrapper
    return decorator


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

    @skip_below_version('17.05')
    def test_restart_service(self):
        join_command = self.init_swarm()

        with self.with_dind_container() as second_dind:
            
            self.prepare_images('alpine', client=self.dind_client(second_dind))

            second_dind.exec_run(join_command)

            service = self.remote_client.services.create('alpine',
                                                         name='target-svc',
                                                         mode='global',
                                                         command='sh -c "date +%s ; sleep 3600"',
                                                         stop_grace_period=1)
            
            for _ in range(10):
                if all(task['Status']['State'] == 'running' for task in service.tasks()):
                    break

                time.sleep(0.5)

            initial_logs = set(line for line in service.logs(stdout=True) if line.strip())

            command = [
                '--template #ok',
                '--restart target-svc',
                '--one-shot'
            ]

            self.remote_client.containers.run('pygen-build', command=' '.join(command), remove=True,
                                              volumes=['/var/run/docker.sock:/var/run/docker.sock:ro'])

            for _ in range(60):
                if len(service.tasks()) >= 4:
                    if all(task['Status']['State'] == 'running'
                           for task in service.tasks(filters={'desired-state': 'running'})):
                        break

                time.sleep(0.5)

            newer_logs = set(line for line in service.logs(stdout=True) if line.strip())

            self.assertNotEqual(newer_logs, initial_logs)

    @skip_below_version('17.05')
    def test_signal_service(self):
        join_command = self.init_swarm()

        with self.with_dind_container() as second_dind:
            
            self.prepare_images('alpine', 'pygen-build', client=self.dind_client(second_dind))

            second_dind.exec_run(join_command)

            network = self.remote_client.networks.create('pygen-net', driver='overlay')

            command = 'sh -c "echo \'Starting...\'; trap \\"echo \'Signalled \'$(hostname)\\" SIGHUP && read"'
            service = self.remote_client.services.create('alpine',
                                                         name='target-svc',
                                                         mode='global',
                                                         command=command,
                                                         networks=[network.name],
                                                         tty=True)

            for _ in range(60):
                if len(service.tasks()) >= 2 and all(task['Status']['State'] == 'running' for task in service.tasks()):
                    break

                time.sleep(0.5)

            time.sleep(5)  # give it some time for logging

            initial_logs = list(line.strip()
                                for line in ''.join(line for line in service.logs(stdout=True)).split('\n')
                                if line.strip())

            worker = self.remote_client.services.create('pygen-build',
                                                        name='pygen-worker',
                                                        command='python',
                                                        args=['swarm_worker.py',
                                                              '--manager', 'pygen-manager',
                                                              '--events', 'none'],
                                                        mode='global',
                                                        networks=[network.name],
                                                        mounts=['/var/run/docker.sock:/var/run/docker.sock:ro'])
            
            for _ in range(60):
                if len(worker.tasks()) >= 2 and all(task['Status']['State'] == 'running' for task in worker.tasks()):
                    break

                time.sleep(0.5)

            args = [
                '--template', '#ok',
                '--signal', 'target-svc', 'HUP',
                '--swarm-manager',
                '--workers', 'tasks.pygen-worker',
                '--interval', '0'
            ]

            manager = self.remote_client.services.create('pygen-build',
                                                         name='pygen-manager',
                                                         args=args,
                                                         constraints=['node.role==manager'],
                                                         networks=[network.name],
                                                         mounts=['/var/run/docker.sock:/var/run/docker.sock:ro'])
            for _ in range(60):
                if len(manager.tasks()) > 0 and all(task['Status']['State'] == 'running' for task in manager.tasks()):
                    break

                time.sleep(0.5)

            time.sleep(5)  # give it some time to execute the action

            newer_logs = list(line.strip()
                              for line in ''.join(line for line in service.logs(stdout=True)).split('\n')
                              if line.strip())

            self.assertNotEqual(tuple(sorted(newer_logs)), tuple(sorted(initial_logs)))
            self.assertEqual(len(newer_logs), 4)
