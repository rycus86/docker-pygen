import os

import docker

from metrics import Histogram
from models import ContainerInfo, ServiceInfo, NodeInfo
from resources import ContainerList, ServiceList, ResourceList
from utils import EnhancedDict, Lazy


# metrics
containers_histogram = Histogram(
    'pygen_api_containers_seconds', 'API call metrics for listing containers',
    labelnames=('list_all',)
)
services_histogram = Histogram(
    'pygen_api_services_seconds', 'API call metrics for listing services',
    labelnames=('desired_state',)
)
nodes_histogram = Histogram(
    'pygen_api_nodes_seconds', 'API call metrics for listing Swarm nodes'
)


class DockerApi(object):
    def __init__(self, address=os.environ.get('DOCKER_ADDRESS')):
        self.client = docker.DockerClient(address, version='auto')

    @property
    def is_swarm_mode(self):
        return len(self.client.swarm.attrs) > 0

    def containers(self, **kwargs):
        with containers_histogram.labels('1' if kwargs.get('all') else '0').time():
            return ContainerList(ContainerInfo(c) for c in self.client.containers.list(**kwargs))

    def services(self, desired_task_state='running', **kwargs):
        if self.is_swarm_mode:
            with services_histogram.labels(desired_task_state).time():
                return ServiceList(ServiceInfo(s, desired_task_state=desired_task_state)
                                   for s in self.client.services.list(**kwargs))

        else:
            return ServiceList()

    def nodes(self, **kwargs):
        if self.is_swarm_mode:
            with nodes_histogram.time():
                return ResourceList(NodeInfo(n) for n in self.client.nodes.list(**kwargs))

        else:
            return ResourceList()

    @property
    def state(self):
        return EnhancedDict(containers=self.containers(),
                            services=self.services(),
                            all_containers=Lazy(self.containers, all=True),
                            all_services=Lazy(self.services, desired_task_state=''),
                            nodes=Lazy(self.nodes))

    def events(self, **kwargs):
        for event in self.client.events(**kwargs):
            yield event

    def run_action(self, action_type, *args, **kwargs):
        action = action_type(self, swarm_manager=kwargs.get('manager'))
        action.execute(*args)

    def close(self):
        self.client.api.close()
