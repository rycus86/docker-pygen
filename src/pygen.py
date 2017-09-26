import os
import threading

from actions import RestartAction, SignalAction
from api import *
from errors import *
from http_manager import Manager
from templates import initialize_template
from timer import NotificationTimer
from utils import get_logger

logger = get_logger('pygen')


class PyGen(object):
    EMPTY_DICT = dict()
    EMPTY_LIST = list()

    DEFAULT_INTERVALS = [0.5, 2]
    DEFAULT_EVENTS = ['start', 'stop', 'die']

    def __init__(self, **kwargs):
        self.target_path = kwargs.get('target')
        self.template_source = kwargs.get('template')
        self.restart_targets = kwargs.get('restart', self.EMPTY_LIST)
        self.signal_targets = kwargs.get('signal', self.EMPTY_LIST)
        self.events = kwargs.get('events', self.DEFAULT_EVENTS)
        self.one_shot = kwargs.get('one_shot', False)
        self.update_lock = threading.Lock()

        logger.debug('Targets to restart on changes: [%s]',
                     ', '.join(self.restart_targets))
        logger.debug('Targets to signal on changes: [%s]',
                     ', '.join('%s <%s>' % (target, signal) for target, signal in self.signal_targets))

        if not self.template_source:
            raise PyGenException('No template is defined')

        else:
            self.template = initialize_template(self.template_source)

            logger.debug('Template successfully initialized')

        intervals = kwargs.get('interval', self.DEFAULT_INTERVALS)

        if self.one_shot:
            intervals = [0]

            logger.debug('One-shot mode: actions will be executed immediately after the update')

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

        self.api = DockerApi(kwargs.get('docker_address'))

        logger.debug('Successfully connected to the Docker API')

        if kwargs.get('swarm_manager', False):
            if self.one_shot:
                raise PyGenException('Swarm manager is not available in one-shot mode')

            workers = kwargs.get('workers', self.EMPTY_LIST)
            retries = kwargs.get('retries', 0)

            self.swarm_manager = Manager(self, workers, retries)
            self.swarm_manager.start()

        else:
            self.swarm_manager = None

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
            self.api.run_action(RestartAction, target, manager=self.swarm_manager)

    def _signal_targets(self):
        for target, signal in self.signal_targets:
            self.api.run_action(SignalAction, target, signal, manager=self.swarm_manager)

    def watch(self, **kwargs):
        if self.one_shot:
            logger.info('Not watching events in one-shot mode')

            return

        kwargs['decode'] = True

        for event in self.api.events(**kwargs):
            if event.get('status') in self.events:
                logger.info('Received %s event from %s',
                            event.get('status'),
                            event.get('Actor', self.EMPTY_DICT).get('Attributes', self.EMPTY_DICT).get('name', '<?>'))

                self.update_target()

    def stop(self):
        if self.swarm_manager:
            self.swarm_manager.shutdown()
