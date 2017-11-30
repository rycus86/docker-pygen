from docker.errors import DockerException

from errors import PyGenException
from metrics import Summary
from utils import get_logger

logger = get_logger('pygen-actions')

# metrics
execution_strategy_summary = Summary(
    'pygen_action_execution_strategy_seconds', 'Action execution metrics by strategy',
    labelnames=('strategy',)
)
restart_action_summary = Summary(
    'pygen_restart_action_seconds', 'Restart action metrics',
    labelnames=('target',)
)
signal_action_summary = Summary(
    'pygen_signal_action_seconds', 'Signal action metrics',
    labelnames=('target', 'signal')
)


_registered_actions = dict()


def register(name, strategy=None):
    def wrapper(cls):
        cls.action_name = name

        if strategy:
            cls.execution_strategy = strategy

        _registered_actions[name] = cls
        
        return cls

    return wrapper


class ExecutionStrategy(object):
    LOCAL = 1
    WORKER = 2
    MANAGER = 4


class Action(object):
    action_name = None
    execution_strategy = ExecutionStrategy.LOCAL | ExecutionStrategy.WORKER

    def __init__(self, api, swarm_manager=None):
        self.api = api
        self.manager = swarm_manager

    @classmethod
    def by_name(cls, name):
        if name not in _registered_actions:
            raise PyGenException('Unknown action: %s' % name)

        return _registered_actions[name]

    def execute(self, *args):
        try:
            if self.manager:
                if self.execution_strategy & ExecutionStrategy.WORKER:
                    logger.debug('Executing %s action on workers', self.action_name)

                    with execution_strategy_summary.labels('worker').time():
                        self.manager.send_action(self.action_name, *args)

                if self.execution_strategy & ExecutionStrategy.MANAGER:
                    logger.debug('Executing %s action on the Swarm manager', self.action_name)

                    with execution_strategy_summary.labels('manager').time():
                        self.process(*args)
            
            if not self.manager or self.execution_strategy & ExecutionStrategy.LOCAL:
                logger.debug('Executing %s action locally', self.action_name)

                with execution_strategy_summary.labels('local').time():
                    self.process(*args)

        except Exception as ex:
            logger.error('Failed to execute %s action: %s', self.action_name, ex, exc_info=1)

    def process(self, *args):
        raise PyGenException('Action not defined')

    def matching_services(self, target):
        return self.api.services().matching(target)

    def matching_containers(self, target):
        return self.api.containers().matching(target)


@register('restart', ExecutionStrategy.MANAGER)
class RestartAction(Action):
    def process(self, target):
        with restart_action_summary.labels(target).time():
            self._process(target)

    def _process(self, target):
        found_services = 0

        for service in self.matching_services(target):
            docker_api_client = self.api.client.api

            try:
                if service.update_service(docker_api_client, force_update=True):
                    logger.info('Service restarted: %s', service.name)

                else:
                    logger.info('Failed to restart service: %s', service.name)

                found_services += 1

            except DockerException as ex:
                logger.error('Failed to restart service %s: %s', service.name, ex, exc_info=1)

        if found_services:
            logger.debug('Found %d service(s) to restart, not checking containers', found_services)

            return

        if self.manager:
            logger.info('Sending restart event to workers for %s', target)

            self.manager.send_action(self.action_name, target)

            return

        for container in self.matching_containers(target):
            try:
                logger.info('Restarting container %s', container.name)

                container.raw.restart()

            except DockerException as ex:
                logger.error('Failed to restart container %s: %s', container.name, ex, exc_info=1)


@register('signal', ExecutionStrategy.WORKER)
class SignalAction(Action):
    def process(self, target, signal):
        with signal_action_summary.labels(target, signal).time():
            self._process(target, signal)

    def _process(self, target, signal):
        for service in self.matching_services(target):
            logger.warn('Not signalling service %s - this is only available for containers', service.name)

        for container in self.matching_containers(target):
            try:
                logger.info('Signalling container %s : %s', container.name, signal)

                container.raw.kill(signal=signal)

            except DockerException as ex:
                logger.error('Failed to signal [%s] container %s: %s', signal, container.name, ex, exc_info=1)
