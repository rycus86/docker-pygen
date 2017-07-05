import tempfile
from unittest_helper import BaseDockerTestCase

import pygen


class UpdateTest(BaseDockerTestCase):
    def setUp(self):
        super(UpdateTest, self).setUp()

        self.target_file = tempfile.NamedTemporaryFile()
        self.target_path = self.target_file.name

    def tearDown(self):
        super(UpdateTest, self).tearDown()

        self.target_file.close()

    def test_updates_target(self):
        app = pygen.PyGen(target=self.target_path,
                          template="""#
            {% for container in containers %}
                {{ container.name }}
            {% endfor %}""")

        c1 = self.start_container()

        self.assertIn(c1.name, app.generate())

        # TODO update the target file 
