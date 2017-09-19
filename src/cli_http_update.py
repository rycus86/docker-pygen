import sys
import argparse
import httplib
import signal

from api import DockerApi
from utils import get_logger, set_log_level

logger = get_logger('pygen-cli-http-update')


def parse_arguments(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='PyGen cli to send HTTP updates on Docker events')

    parser.add_argument('host',
                        help='The target hostname for the main PyGen app')
    parser.add_argument('port', type=int,
                        help='The target HTTP port for the main PyGen app')

    return parser.parse_args(args)


def send_update(host, port):
    try:
        connection = httplib.HTTPConnection(host, port)
        connection.request('POST', '/')
        response = connection.getresponse()

        logger.info('Update sent to http://%s:%d/ : HTTP %s : %s',
                    host, port, response.status, response.read().strip())

    except Exception as ex:
        logger.error('Failed to send update to http://%s:%d/: %s',
                     host, port, ex, exc_info=1)


def setup_signals(host, port):  # pragma: no cover
    def exit_signal(*args):
        logger.info('Exiting ...')

        exit(0 if signal.SIGTERM else 1)

    signal.signal(signal.SIGTERM, exit_signal)
    signal.signal(signal.SIGINT, exit_signal)

    def update_signal(*args):
        send_update(host, port)

    signal.signal(signal.SIGHUP, update_signal)


def watch_events(host, port):
    api = DockerApi()
    
    logger.info('Starting event watch loop')

    for event in api.events(decode=True):
        if event.get('status') in ('start', 'stop', 'die'):
            send_update(host, port)


if __name__ == '__main__':  # pragma: no cover
    set_log_level('INFO')

    arguments = parse_arguments()

    setup_signals(arguments.host, arguments.port)

    watch_events(arguments.host, arguments.port)

