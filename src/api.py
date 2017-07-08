import six
import docker

from utils import EnhancedDict, EnhancedList


class _NetworkList(EnhancedList):
    def matching(self, target):
        if isinstance(target, six.string_types):
            for net in self:
                if net.id == target or net.name == target:
                    return net

            # try short IDs
            for net in self:
                if net.id.startswith(target):
                    return net

        else:
            if hasattr(target, 'raw'):
                target = target.raw
                target_network_ids = set(net['NetworkID']
                                         for net in target.attrs['NetworkSettings']['Networks'].values())

            elif hasattr(target, 'id'):
                target_network_ids = {target.id}

            else:
                return

            for net in self:
                if net.id in target_network_ids:
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
            'labels': EnhancedDict(container.labels).default(''),
            'env': EnhancedDict(self._split_env(container.attrs['Config'].get('Env'))).default(''),
            'networks': self._networks(container),
            'ports': self._ports(container.attrs['Config'].get('ExposedPorts', dict()).keys())
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
                id=network['NetworkID'],
                ip_address=network['IPAddress']
            ))

        return result

    @staticmethod
    def _ports(port_configurations):
        return EnhancedDict(
            tcp=EnhancedList([int(port.split('/')[0]) for port in port_configurations if port.endswith('/tcp')]),
            udp=EnhancedList([int(port.split('/')[0]) for port in port_configurations if port.endswith('/udp')])
        )


class ServiceInfo(EnhancedDict):
    def __init__(self, service, **kwargs):
        super(ServiceInfo, self).__init__()

        info = {
            'raw': service,
            'id': service.id,
            'short_id': service.short_id,
            'name': service.name,
            'labels': EnhancedDict(service.attrs['Spec']['Labels']).default('')
        }

        self.update(info)
        self.update(kwargs)

    def enrich(self, client):
        # prepare new properties
        self.update({
            'ingress': EnhancedDict(),
            'networks': _NetworkList(),
            'ports': EnhancedDict(tcp=EnhancedList(), udp=EnhancedList()),
            'containers': EnhancedList()
        })

        # process networks #1
        target_networks = {net['Target']: None for net in self.raw.attrs['Spec']['Networks']}

        for network in client.networks.list():
            if network.attrs.get('Ingress'):
                self['ingress'].update({
                    'id': network.id,
                    'short_id': network.short_id,
                    'name': network.name,
                    'ports': EnhancedDict(tcp=EnhancedList(), udp=EnhancedList()),
                    'ip_addresses': EnhancedList()
                })

            if network.id in target_networks:
                details = EnhancedDict(
                    name=network.name,
                    id=network.id,
                    short_id=network.short_id,
                    ip_addresses=EnhancedList()
                )

                target_networks[network.id] = details

                self.networks.append(details)

        # process ports
        for port in self.raw.attrs.get('Spec', dict()).get('EndpointSpec', dict()).get('Ports', list()):
            published, target, protocol = (port.get(key) for key in ('PublishedPort', 'TargetPort', 'Protocol'))

            if port.get('PublishMode') == 'ingress' and published:
                self.ingress['ports'][protocol].append(published)

            self.ports[protocol].append(target)

        # process containers
        for task in self.raw.tasks():
            container_id = task.get('Status', dict()).get('ContainerStatus', dict()).get('ContainerID')

            if container_id:
                container = ContainerInfo(client.containers.get(container_id))

                self.containers.append(container)

                # process networks #2
                for network in container.networks:
                    if network.ip_address:
                        if network.id == self.ingress.id:
                            self.ingress.ip_addresses.append(network.ip_address)

                        elif network.id in target_networks:
                            target_networks[network.id].ip_addresses.append(network.ip_address)

        # return self for method chaining
        return self


class DockerApi(object):
    def __init__(self):
        self.client = docker.DockerClient()

    def containers(self, **kwargs):
        return list(ContainerInfo(c)
                    for c in self.client.containers.list(**kwargs))

    def services(self, **kwargs):
        return list(ServiceInfo(s).enrich(self.client)
                    for s in self.client.services.list(**kwargs))

    def events(self, **kwargs):
        for event in self.client.events(**kwargs):
            yield event

    def close(self):
        self.client.api.close()
