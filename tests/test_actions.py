import os
import six
from unittest_helper import BaseDockerTestCase

import api
import actions


class ActionsTest(BaseDockerTestCase):
    api = None

    def setUp(self):
        super(ActionsTest, self).setUp()
        self.api = api.DockerApi()

    def tearDown(self):
        super(ActionsTest, self).tearDown()
        self.api.close()

    def test_matching_containers(self):
        test_container = self.start_container(labels={'pygen.target': 'pygen-action-target'})

        action = actions.Action(self.api)
        
        containers = list(action.matching_containers('pygen-action-target'))

        self.assertEqual(len(containers), 1)
        self.assertEqual(containers[0].id, test_container.id)
        
        container_ids = list(c.id for c in containers)
        
        six.assertCountEqual(self, list(c.id for c in action.matching_containers(test_container.id)), container_ids)
        six.assertCountEqual(self, list(c.id for c in action.matching_containers(test_container.short_id)), container_ids)
        six.assertCountEqual(self, list(c.id for c in action.matching_containers(test_container.name)), container_ids)

    def test_matching_containers_by_env(self):
        test_containers = [
            self.start_container(environment=['PYGEN_TARGET=pygen-action-by-env']),
            self.start_container(environment=['PYGEN_TARGET=pygen-action-by-env']),
            self.start_container(environment=['PYGEN_TARGET=pygen-action-by-env'])
        ]

        action = actions.Action(self.api)
        
        containers = list(action.matching_containers('pygen-action-by-env'))

        self.assertEqual(len(containers), 3)

        for container in containers:
            self.assertIn(container.id, (c.id for c in test_containers))
    
    def test_matching_compose_container(self):
        composefile = """
        version: '2'
        services:
          actiontest:
            image: {image}
            command: "sleep 300"
        """.format(image=os.environ.get('TEST_IMAGE', 'alpine'))

        project = self.start_compose_project('pygen-actions', 'compose', 'action.yml', composefile)

        action = actions.Action(self.api)
        
        containers = list(action.matching_containers('actiontest'))

        self.assertEqual(len(containers), 1)

        project.get_service('actiontest').scale(3)

        containers = list(action.matching_containers('actiontest'))

        self.assertEqual(len(containers), 3)

    def test_restart_container(self):
        test_container = self.start_container()
        initial_start_time = test_container.attrs['State']['StartedAt']

        initial_containers = self.api.containers()

        self.assertIn(test_container.id, (c.id for c in initial_containers))

        self.api.run_action(actions.RestartAction, test_container.short_id)

        containers = self.api.containers()

        self.assertIn(test_container.id, (c.id for c in containers))

        test_container.reload()
        self.assertNotEqual(test_container.attrs['State']['StartedAt'], initial_start_time)

    def test_restart_multiple_containers(self):
        test_container_1 = self.start_container(environment=['PYGEN_TARGET=restart-test'])
        test_container_2 = self.start_container(environment=['PYGEN_TARGET=restart-test'])

        ids = (test_container_1.id, test_container_2.id)
        initial_start_times = tuple(c.attrs['State']['StartedAt'] for c in (test_container_1, test_container_2))

        containers = self.api.containers()
        
        for container_id in ids:
            self.assertIn(container_id, (c.id for c in containers))

        self.api.run_action(actions.RestartAction, 'restart-test')

        containers = self.api.containers()
        
        for container_id in ids:
            self.assertIn(container_id, (c.id for c in containers))
        
        test_container_1.reload()
        test_container_2.reload()

        start_times = tuple(c.attrs['State']['StartedAt'] for c in (test_container_1, test_container_2))

        for idx, start in enumerate(start_times):
            self.assertNotEqual(start, initial_start_times[idx])

    def test_restart_compose_service(self):
        composefile = """
        version: '2'
        services:
          actiontest:
            image: {image}
            command: "sleep 300"
        """.format(image=os.environ.get('TEST_IMAGE', 'alpine'))

        project = self.start_compose_project('pygen-actions', 'compose', 'action.yml', composefile)
        
        project.get_service('actiontest').scale(3)

        containers = self.api.containers()

        self.assertEqual(len(list(c for c in containers if 'actiontest' in c.name)), 3)

        initial_start_times = {c.name: c.raw.attrs['State']['StartedAt'] for c in containers if 'actiontest' in c.name}

        self.api.run_action(actions.RestartAction, 'actiontest')

        containers = self.api.containers()

        self.assertEqual(len(list(c for c in containers if 'actiontest' in c.name)), 3)

        start_times = {c.name: c.raw.attrs['State']['StartedAt'] for c in containers if 'actiontest' in c.name}

        for name, start in start_times.items():
            self.assertNotEqual(start, initial_start_times[name])

    def test_signal_action(self):
        test_container = self.start_container(command='sh -c "echo \'Starting...\'; trap \\"echo \'Signalled\'\\" SIGHUP && read"')

        logs = test_container.logs()

        self.assertIn('Starting...', logs)
        self.assertNotIn('Signalled', logs)
        
        self.api.run_action(actions.SignalAction, test_container.name, 'HUP')

        logs = test_container.logs()

        self.assertIn('Starting...', logs)
        self.assertIn('Signalled', logs)

    def test_signal_compose_service(self):
        composefile = """
        version: '2'
        services:
          actiontest:
            image: {image}
            command: sh -c "echo 'Starting...'; trap \\"echo 'Signalled'\\" SIGHUP && while [ true ]; do read; done"
            tty: true
        """.format(image=os.environ.get('TEST_IMAGE', 'alpine'))

        project = self.start_compose_project('pygen-actions', 'compose', 'action.yml', composefile)
        
        project.get_service('actiontest').scale(3)

        for container in self.api.containers():
            if container.labels.get('com.docker.compose.service', '') == 'actiontest':
                logs = container.raw.logs()

                self.assertIn('Starting...', logs)
                self.assertNotIn('Signalled', logs)

        self.api.run_action(actions.SignalAction, 'actiontest', 'HUP')
        
        for container in self.api.containers():
            if container.labels.get('com.docker.compose.service', '') == 'actiontest':
                logs = container.raw.logs()

                self.assertIn('Starting...', logs)
                self.assertIn('Signalled', logs)

