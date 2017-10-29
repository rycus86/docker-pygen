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

    def test_restart_compose_service(self):
        from compose.config.config import ConfigFile, ConfigDetails
        from compose.config.config import load as load_config
        from compose.project import Project

        composefile = """
        version: '2'
        services:
          app:
            image: alpine
            command: sh -c 'date +%s ; sleep 3600'

          pygen:
            image: pygen-build
            command: >
              --template '#ok'
              --restart app
              --one-shot
            volumes:
              - /var/run/docker.sock:/var/run/docker.sock:ro
            depends_on:
              - app
        """

        with open('/tmp/pygen-composefile.yml', 'w') as target:
            target.write(composefile)

        config = ConfigFile.from_filename('/tmp/pygen-composefile.yml')
        details = ConfigDetails('/tmp', [config])
        project = Project.from_config('cmpse', load_config(details), self.remote_client.api)

        with self.suppress_stderr():
            project.up(detached=True, service_names=['app'], scale_override={'app': 2})

            app = project.get_service('app')

            for _ in range(60):
                if len(app.containers()) < 2 or not all(c.is_running for c in app.containers()):
                    self.wait(0.5)

            initial_logs = list(''.join(c.logs(stdout=True) for c in app.containers()).splitlines())

            project.up(detached=True, scale_override={'app': 2})

            pygen_service = project.get_service('pygen')
            pygen_container = next(iter(pygen_service.containers()))
            pygen_container.wait()

            for _ in range(60):
                if len(app.containers()) < 2 or not all(c.is_running for c in app.containers()):
                    self.wait(0.5)
        
            newer_logs = list(''.join(c.logs(stdout=True) for c in app.containers()).splitlines())

            self.assertNotEqual(tuple(sorted(newer_logs)), tuple(sorted(initial_logs)))
            self.assertEqual(len(newer_logs), 4)

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

    @skip_below_version('1.13')
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

            self.wait_for_service_start(service, num_tasks=2)

            initial_logs = self.get_service_logs(service)

            command = [
                '--template #ok',
                '--restart target-svc',
                '--one-shot'
            ]

            self.remote_client.containers.run('pygen-build', command=' '.join(command), remove=True,
                                              volumes=['/var/run/docker.sock:/var/run/docker.sock:ro'])

            self.wait_for_service_start(service, num_tasks=4)

            self.wait(5)  # give it some time for logging

            newer_logs = self.get_service_logs(service)

            self.assertNotEqual(newer_logs, initial_logs)

    @skip_below_version('1.13')
    def test_restart_service_retains_settings(self):
        from docker.types import EndpointSpec, Resources, RestartPolicy, SecretReference, UpdateConfig

        join_command = self.init_swarm()

        with self.with_dind_container() as second_dind:
            self.prepare_images('alpine', client=self.dind_client(second_dind))

            second_dind.exec_run(join_command)

            network = self.remote_client.networks.create('pygen-net', driver='overlay')

            secret = self.remote_client.secrets.create(name='pygen-secret', data='TopSecret')

            secret.reload()

            service = self.remote_client.services.create('alpine',
                                                         name='target-svc',
                                                         mode='global',
                                                         command='sh -c "date +%s ; sleep 3600"',
                                                         constraints=['node.hostname != non-existing-node'],
                                                         container_labels={'container.label': 'testing'},
                                                         endpoint_spec=EndpointSpec(mode='vip',
                                                                                    ports={14002: 1234}),
                                                         env=['TEST_ENV_VAR=12345'],
                                                         labels={'service.label': 'on-service'},
                                                         mounts=['/tmp:/data/hosttmp:ro'],
                                                         networks=[network.name],
                                                         resources=Resources(mem_limit=24000000),
                                                         restart_policy=RestartPolicy(condition='any',
                                                                                      delay=5,
                                                                                      max_attempts=3),
                                                         secrets=[SecretReference(secret_id=secret.id,
                                                                                  secret_name=secret.name)],
                                                         stop_grace_period=1,
                                                         update_config=UpdateConfig(parallelism=1, delay=1),
                                                         user='nobody',
                                                         workdir='/data/hosttmp',
                                                         tty=True)

            self.wait_for_service_start(service, num_tasks=2)

            service.reload()

            initial_spec = service.attrs['Spec']

            command = [
                '--template #ok',
                '--restart target-svc',
                '--one-shot'
            ]

            self.remote_client.containers.run('pygen-build', command=' '.join(command), remove=True,
                                              volumes=['/var/run/docker.sock:/var/run/docker.sock:ro'])

            self.wait_for_service_start(service, num_tasks=4)

            service = self.remote_client.services.get(service.id)

            service.reload()

            newer_spec = service.attrs['Spec']

            del initial_spec['TaskTemplate']['ForceUpdate']
            del newer_spec['TaskTemplate']['ForceUpdate']

            self.assertDictEqual(newer_spec, initial_spec)

    @skip_below_version('1.13')
    def test_signal_service(self):
        join_command = self.init_swarm()

        with self.with_dind_container() as second_dind:

            self.prepare_images('alpine', 'pygen-build', client=self.dind_client(second_dind))

            second_dind.exec_run(join_command)

            network = self.remote_client.networks.create('pygen-net', driver='overlay')

            command = ''.join(['sh -c "echo -n \'Starting...\' > /var/tmp/output; '
                               'trap \\"echo -n \'Signalled\' > /var/tmp/output\\" SIGHUP ',
                               '&& read"'])

            service = self.remote_client.services.create('alpine',
                                                         name='target-svc',
                                                         mode='global',
                                                         command=command,
                                                         networks=None,
                                                         mounts=['/var/tmp:/var/tmp'],
                                                         tty=True)

            self.wait_for_service_start(service, num_tasks=2)

            self.wait(5)  # give it some time for logging

            initial_output = list(c.exec_run(['cat', '/var/tmp/output']) for c in self.dind_containers)

            self.assertEqual(initial_output, ['Starting...', 'Starting...'])

            worker = self.remote_client.services.create('pygen-build',
                                                        name='pygen-worker',
                                                        command='python',
                                                        args=['swarm_worker.py',
                                                              '--manager', 'pygen-manager',
                                                              '--events', 'none'],
                                                        mode='global',
                                                        networks=[network.name],
                                                        mounts=['/var/run/docker.sock:/var/run/docker.sock:ro'])

            self.wait_for_service_start(worker, num_tasks=2)

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

            self.wait_for_service_start(manager, num_tasks=1)

            self.wait(5)  # give it some time to execute the action

            newer_output = list(c.exec_run(['cat', '/var/tmp/output']) for c in self.dind_containers)

            self.assertEqual(newer_output, ['Signalled', 'Signalled'])
