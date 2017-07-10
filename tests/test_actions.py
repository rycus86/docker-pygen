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

