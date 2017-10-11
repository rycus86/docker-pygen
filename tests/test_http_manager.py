import unittest

import socket
import requests

import pygen
import http_manager


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

    def test_retries(self):
        manager = http_manager.Manager(None, ['test'], 3)

        calls = list()

        def mock_action(*args):
            calls.append(1)
            return 500, 'Error'
        
        manager._send_action_request = mock_action

        def mock_getaddrinfo(*args):
            yield (0, 0, 0, 0, ('test-host', 1234))
        
        original_getaddrinfo = socket.getaddrinfo

        try:
            socket.getaddrinfo = mock_getaddrinfo

            manager.send_action('signal', 'test', 'HUP')

            self.assertEqual(4, sum(calls))

        finally:
            socket.getaddrinfo = original_getaddrinfo

