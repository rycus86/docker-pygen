import os
import unittest

import pygen


def relative(path):
    return os.path.join(os.path.dirname(__file__), path)


class CliTest(unittest.TestCase):
    def test_parse_arguments(self):
        args = pygen.parse_arguments(['--template', 'test.template', '--target', '/etc/target.file'])

        self.assertEqual(args.template, 'test.template')
        self.assertEqual(args.target, '/etc/target.file')

    def test_parse_arguments_defaults(self):
        args = pygen.parse_arguments(['--template', 'test.template'])

        self.assertEqual(args.template, 'test.template')
        self.assertIsNone(args.target, None)

    def test_parse_empty_arguments(self):
        args = pygen.parse_arguments([])

        self.assertIsNone(args.template)
        self.assertIsNone(args.target)

    def test_inline_template(self):
        app = pygen.PyGen(template='#{{ who }} {{ what }} use inline templates')

        self.assertIsNotNone(app.template)
        self.assertEqual('You can use inline templates', app.template.render(who='You', what='can'))
        self.assertEqual('I could use inline templates', app.template.render(who='I', what='could'))

    def test_template_from_file(self):
        app = pygen.PyGen(template=relative('templates/hello.txt'))

        self.assertIsNotNone(app.template)
        self.assertEqual('Hello world!', app.template.render(name='world'))
        self.assertEqual('Hello Jinja2!', app.template.render(name='Jinja2'))

    def test_template_from_absolute_file(self):
        app = pygen.PyGen(template=os.path.abspath(relative('templates/hello.txt')))

        self.assertIsNotNone(app.template)
        self.assertEqual('Hello world!', app.template.render(name='world'))
        self.assertEqual('Hello Jinja2!', app.template.render(name='Jinja2'))

    def test_no_template_raises_error(self):
        self.assertRaises(pygen.PyGenException, pygen.PyGen, template=None)
        self.assertRaises(pygen.PyGenException, pygen.PyGen, unknown_key='x')

    def test_missing_template_raises_error(self):
        from jinja2 import TemplateNotFound
        self.assertRaises(TemplateNotFound, pygen.PyGen, template='missing/template.file')

    def test_prints_help(self):
        import sys
        sys_stdout = sys.stdout

        try:
            class _CapturingOutput(object):
                def __init__(self):
                    self.data = ''

                def write(self, data):
                    self.data += data

            sys.stdout = _CapturingOutput()

            try:
                pygen.parse_arguments(['--help'])

            except SystemExit as ex:
                self.assertEqual(0, ex.code)

            print sys.stdout.data
            self.assertIn('Template generator based on Docker runtime information', sys.stdout.data)

        finally:
            sys.stdout = sys_stdout
