import docker

from models import ContainerInfo, ServiceInfo
from resources import ContainerList, ServiceList
from utils import EnhancedDict, Lazy


class DockerApi(object):
    def __init__(self):
        self.client = docker.DockerClient()

    @property
    def is_swarm_mode(self):
        return len(self.client.swarm.attrs) > 0

    def containers(self, **kwargs):
        return ContainerList(ContainerInfo(c) for c in self.client.containers.list(**kwargs))

    def services(self, desired_task_state='running', **kwargs):
        if self.is_swarm_mode:
            return ServiceList(ServiceInfo(s, desired_task_state) for s in self.client.services.list(**kwargs))

        else:
            return ServiceList()

    @property
    def state(self):
        return EnhancedDict(containers=self.containers(),
                            services=self.services(),
                            all_containers=Lazy(self.containers, all=True),
                            all_services=Lazy(self.services, desired_task_state=''))

    def events(self, **kwargs):
        for event in self.client.events(**kwargs):
            yield event

    def run_action(self, action_type, *args, **kwargs):
        action = action_type(self, swarm_manager=kwargs.get('manager'))
        action.execute(*args, **kwargs)

    def close(self):
        self.client.api.close()
