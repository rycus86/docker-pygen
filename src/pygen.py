import os

import jinja2

from api import *
from errors import *


class PyGen(object):
    def __init__(self, **kwargs):
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

    def update_target(self):
        existing_content = ''

        if os.path.exists(self.target_path):
            with open(self.target_path, 'r') as target:
                existing_content = target.read()

        content = self.generate()

        if content == existing_content:
            return

        with open(self.target_path, 'w') as target:
            target.write(content)

        self.signal()

    def signal(self):
        pass

    def watch(self, **kwargs):
        kwargs['decode'] = True

        for event in self.api.events(**kwargs):
            if event.get('status') in ('start', 'stop', 'die'):
                self.update_target()
