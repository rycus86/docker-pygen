import sys
import argparse

from pygen import PyGen


def parse_arguments(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Template generator based on Docker runtime information')

    parser.add_argument('--template',
                        help='The base Jinja2 template file or inline template as string if it starts with "#"')
    parser.add_argument('--target',
                        help='The target to save the generated file (/dev/stdout by default)')

    return parser.parse_args(args)


if __name__ == '__main__':  # pragma: no cover
    assert PyGen() is not None
