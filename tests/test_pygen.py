import os
import unittest

import pygen
from unittest_helper import relative_path


class PyGenTest(unittest.TestCase):
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
