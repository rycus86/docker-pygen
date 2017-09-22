import socket

import requests

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

        data = {'action': name, 'args': args}

        for worker in self.workers:
            signalled_hosts = set()

            try:
                for address_info in socket.getaddrinfo(worker, self.worker_port,
                                                       socket.AF_INET, socket.SOCK_STREAM,
                                                       socket.IPPROTO_TCP):

                    _, _, _, _, socket_address = address_info
                    address, port = socket_address

                    if address in signalled_hosts:
                        continue

                    for _ in range(self.retries + 1):
                        try:
                            status, response = self._send_action_request(address, port, data)

                            if status == 200:
                                logger.info('Action (%s) sent to http://%s:%d/ : HTTP %s : %s',
                                            name, address, port, status, response)
                                
                                signalled_hosts.add(address)

                                break

                            else:
                                logger.error('Failed to send %s action to http://%s:%d/ : HTTP %s : %s',
                                             name, address, port, status, response)

                        except Exception as ex:
                            logger.error('Failed to send %s action to http://%s:%d/ : %s',
                                         name, address, port, ex, exc_info=1)

            except Exception as ex:
                logger.error('Failed to send %s action to http://%s:%d/ : %s',
                             name, worker, self.worker_port, ex, exc_info=1)

    @staticmethod
    def _send_action_request(address, port, data):
        response = requests.post('http://%s:%d/' % (address, port), json=data, timeout=(5, 30))

        return response.status_code, response.text.strip()
