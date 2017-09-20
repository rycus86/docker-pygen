from docker.errors import DockerException

from errors import PyGenException
from utils import get_logger

logger = get_logger('pygen-actions')

_registered_actions = dict()


def register(name):
    def wrapper(cls):
        cls.action_name = name
        _registered_actions[name] = cls
        return cls

    return wrapper


class Action(object):
    action_name = None

    def __init__(self, api):
        self.api = api

    @classmethod
    def by_name(cls, name):
        if name not in _registered_actions:
            raise PyGenException('Unknown action: %s' % name)

        return _registered_actions[name]

    def execute(self, *args, **kwargs):
        try:
            logger.debug('Executing %s action', self.action_name)

            self.process(*args, **kwargs)

        except Exception as ex:
            logger.error('Failed to execute %s action: %s', self.action_name, ex, exc_info=1)

    def process(self, *args, **kwargs):
        raise PyGenException('Action not defined')

    def matching_services(self, target):
        return self.api.services().matching(target)

    def matching_containers(self, target):
        return self.api.containers().matching(target)


@register('restart')
class RestartAction(Action):
    _services_ready = False

    def process(self, target):
        found_services = False

        for service in self.matching_services(target):
            if not self._services_ready:
                logger.warn('Not restarting services - this is not available yet')
                break  # this is not working yet

            found_services = True

            # TODO need to find a reliable way to restart services with docker-py

        if found_services:
            return

        for container in self.matching_containers(target):
            try:
                logger.info('Restarting container %s', container.name)

                container.raw.restart()

            except DockerException as ex:
                logger.error('Failed to restart container %s: %s', container.name, ex, exc_info=1)


@register('signal')
class SignalAction(Action):
    def process(self, target, signal):
        for service in self.matching_services(target):
            logger.warn('Not signalling service %s - this is only available for containers', service.name)

        for container in self.matching_containers(target):
            try:
                logger.info('Signalling container %s : %s', container.name, signal)

                container.raw.kill(signal=signal)

            except DockerException as ex:
                logger.error('Failed to signal [%s] container %s: %s', signal, container.name, ex, exc_info=1)
