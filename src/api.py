import docker

from utils import EnhancedDict, EnhancedList


class _NetworkList(EnhancedList):
    def matching(self, target):
        if hasattr(target, 'raw'):
            target = target.raw

        target_gateways = set(net['Gateway'] for net in target.attrs['NetworkSettings']['Networks'].values())

        for net in self:
            if net.gateway in target_gateways:
                return net


class ContainerInfo(EnhancedDict):
    def __init__(self, container, **kwargs):
        super(ContainerInfo, self).__init__()

        info = {
            'raw': container,
            'id': container.id,
            'short_id': container.short_id,
            'name': container.name,
            'image': container.attrs['Config'].get('Image'),
            'status': container.status,
            'labels': EnhancedDict(container.labels, default=''),
            'env': EnhancedDict(self._split_env(container.attrs['Config'].get('Env')), default=''),
            'networks': self._networks(container),
            'ports': self._ports(container.attrs['Config'].get('ExposedPorts', {}).keys())
        }

        self.update(info)
        self.update(kwargs)

    @staticmethod
    def _split_env(values):
        return map(lambda x: x.split('=', 1), values)

    @staticmethod
    def _networks(container):
        result = _NetworkList()

        settings = container.attrs['NetworkSettings']

        result.ip_address = settings.get('IPAddress', '')
        result.ports = ContainerInfo._ports(settings.get('Ports'))

        for name, network in settings['Networks'].items():
            result.append(EnhancedDict(
                name=name,
                ip_address=network['IPAddress'],
                gateway=network['Gateway']
            ))

        return result

    @staticmethod
    def _ports(port_configurations):
        return EnhancedDict(
            tcp=EnhancedList([port.split('/')[0] for port in port_configurations if port.endswith('/tcp')]),
            udp=EnhancedList([port.split('/')[0] for port in port_configurations if port.endswith('/udp')])
        )


class ServiceInfo(EnhancedDict):
    def __init__(self, service, **kwargs):
        super(ServiceInfo, self).__init__()

        info = {
            'raw': service,
            'id': service.id,
            'short_id': service.short_id,
            'name': service.name
        }

        self.update(info)
        self.update(kwargs)


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
