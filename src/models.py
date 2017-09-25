from resources import NetworkList, TaskList
from utils import EnhancedDict, EnhancedList


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
    def __init__(self, service, task, **kwargs):
        super(TaskInfo, self).__init__()

        info = {
            'raw': task,
            'id': task['ID'],
            'name':
                '%s.%s.%s' % (service.name, task.get('Slot'), task['ID'])
                if task.get('Slot') else
                '%s.%s.%s' % (service.name, task.get('NodeID'), task['ID']),
            'node_id': task.get('NodeID'),
            'service_id': task['ServiceID'],
            'slot': task.get('Slot'),
            'container_id': task['Status'].get('ContainerStatus', dict()).get('ContainerID'),
            'image': task['Spec']['ContainerSpec']['Image'],
            'status': task['Status']['State'],
            'desired_state': task['DesiredState'],
            'labels': EnhancedDict(task['Spec']['ContainerSpec'].get('Labels', dict())).default(''),
            'env': EnhancedDict(ContainerInfo.split_env(task['Spec']['ContainerSpec'].get('Env', list()))).default(''),
            'networks': NetworkList(self.parse_network(network) for network in task.get('NetworksAttachments', list()))
        }

        info['labels'].update({
            'com.docker.swarm.service.id': service.id,
            'com.docker.swarm.service.name': service.name,
            'com.docker.swarm.task.id': info['id'],
            'com.docker.swarm.task.name': info['name'],
            'com.docker.swarm.node.id': info['node_id']
        })

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
            labels=EnhancedDict(spec.get('Labels', dict())),
            ip_addresses=EnhancedList(address.split('/')[0] for address in addresses)
        )


class ServiceInfo(EnhancedDict):
    def __init__(self, service, desired_task_state='running', **kwargs):
        super(ServiceInfo, self).__init__()

        info = {
            'raw': service,
            'id': service.id,
            'short_id': service.short_id,
            'name': service.name,
            'image': service.attrs['Spec']['TaskTemplate']['ContainerSpec']['Image'],
            'labels': EnhancedDict(service.attrs['Spec']['Labels']).default(''),
            'ports': EnhancedDict(tcp=EnhancedList(), udp=EnhancedList()),
            'networks': NetworkList(),
            'ingress': EnhancedDict(ports=EnhancedDict(tcp=EnhancedList(), udp=EnhancedList()),
                                    gateway='',
                                    ip_addresses=EnhancedList())
        }

        if desired_task_state:
            task_filters = {'desired-state': desired_task_state}

        else:
            task_filters = None
        
        info['tasks'] = TaskList(TaskInfo(service, task)
                                 for task in service.tasks(filters=task_filters))

        self.update(info)

        self.process_ingress()
        self.process_networks()
        self.process_ports()

        self.update(kwargs)

    def process_ingress(self):
        virtual_ips = self.raw.attrs['Endpoint'].get('VirtualIPs', list())

        # for older API versions
        probably_ingress = None
        target_network_ids = set()
        target_network_ids.update(
            network['Target'] for network in self.raw.attrs['Spec'].get('TaskTemplate', dict()).get('Networks', list()))
        target_network_ids.update(
            network['Target'] for network in self.raw.attrs['Spec'].get('Networks', list()))

        for vip in virtual_ips:
            if vip['NetworkID'] not in target_network_ids:
                probably_ingress = vip['NetworkID']

        for task in self.tasks:
            for task_network in task.networks:
                if task_network.is_ingress or task_network.id == probably_ingress:
                    self.ingress.update(
                        id=task_network.id,
                        name=task_network.name
                    )

                    self.ingress.ip_addresses.extend(task_network.ip_addresses)

                if probably_ingress and task_network.id == probably_ingress:
                    task_network.is_ingress = True

        for vip in virtual_ips:
            if vip['NetworkID'] == self.ingress.id:
                self.ingress.gateway = vip['Addr'].split('/')[0]

    def process_networks(self):
        virtual_ips = self.raw.attrs['Endpoint'].get('VirtualIPs', list())

        raw_network_ids = set()
        raw_network_ids.update(
            network['Target'] for network in self.raw.attrs['Spec'].get('TaskTemplate', dict()).get('Networks', list()))
        raw_network_ids.update(
            network['Target'] for network in self.raw.attrs['Spec'].get('Networks', list()))

        for network_id in raw_network_ids:
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

    def update_service(self, docker_api_client, force_update=False):
        self.raw.reload()

        raw = self.raw.attrs
        spec = raw['Spec']

        service_id = raw['ID']
        version = raw['Version']['Index']
        task_template = spec['TaskTemplate']
        name = spec['Name']
        labels = spec.get('Labels')
        mode = spec['Mode']
        update_config = spec.get('UpdateConfig')
        networks = task_template.get('Networks')
        endpoint_spec = spec.get('EndpointSpec')
        
        if force_update:
            task_template['ForceUpdate'] = (task_template['ForceUpdate'] + 1) % 100

        return docker_api_client.update_service(service=service_id,
                                                version=version,
                                                task_template=task_template,
                                                name=name,
                                                labels=labels,
                                                mode=mode,
                                                update_config=update_config,
                                                networks=networks,
                                                endpoint_spec=endpoint_spec)


class NodeInfo(EnhancedDict):
    def __init__(self, node, **kwargs):
        super(NodeInfo, self).__init__()
        
        info = {
            'raw': node,
            'id': node.id,
            'short_id': node.short_id,
            'version': node.version,
            'state': node.attrs['Status'].get('State'),
            'address': node.attrs['Status'].get('Addr'),
            'hostname': node.attrs.get('Description', dict()).get('Hostname', ''),
            'role': node.attrs['Spec']['Role'],
            'availability': node.attrs['Spec']['Availability'],
            'labels': EnhancedDict(node.attrs['Spec']['Labels']).default('')
        }

        info['name'] = info['hostname'] if info['hostname'] else info['short_id']

        self.update(info)
        self.update(kwargs)

