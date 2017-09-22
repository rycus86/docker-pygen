import argparse
import json
import signal
import sys

import requests
import six

from actions import Action
from api import DockerApi
from http_server import HttpServer
from utils import get_logger, set_log_level

logger = get_logger('pygen-worker')


class Worker(HttpServer):
    manager_port = 9411
    worker_port = 9412

    def __init__(self, manager, retries=0):
        super(Worker, self).__init__(self.worker_port)

        self.manager = manager
        self.retries = retries

        self.api = DockerApi()

    def _handle_request(self, request):
        length = int(request.headers['Content-Length'])

        data = json.loads(six.u(request.rfile.read(length)))

        self.handle_action(data.get('action'), *data.get('args', list()))

    def handle_action(self, action_name, *args):
        action_type = Action.by_name(action_name)

        self.api.run_action(action_type, *args)

    def watch_events(self):
        for event in self.api.events(decode=True):
            if event.get('status') in ('start', 'stop', 'die'):
                self.send_update()

    def send_update(self):
        for _ in range(self.retries + 1):
            try:
                response = requests.post('http://%s:%d/' % (self.manager, self.manager_port), timeout=(5, 30))

                logger.info('Update sent to http://%s:%d/ : HTTP %s : %s',
                            self.manager, self.manager_port, response.status_code, response.text.strip())

                break

            except Exception as ex:
                logger.error('Failed to send update to http://%s:%d/: %s',
                             self.manager, self.manager_port, ex, exc_info=1)


def parse_arguments(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='PyGen cli to send HTTP updates on Docker events')

    parser.add_argument('--manager',
                        metavar='<HOSTNAME>', required=True,
                        help='The target hostname of the PyGen manager instance listening on port 9411')
    parser.add_argument('--retries',
                        required=False, type=int, default=0,
                        help='Number of retries for sending an update to the manager')

    parser.add_argument('--debug',
                        required=False, action='store_true',
                        help='Enable debug log messages')

    return parser.parse_args(args)


def setup_signals(worker):  # pragma: no cover
    def exit_signal(*args):
        logger.info('Exiting ...')

        exit(0 if signal.SIGTERM else 1)

    signal.signal(signal.SIGTERM, exit_signal)
    signal.signal(signal.SIGINT, exit_signal)

    def update_signal(*args):
        worker.send_update()

    signal.signal(signal.SIGHUP, update_signal)


if __name__ == '__main__':  # pragma: no cover
    set_log_level('INFO')

    arguments = parse_arguments()

    if arguments.debug:
        set_log_level('DEBUG')

    worker = Worker(arguments.manager, arguments.retries)

    setup_signals(worker)

    logger.debug('Signal handlers set up for SIGTERM, SIGINT and SIGHUP')

    try:
        worker.start()

        logger.info('Starting event watch loop')

        worker.watch_events()

    except SystemExit:
        logger.info('Exiting...')

        worker.shutdown()

        raise

    except Exception:
        worker.shutdown()

        raise
