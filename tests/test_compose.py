import os
import time
import json
import unittest
from compose.config.config import ConfigFile, ConfigDetails
from compose.config.config import load as load_config
from compose.project import Project
from unittest_helper import relative_path

import pygen


@unittest.skipIf(os.environ.get('TEST_IMAGE'), 'Skipping on non-x86 architectures')
class DockerComposeTests(unittest.TestCase):
    project = None

    def setUp(self):
        self.app = pygen.PyGen(template=relative_path('templates/mockserver.conf.json'))

    def tearDown(self):
        if self.project:
            self.project.down(False, True, True)

    def test_compose(self):
        config = ConfigFile.from_filename(relative_path('compose/sample.yml'))
        details = ConfigDetails(relative_path('compose'), [config])
        self.project = Project.from_config('pygen-test', load_config(details), self.app.api.client.api)
        
        self.project.up(detached=True)
        
        content = self.app.generate()

        print(content)
        
        parsed = json.loads(content)
        
        self.assertIn('server', parsed)
        self.assertIn('proxy', parsed['server'])

        hosts = parsed['server']['proxy']

        self.assertEquals(len(hosts), 2)

        for host in hosts:
            self.assertIn('host', host)
            self.assertIn(host['host'], ('api.sample.com', 'www.sample.com'))

