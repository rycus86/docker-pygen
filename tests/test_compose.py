import unittest
from compose.config.config import ConfigFile, ConfigDetails
from compose.config.config import load as load_config
from compose.project import Project
from unittest_helper import relative_path

import pygen


@unittest.skip
class DockerComposeTests(unittest.TestCase):
    def setUp(self):
        self.app = pygen.PyGen(template=relative_path('templates/mockserver.conf.json'))

    def test_compose(self):
        config = ConfigFile.from_filename(relative_path('compose/sample.yml'))
        details = ConfigDetails(relative_path('compose'), [config])
        project = Project.from_config('pygen-test', load_config(details), self.app.api.client.api)

        project.up(detached=False)

        try:
            import time
            for _ in range(10):
                print(self.app.api.list())
                time.sleep(0.5)

            project.down()

        except:
            pass
