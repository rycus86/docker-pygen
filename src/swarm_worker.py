import argparse
import json
import signal
import sys

from six.moves import http_client

from actions import Action
from api import DockerApi
from http_server import HttpServer
from utils import get_logger, set_log_level

logger = get_logger('pygen-worker')


class Worker(HttpServer):
    manager_port = 9411
    worker_port = 9412

    def __init__(self, manager):
        super(Worker, self).__init__(self.worker_port)

        self.manager = manager
        self.api = DockerApi()

    def _handle_request(self, request):
        data = json.load(request.rfile)

        self.handle_action(data.get('action'), *data.get('args', list()))

    def handle_action(self, action_name, *args):
        action_type = Action.by_name(action_name)

        self.api.run_action(action_type, *args)

    def watch_events(self):
        for event in self.api.events(decode=True):
            if event.get('status') in ('start', 'stop', 'die'):
                self.send_update()

    def send_update(self):
        try:
            connection = http_client.HTTPConnection(self.manager, self.manager_port)
            connection.request('POST', '/')
            response = connection.getresponse()

            logger.info('Update sent to http://%s:%d/ : HTTP %s : %s',
                        self.manager, self.manager_port, response.status, response.read().strip())

        except Exception as ex:
            logger.error('Failed to send update to http://%s:%d/: %s',
                         self.manager, self.manager_port, ex, exc_info=1)


def parse_arguments(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='PyGen cli to send HTTP updates on Docker events')

    parser.add_argument('--manager',
                        metavar='<HOSTNAME>', required=True,
                        help='The target hostname of the PyGen manager instance listening on port 9411')

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

    worker = Worker(arguments.manager)

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
