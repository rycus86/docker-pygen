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

    def __init__(self, app, workers, retries=0):
        super(Manager, self).__init__(self.manager_port)

        self.app = app
        self.workers = workers
        self.retries = retries

    def _handle_request(self, request):
        self.app.update_target()

    def send_action(self, name, *args):
        logger.debug('Sending %s action to workers: %s', name, ', '.join(self.workers))

        data = six.b(json.dumps({'action': name, 'args': args}))

        for worker in self.workers:
            try:
                for address_info in socket.getaddrinfo(worker, self.worker_port,
                                                       socket.AF_INET, socket.SOCK_STREAM,
                                                       socket.IPPROTO_TCP):

                    _, _, _, _, socket_address = address_info
                    address, port = socket_address

                    for _ in range(self.retries):
                        try:
                            status, response = self._send_action_request(address, port, data)

                            if status == 200:
                                logger.info('Action (%s) sent to http://%s:%d/ : HTTP %s : %s',
                                            name, address, port, status, response)

                                break

                            else:
                                logger.error('Failed to send %s action to http://%s:%d/ : HTTP %s : %s',
                                             name, address, port, status, response)

                        except Exception as ex:
                            logger.error('Failed to send %s action to http://%s:%d/: %s',
                                         name, address, port, ex, exc_info=1)

            except Exception as ex:
                logger.error('Failed to send %s action to http://%s:%d/: %s',
                             name, worker, self.worker_port, ex, exc_info=1)

    @staticmethod
    def _send_action_request(address, port, data):
        connection = http_client.HTTPConnection(address, port, timeout=30)
        connection.request('POST', '/', body=data, headers={
            'Content-Type': 'application/json',
            'Content-Length': len(data)
        })
        response = connection.getresponse()

        return response.status, response.read().strip()
