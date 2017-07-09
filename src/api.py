import docker

from models import ResourceList, ContainerInfo, ServiceInfo


class DockerApi(object):
    def __init__(self):
        self.client = docker.DockerClient()

    @property
    def is_swarm_mode(self):
        return len(self.client.swarm.attrs) > 0

    def containers(self, **kwargs):
        return ResourceList(ContainerInfo(c) for c in self.client.containers.list(**kwargs))

    def services(self, **kwargs):
        return ResourceList(ServiceInfo(s) for s in self.client.services.list(**kwargs))

    def events(self, **kwargs):
        for event in self.client.events(**kwargs):
            yield event

    def run_action(self, action_type, *args, **kwargs):
        action = action_type(self)
        action.execute(*args, **kwargs)

    def close(self):
        self.client.api.close()
