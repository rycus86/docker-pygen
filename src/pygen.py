import argparse
import os
import sys

import jinja2

from api import *
from errors import *


class PyGen(object):
    def __init__(self, **kwargs):
        if not kwargs:
            kwargs = getattr(parse_arguments(), '__dict__')

        self.target_path = kwargs.get('target')
        self.template_source = kwargs.get('template')

        if not self.template_source:
            raise PyGenException('No template is defined')

        self.template = self._init_template(self.template_source)

        self.api = DockerApi()

    @staticmethod
    def _init_template(source):
        if source.startswith('#'):
            return jinja2.Template(source[1:].strip())

        else:
            template_directory, template_filename = os.path.split(os.path.abspath(source))

            jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(template_directory),
                                                   trim_blocks=True, lstrip_blocks=True,
                                                   extensions=['jinja2.ext.loopcontrols'])

            return jinja_environment.get_template(template_filename)

    def generate(self):
        containers = self.api.list()
        return self.template.render(containers=containers)


def parse_arguments(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Template generator based on Docker runtime information')

    parser.add_argument('--template',
                        help='The base Jinja2 template file or inline template as string if it starts with "#"')
    parser.add_argument('--target',
                        help='The target to save the generated file (/dev/stdout by default)')

    return parser.parse_args(args)


if __name__ == '__main__':  # pragma: no cover
    assert PyGen() is not None
