from docker.errors import DockerException

from errors import PyGenException
from utils import get_logger

logger = get_logger('pygen-actions')


class Action(object):
    def __init__(self, api):
        self.api = api

    def execute(self, *args, **kwargs):
        try:
            self._execute(*args, **kwargs)

        except Exception as ex:
            logger.error('Failed to execute %s: %s', type(self).__name__, ex, exc_info=1)

    def _execute(self, *args, **kwargs):
        raise PyGenException('Action not defined')

    def matching_services(self, target):
        if not self.api.is_swarm_mode:
            return

        for service in self.api.services():
            # check by explicit label
            if target == service.labels.get('pygen.target', ''):
                yield service

            # check by plain services
            elif target in (service.id, service.short_id, service.name):
                yield service

    def matching_containers(self, target):
        for container in self.api.containers():
            # check by explicit label
            if target == container.labels.get('pygen.target', ''):
                yield container

            # check by explicit environment variable
            elif target == container.env.get('PYGEN_TARGET', ''):
                yield container

            # check by plain containers
            elif target in (container.id, container.short_id, container.name):
                yield container

            # check compose services
            elif target == container.labels.get('com.docker.compose.service', ''):
                yield container


class RestartAction(Action):
    _services_ready = False

    def _execute(self, target):
        found_services = False

        for service in self.matching_services(target):
            if not self._services_ready:
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


class SignalAction(Action):
    def _execute(self, target, signal):
        for service in self.matching_services(target):
            logger.warn('Not signalling service %s - this is only available for containers', service.name)

        for container in self.matching_containers(target):
            try:
                logger.info('Signalling container %s : %s', container.name, signal)

                container.raw.kill(signal=signal)

            except DockerException as ex:
                logger.error('Failed to signal [%s] container %s: %s', signal, container.name, ex, exc_info=1)
