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
