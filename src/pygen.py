import os
import threading

import jinja2

from actions import RestartAction, SignalAction
from api import *
from errors import *
from http_updater import HttpServer
from timer import NotificationTimer
from utils import get_logger

logger = get_logger('pygen')


class PyGen(object):
    EMPTY_DICT = dict()
    EMPTY_LIST = list()

    DEFAULT_INTERVALS = [0.5, 2]

    def __init__(self, **kwargs):
        self.target_path = kwargs.get('target')
        self.template_source = kwargs.get('template')
        self.restart_targets = kwargs.get('restart', self.EMPTY_LIST)
        self.signal_targets = kwargs.get('signal', self.EMPTY_LIST)
        self.update_lock = threading.Lock()

        logger.debug('Targets to restart on changes: [%s]',
                     ', '.join(self.restart_targets))
        logger.debug('Targets to signal on changes: [%s]',
                     ', '.join('%s <%s>' % (target, signal) for target, signal in self.signal_targets))

        if not self.template_source:
            raise PyGenException('No template is defined')

        else:
            self.template = self._initialize_template(self.template_source)

            logger.debug('Template successfully initialized')

        intervals = kwargs.get('interval', self.DEFAULT_INTERVALS)

        if len(intervals) > 2:
            raise PyGenException('Invalid intervals, see help for usage')

        if len(intervals) == 1:
            min_interval = max_interval = intervals[0]

        else:
            min_interval, max_interval = intervals

            if min_interval > max_interval:
                raise PyGenException('Invalid min/max intervals: %.2f > %.2f' % (min_interval, max_interval))

        logger.debug('Notification intervals set as min=%.2f max=%.2f', min_interval, max_interval)

        self.timer = NotificationTimer(self.signal, min_interval, max_interval)

        self.api = DockerApi()

        logger.debug('Successfully connected to the Docker API')

        if kwargs.get('http') is not None:
            self.httpd = HttpServer(self, **kwargs)
            self.httpd.start()

        else:
            self.httpd = None

    @staticmethod
    def _initialize_template(source):
        jinja_env_options = {
            'trim_blocks': True,
            'lstrip_blocks': True,
            'extensions': ['jinja2.ext.loopcontrols']
        }

        if source.startswith('#'):
            template_filename = 'inline'

            jinja_environment = jinja2.Environment(loader=jinja2.DictLoader({template_filename: source[1:].strip()}),
                                                   **jinja_env_options)

        else:
            template_directory, template_filename = os.path.split(os.path.abspath(source))

            jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(template_directory),
                                                   **jinja_env_options)

        jinja_environment.filters.update({
            'any': any,
            'all': all
        })

        logger.debug('Loading Jinja2 template from: %s', template_filename)

        return jinja_environment.get_template(template_filename)

    def generate(self):
        state = self.api.state

        logger.debug('Generating content based on information from %s containers and %s services',
                     len(state.containers), len(state.services))

        return self.template.render(**state)

    def update_target(self):
        if not self.target_path:
            logger.info('Printing generated content to stdout')

            print(self.generate())
            self.timer.schedule()

            return

        with self.update_lock:
            if not self._update_target_file():
                return

        self.timer.schedule()

    def _update_target_file(self):
        logger.info('Updating target file at %s', self.target_path)

        existing_content = ''

        if os.path.exists(self.target_path):
            with open(self.target_path, 'r') as target:
                existing_content = target.read()

        content = self.generate()

        if content == existing_content:
            logger.info('Skip updating target file, contents have not changed')

            return False

        with open(self.target_path, 'w') as target:
            target.write(content)

        logger.info('Target file updated at %s', self.target_path)

        return True

    def signal(self):
        logger.info('Sending notifications')

        self._restart_targets()
        self._signal_targets()

    def _restart_targets(self):
        for target in self.restart_targets:
            self.api.run_action(RestartAction, target)

    def _signal_targets(self):
        for target, signal in self.signal_targets:
            self.api.run_action(SignalAction, target, signal)

    def watch(self, **kwargs):
        kwargs['decode'] = True

        for event in self.api.events(**kwargs):
            if event.get('status') in ('start', 'stop', 'die'):
                logger.info('Received %s event from %s',
                            event.get('status'),
                            event.get('Actor', self.EMPTY_DICT).get('Attributes', self.EMPTY_DICT).get('name', '<?>'))

                self.update_target()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
