import json
import socket

import six
from six.moves import http_client

from http_server import HttpServer
from utils import get_logger

logger = get_logger('pygen-http')


class Manager(HttpServer):
    manager_port = 9411
    worker_port = 9412

    def __init__(self, app, workers):
        super(Manager, self).__init__(self.manager_port)

        self.app = app
        self.workers = workers

    def _handle_request(self, request):
        self.app.update_target()

    def send_action(self, name, *args):
        data = six.b(json.dumps({'action': name, 'args': args}))

        for worker in self.workers:
            for _, _, _, _, socket_address in socket.getaddrinfo(worker, self.worker_port,
                                                                 socket.AF_INET, socket.SOCK_STREAM,
                                                                 socket.IPPROTO_TCP):
                address, port = socket_address

                self._send_action_request(address, port, data)

    @staticmethod
    def _send_action_request(address, port, data):
        try:
            connection = http_client.HTTPConnection(address, port)
            connection.request('POST', '/', body=data, headers={
                'Content-Type': 'application/json',
                'Content-Length': len(data)
            })
            response = connection.getresponse()

            logger.info('Action (%s) sent to http://%s:%d/ : HTTP %s : %s',
                        data['action'], address, port, response.status, response.read().strip())

        except Exception as ex:
            logger.error('Failed to send action to http://%s:%d/: %s',
                         address, port, ex, exc_info=1)
