import unittest
from unittest_helper import BaseDockerTestCase

import pygen


class GeneratorTest(BaseDockerTestCase):
    def test_generate(self):
        test_container = self.start_container(environment=['GENERATOR=pygen'])

        app = pygen.PyGen(template="""#
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

    @unittest.skip('Needs passing the helper functions to Jinja2')  # TODO
    def test_generate_with_groups(self):
        self.start_container(environment=['GENERATOR=pygen'],
                             labels={'instance': '001',
                                     'application': 'web'})
        self.start_container(environment=['GENERATOR=pygen'],
                             labels={'instance': '002',
                                     'application': 'web'})
        self.start_container(environment=['GENERATOR=pygen'],
                             labels={'instance': '003',
                                     'application': 'db'})

        app = pygen.PyGen(template="""#
            {% for key, containers in group_by(containers, 'labels.application') %}
            group: {{ key }}
              {% for container in containers %}
              instance: {{ container.labels.instance }}
              {% endfor %}
            {% endfor %}""")

        content = app.generate()

        self.assertIn('group: web', content)
        self.assertIn('group: db', content)

        for num in xrange(1, 4):
            self.assertIn('instance: %03d' % num, content)

