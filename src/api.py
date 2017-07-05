from itertools import groupby

import docker


class GetterDict(dict):
    def __getattr__(self, item):
        return self.get(item, '')


class ContainerInfo(GetterDict):
    def __init__(self, container, **kwargs):
        super(ContainerInfo, self).__init__()

        info = {
            'raw': container,
            'id': container.id,
            'short_id': container.short_id,
            'name': container.name,
            'image': container.attrs['Config'].get('Image'),
            'status': container.status,
            'labels': GetterDict(container.labels),
            'env': self._split_env(container.attrs['Config'].get('Env')),
            'network': self._network_settings(container.attrs)
        }

        self.update(info)
        self.update(kwargs)

    @staticmethod
    def _split_env(values):
        return GetterDict(map(lambda x: x.split('=', 1), values))

    @staticmethod
    def _network_settings(attrs):
        network_dict = attrs['NetworkSettings']['Networks']
        exposed_ports = attrs['Config'].get('ExposedPorts', {}).keys()

        return GetterDict(
            ip_addresses=[network['IPAddress'] for network in network_dict.values()],
            ports={
                port_type: list(int(value) for value, _type in values)
                for port_type, values in groupby((port.split('/') for port in exposed_ports), lambda (_v, t): t)
            })


class DockerApi(object):
    def __init__(self):
        self.client = docker.DockerClient()

    def list(self, **kwargs):
        return map(ContainerInfo, self.client.containers.list(**kwargs))

    def events(self, **kwargs):
        for event in self.client.events(**kwargs):
            yield event
