import docker

from models import ContainerInfo, ServiceInfo


class DockerApi(object):
    def __init__(self):
        self.client = docker.DockerClient()

    def containers(self, **kwargs):
        return list(ContainerInfo(c) for c in self.client.containers.list(**kwargs))

    def services(self, **kwargs):
        return list(ServiceInfo(s) for s in self.client.services.list(**kwargs))

    def events(self, **kwargs):
        for event in self.client.events(**kwargs):
            yield event

    def close(self):
        self.client.api.close()
