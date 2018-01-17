import re
import sys
import json
import signal
import argparse

import requests

from actions import Action
from api import DockerApi
from http_server import HttpServer
from metrics import MetricsServer, Counter
from utils import get_logger, set_log_level

logger = get_logger('pygen-worker')

request_counter = Counter(
    'pygen_worker_request_count', 'Number of requests handled by the Swarm worker',
    labelnames=('client',)
)
send_counter = Counter(
    'pygen_worker_send_count', 'Number of requests sent by the Swarm worker',
    labelnames=('target',)
)


class Worker(HttpServer):
    manager_port = 9411
    worker_port = 9412

    DEFAULT_EVENTS = ['start', 'stop', 'die', 'health_status']

    EMPTY_DICT = dict()

    def __init__(self, managers, retries=0, events=None, metrics_port=9414):
        super(Worker, self).__init__(self.worker_port)

        self.managers = managers
        self.retries = retries
        self.events = events or self.DEFAULT_EVENTS
        self.metrics = MetricsServer(metrics_port)

        self.api = DockerApi()

    def start(self):
        super(Worker, self).start()

        if self.metrics:
            self.metrics.start()

    def _handle_request(self, request):
        request_counter.labels(request.address_string()).inc()

        length = int(request.headers['Content-Length'])

        data = json.loads(request.rfile.read(length).decode('utf-8'))

        self.handle_action(data.get('action'), *data.get('args', list()))

    def handle_action(self, action_name, *args):
        action_type = Action.by_name(action_name)

        self.api.run_action(action_type, *args)

    def watch_events(self):
        for event in self.api.events(decode=True):
            if self.is_watched(event):
                logger.info('Received %s event from %s',
                            event.get('status'),
                            event.get('Actor', self.EMPTY_DICT).get('Attributes', self.EMPTY_DICT).get('name', '<?>'))

                self.send_update(event.get('status'))

    def is_watched(self, event):
        if event.get('status') in self.events:
            return True

        # health_status comes as 'health_status: healthy' for example
        if any(re.match(r'%s:.+' % item, event.get('status', '')) for item in self.events):
            return True

        return False

    def send_update(self, status):
        for manager in self.managers:
            for _ in range(self.retries + 1):
                try:
                    response = requests.post('http://%s:%d/' % (manager, self.manager_port), timeout=(5, 30))

                    logger.info('Update (%s) sent to http://%s:%d/ : HTTP %s : %s',
                                status, manager, self.manager_port, response.status_code, response.text.strip())

                    send_counter.labels(manager).inc()

                    break

                except Exception as ex:
                    logger.error('Failed to send update to http://%s:%d/: %s',
                                 manager, self.manager_port, ex, exc_info=1)

    def shutdown(self):
        super(Worker, self).shutdown()

        if self.metrics:
            self.metrics.shutdown()


def parse_arguments(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='PyGen cli to send HTTP updates on Docker events')

    parser.add_argument('--manager',
                        metavar='<HOSTNAME>', required=True, nargs='+',
                        help='The target hostname of the PyGen manager instance listening on port 9411')
    parser.add_argument('--retries',
                        required=False, type=int, default=0,
                        help='Number of retries for sending an update to the manager')

    parser.add_argument('--events',
                        metavar='<EVENT>', required=False, nargs='+',
                        default=['start', 'stop', 'die', 'health_status'],
                        help='Docker events to watch and trigger updates for '
                             '(default: start, stop, die, health_status)')

    parser.add_argument('--metrics',
                        metavar='<PORT>', required=False, type=int, default=9414,
                        help='HTTP port number for exposing Prometheus metrics (default: 9414)')

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

    worker = Worker(arguments.manager, arguments.retries, arguments.events, arguments.metrics)

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
