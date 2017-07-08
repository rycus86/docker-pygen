import six

from utils import EnhancedDict, EnhancedList


class NetworkList(EnhancedList):
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
            'env': EnhancedDict(self.split_env(container.attrs['Config'].get('Env'))).default(''),
            'networks': self._networks(container),
            'ports': self._ports(container.attrs['Config'].get('ExposedPorts', dict()).keys())
        }

        self.update(info)
        self.update(kwargs)

    @staticmethod
    def split_env(values):
        return map(lambda x: x.split('=', 1), values)

    @staticmethod
    def _networks(container):
        result = NetworkList()

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


class TaskInfo(EnhancedDict):
    def __init__(self, task, **kwargs):
        super(TaskInfo, self).__init__()

        info = {
            'raw': task,
            'id': task['ID'],
            'node_id': task['NodeID'],
            'service_id': task['ServiceID'],
            'container_id': task['Status']['ContainerStatus']['ContainerID'],
            'image': task['Spec']['ContainerSpec']['Image'],
            'status': task['Status']['State'],
            'desired_state': task['DesiredState'],
            'labels': EnhancedDict(task['Spec']['ContainerSpec']['Labels']).default(''),
            'env': EnhancedDict(ContainerInfo.split_env(task['Spec']['ContainerSpec']['Env'])).default(''),
            'networks': NetworkList(self.parse_network(network) for network in task['NetworksAttachments'])
        }

        self.update(info)
        self.update(kwargs)

    @staticmethod
    def parse_network(network):
        details = network['Network']
        spec = details['Spec']
        addresses = network['Addresses']

        return EnhancedDict(
            id=details['ID'],
            name=spec['Name'],
            is_ingress=spec.get('Ingress') is True,
            labels=EnhancedDict(spec['Labels']),
            ip_addresses=EnhancedList(address.split('/')[0] for address in addresses)
        )


class ServiceInfo(EnhancedDict):
    def __init__(self, service, **kwargs):
        super(ServiceInfo, self).__init__()

        info = {
            'raw': service,
            'id': service.id,
            'short_id': service.short_id,
            'name': service.name,
            'image': service.attrs['Spec']['TaskTemplate']['ContainerSpec']['Image'],
            'tasks': EnhancedList(TaskInfo(task) for task in service.tasks()),
            'labels': EnhancedDict(service.attrs['Spec']['Labels']).default(''),
            'ports': EnhancedDict(tcp=EnhancedList(), udp=EnhancedList()),
            'networks': NetworkList(),
            'ingress': EnhancedDict(ports=EnhancedDict(tcp=EnhancedList(), udp=EnhancedList()),
                                    gateway='',
                                    ip_addresses=EnhancedList())
        }

        self.update(info)

        self.process_ingress()
        self.process_networks()
        self.process_ports()

        self.update(kwargs)

    def process_ingress(self):
        virtual_ips = self.raw.attrs['Endpoint']['VirtualIPs']

        for task in self.tasks:
            for task_network in task.networks:
                if task_network.is_ingress:
                    self.ingress.update(
                        id=task_network.id,
                        name=task_network.name
                    )

                    self.ingress.ip_addresses.extend(task_network.ip_addresses)

        for vip in virtual_ips:
            if vip['NetworkID'] == self.ingress.id:
                self.ingress.gateway = vip['Addr'].split('/')[0]

    def process_networks(self):
        virtual_ips = self.raw.attrs['Endpoint']['VirtualIPs']

        for network in self.raw.attrs['Spec']['Networks']:
            network_id = network['Target']

            gateway = None
            name = None
            ip_addresses = EnhancedList()

            # get an address for it
            for vip in virtual_ips:
                if vip['NetworkID'] == network_id:
                    gateway = vip['Addr'].split('/')[0]
                    break

            # process network details based on task information
            for task in self.tasks:
                for task_network in task.networks:
                    if task_network.id == network_id:
                        name = task_network.name
                        ip_addresses.extend(task_network.ip_addresses)

            self.networks.append(EnhancedDict(
                id=network_id,
                name=name,
                gateway=gateway,
                ip_addresses=ip_addresses
            ))

    def process_ports(self):
        for port in self.raw.attrs.get('Spec', dict()).get('EndpointSpec', dict()).get('Ports', list()):
            published, target, protocol = (port.get(key) for key in ('PublishedPort', 'TargetPort', 'Protocol'))

            if port.get('PublishMode') == 'ingress' and published:
                self.ingress.ports[protocol].append(published)

            self.ports[protocol].append(target)
