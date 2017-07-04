import unittest
from unittest_helper import BaseDockerTestCase

import cli


class GeneratorTest(BaseDockerTestCase):
    def test_generate(self):
        test_container = self.start_container(environment=['GENERATOR=pygen'])

        app = cli.App(template="""#
            {% for container in containers %}
            running: {{ container.name }} ID={{ container.short_id }}
              {% for key, value in container.env.items() %}
              env: {{ key }}=>{{ value }}
              {% endfor %}
            {% endfor %}""")

        content = app.generate()

        self.assertIn('running: %s' % test_container.name, content)
        self.assertIn('ID=%s' % test_container.short_id, content)
        self.assertIn('env: GENERATOR=>pygen', content)
