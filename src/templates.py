import os
import re

import jinja2
import requests

from utils import get_logger

logger = get_logger('pygen-templates')


class HttpLoader(jinja2.BaseLoader):
    def __init__(self, disable_ssl_verification):
        self.verify_ssl = not disable_ssl_verification

    def get_source(self, environment, template):
        response = requests.get(template, verify=self.verify_ssl, timeout=60)

        if response.ok:
            template_source = response.text

        else:
            raise jinja2.TemplateNotFound(template)

        return template_source, None, lambda: False


def initialize_template(source, **kwargs):
    jinja_env_options = {
        'trim_blocks': True,
        'lstrip_blocks': True,
        'extensions': ['jinja2.ext.loopcontrols']
    }

    log = logger.debug

    if source.startswith('#'):
        template_filename = 'inline'

        jinja_environment = jinja2.Environment(loader=jinja2.DictLoader({template_filename: source[1:].strip()}),
                                               **jinja_env_options)

    elif re.match(r'^https?://[^.]+\..+', source, re.IGNORECASE):
        template_filename = source

        jinja_environment = jinja2.Environment(loader=HttpLoader(kwargs.get('no_ssl_check', False)),
                                               **jinja_env_options)

        log = logger.info

    else:
        template_directory, template_filename = os.path.split(os.path.abspath(source))

        jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(template_directory),
                                               **jinja_env_options)

    jinja_environment.filters.update({
        'any': any,
        'all': all
    })

    log('Loading Jinja2 template from: %s', template_filename)

    return jinja_environment.get_template(template_filename)
