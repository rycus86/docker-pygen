import argparse
import signal
import sys

from pygen import PyGen
from utils import get_logger, set_log_level

logger = get_logger('pygen-cli')


def parse_arguments(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Template generator based on Docker runtime information')

    parser.add_argument('--template',
                        help='The base Jinja2 template file or inline template as string if it starts with "#"')
    parser.add_argument('--target',
                        help='The target to save the generated file (/dev/stdout by default)')
    parser.add_argument('--restart',
                        metavar='<CONTAINER>', required=False, action='append',
                        help='Restart the target container, can be: '
                             'ID, short ID, name, Compose service name, '
                             'label ["pygen.target"] or environment variable ["PYGEN_TARGET"]')
    parser.add_argument('--signal',
                        metavar=('<CONTAINER>', '<SIGNAL>'), required=False, nargs=2, action='append',
                        help='Signal the target container, in <container> <signal> format. '
                             'The <container> argument can be one of the attributes described in --restart')

    return parser.parse_args(args)


def handle_signal(num, _):  # pragma: no cover
    if num == signal.SIGTERM:
        exit(0)

    else:
        exit(1)


if __name__ == '__main__':  # pragma: no cover
    set_log_level('INFO')

    kwargs = parse_arguments().__dict__

    app = PyGen(**kwargs)
    app.update_target()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        app.watch()

    except SystemExit:
        logger.info('Exiting...')
        raise
