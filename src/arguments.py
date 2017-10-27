import argparse
import sys


def parse_arguments(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Template generator based on Docker runtime information')

    parser.add_argument('--template',
                        required=True,
                        help='The base Jinja2 template file or inline template as string if it starts with "#"')
    parser.add_argument('--target',
                        required=False,
                        help='The target to save the generated file (/dev/stdout by default)')

    parser.add_argument('--restart',
                        metavar='<CONTAINER>', required=False, action='append', default=list(),
                        help='Restart the target container, can be: '
                             'ID, short ID, name, Compose service name, '
                             'label ["pygen.target"] or environment variable ["PYGEN_TARGET"]')
    parser.add_argument('--signal',
                        metavar=('<CONTAINER>', '<SIGNAL>'), required=False, nargs=2, action='append', default=list(),
                        help='Signal the target container, in <container> <signal> format. '
                             'The <container> argument can be one of the attributes described in --restart')
    parser.add_argument('--interval',
                        metavar=('<MIN>', '<MAX>'), required=False, nargs='+', default=[0.5, 2], type=float,
                        help='Minimum and maximum intervals for sending notifications. '
                             'If there is only one argument it will be used for both MIN and MAX. '
                             'The defaults are: 0.5 and 2 seconds.')
    parser.add_argument('--events',
                        metavar='<EVENT>', required=False, nargs='+',
                        default=['start', 'stop', 'die', 'health_status'],
                        help='Docker events to watch and trigger updates for '
                             '(default: start, stop, die, health_status)')

    parser.add_argument('--swarm-manager',
                        required=False, action='store_true',
                        help='Enable the Swarm manager HTTP endpoint on port 9411')
    parser.add_argument('--workers',
                        metavar='<TARGET>', required=False, nargs='+',
                        default=list(),
                        help='The target hostname of PyGen workers listening on port 9412 '
                             '(use "tasks.service_name" for Swarm workers)')
    parser.add_argument('--retries',
                        required=False, type=int, default=0,
                        help='Number of retries for sending an action to a Swarm worker')

    parser.add_argument('--no-ssl-check',
                        required=False, action='store_true',
                        help='Disable SSL verification when loading templates over HTTPS (not secure)')

    parser.add_argument('--one-shot',
                        required=False, action='store_true',
                        help='Run the update once and exit, also execute actions if the target changes')

    parser.add_argument('--docker-address',
                        metavar='<ADDRESS>', required=False,
                        help='Alternative address (URL) for the Docker daemon connection')

    parser.add_argument('--debug',
                        required=False, action='store_true',
                        help='Enable debug log messages')

    return parser.parse_args(args)


if __name__ == '__main__':  # pragma: no cover
    print(parse_arguments())
