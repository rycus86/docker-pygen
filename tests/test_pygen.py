import os
import unittest
import docker_helper

from unittest_helper import relative_path

import pygen
from metrics import MetricsServer


class PyGenTest(unittest.TestCase):
    def tearDown(self):
        MetricsServer.shutdown_current()

    def test_inline_template(self):
        app = pygen.PyGen(template='#{{ who }} {{ what }} use inline templates')

        self.assertIsNotNone(app.template)
        self.assertEqual('You can use inline templates', app.template.render(who='You', what='can'))
        self.assertEqual('I could use inline templates', app.template.render(who='I', what='could'))

    def test_template_from_file(self):
        app = pygen.PyGen(template=relative_path('templates/hello.txt'))

        self.assertIsNotNone(app.template)
        self.assertEqual('Hello world!', app.template.render(name='world'))
        self.assertEqual('Hello Jinja2!', app.template.render(name='Jinja2'))

    def test_template_from_absolute_file(self):
        app = pygen.PyGen(template=os.path.abspath(relative_path('templates/hello.txt')))

        self.assertIsNotNone(app.template)
        self.assertEqual('Hello world!', app.template.render(name='world'))
        self.assertEqual('Hello Jinja2!', app.template.render(name='Jinja2'))

    def test_template_from_url(self):
        url = 'https://raw.githubusercontent.com/rycus86/docker-pygen/master/tests/templates/hello.txt'
        app = pygen.PyGen(template=url)

        self.assertIsNotNone(app.template)
        self.assertEqual('Hello world!', app.template.render(name='world'))
        self.assertEqual('Hello Jinja2!', app.template.render(name='Jinja2'))

    def test_no_template_raises_error(self):
        self.assertRaises(pygen.PyGenException, pygen.PyGen, template=None)
        self.assertRaises(pygen.PyGenException, pygen.PyGen, unknown_key='x')

    def test_missing_template_raises_error(self):
        from jinja2 import TemplateNotFound
        self.assertRaises(TemplateNotFound, pygen.PyGen, template='missing/template.file')

    def test_lazy_in_templates(self):
        app = pygen.PyGen(template='#{% for c in all_containers %}'
                                   '{{ all_containers|length }}{{ c.name }}'
                                   '-{% set first = all_containers|first %}{{ first.id }}'
                                   '{% endfor %}')
        
        def mock_containers(*args, **kwargs):
            return [{'name': 'mocked', 'id': 12}]

        app.api.containers = mock_containers

        self.assertEqual('1mocked-12', app.generate())

    def test_read_config(self):
        app = pygen.PyGen(template='#c1={{ read_config("PYGEN_TEST_KEY") }} '
                                   'c2={{ read_config("PYGEN_CONF", "/tmp/pygen-conf-test") }} '
                                   'cd={{ read_config("PYGEN_DEFAULT", default="DefaultValue") }}')
        
        try:
            os.environ['PYGEN_TEST_KEY'] = 'from-env'

            with open('/tmp/pygen-conf-test', 'w') as config_file:
                config_file.write('PYGEN_CONF=from-file')

            content = app.generate()

            self.assertIn('c1=from-env', content)
            self.assertIn('c2=from-file', content)
            self.assertIn('cd=DefaultValue', content)

        finally:
            del os.environ['PYGEN_TEST_KEY']
            
            if os.path.exists('/tmp/pygen-conf-test'):
                os.remove('/tmp/pygen-conf-test')
    
    @unittest.skipUnless(os.path.exists('/proc/1/cgroup'),
                         'Test is not running in a container')
    def test_own_container_id(self):
        app = pygen.PyGen(template='#cid={{ own_container_id }}')
        container_id = docker_helper.get_current_container_id()

        self.assertEqual('cid=%s' % container_id, app.generate())

    def test_intervals(self):
        self.assertRaises(pygen.PyGenException, pygen.PyGen, template='#', interval=[1, 2, 3])
        self.assertRaises(pygen.PyGenException, pygen.PyGen, template='#', interval=[2, 1])

        app = pygen.PyGen(template='#', interval=[12, 40])

        self.assertEqual(app.timer.min_interval, 12)
        self.assertEqual(app.timer.max_interval, 40)

