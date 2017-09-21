import unittest

import requests

import pygen


class HttpManagerTest(unittest.TestCase):
    def setUp(self):
        self.generate_count = 0

        self.app = pygen.PyGen(template='#', swarm_manager=True)

        def counting_generate():
            self.generate_count += 1
            return 'Generated %d times' % self.generate_count

        self.app.generate = counting_generate

    def tearDown(self):
        self.app.stop()

    def test_http_post_triggers_update(self):
        status, data = self._call_updater()

        self.assertEqual(200, status)
        self.assertEqual('OK', data)

        self.assertEqual(1, self.generate_count)

    def test_multiple_calls(self):
        self._call_updater()
        self._call_updater()
        self._call_updater()

        self.assertEqual(3, self.generate_count)

    def _call_updater(self):
        response = requests.post('http://localhost:%d' % self.app.swarm_manager.port)

        return response.status_code, response.text.strip()
