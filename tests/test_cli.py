import unittest

import cli


class CliTest(unittest.TestCase):
    def test_parse_arguments(self):
        args = cli.parse_arguments(['--template', 'test.template', '--target', '/etc/target.file'])

        self.assertEqual(args.template, 'test.template')
        self.assertEqual(args.target, '/etc/target.file')

    def test_parse_arguments_defaults(self):
        args = cli.parse_arguments(['--template', 'test.template'])

        self.assertEqual(args.template, 'test.template')
        self.assertIsNone(args.target, None)

    def test_parse_empty_arguments(self):
        args = cli.parse_arguments([])

        self.assertIsNone(args.template)
        self.assertIsNone(args.target)

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
                cli.parse_arguments(['--help'])

            except SystemExit as ex:
                self.assertEqual(0, ex.code)

            print sys.stdout.data
            self.assertIn('Template generator based on Docker runtime information', sys.stdout.data)

        finally:
            sys.stdout = sys_stdout
