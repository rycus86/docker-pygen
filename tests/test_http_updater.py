import unittest

import six
from six.moves import http_client

import pygen


class HttpUpdaterTest(unittest.TestCase):
    def setUp(self):
        self.generate_count = 0

        self.app = pygen.PyGen(template='#testing', http=0)

        def counting_generate():
            self.generate_count += 1
            return 'Generated %d times' % self.generate_count

        self.app.generate = counting_generate

    def tearDown(self):
        self.app.stop()

    def test_http_post_triggers_update(self):
        response = self._call_updater()

        self.assertEqual(200, response.status)
        self.assertEqual(six.b('OK'), response.read().strip())

        self.assertEqual(1, self.generate_count)

    def test_multiple_calls(self):
        self._call_updater()
        self._call_updater()
        self._call_updater()

        self.assertEqual(3, self.generate_count)

    def _call_updater(self):
        connection = http_client.HTTPConnection('localhost', self.app.httpd.port)
        connection.request('POST', '/')
        return connection.getresponse()
