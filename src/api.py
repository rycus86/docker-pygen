import docker


class ContainerInfo(dict):
    def __init__(self, container, **kwargs):
        super(ContainerInfo, self).__init__()

        info = {
            'raw': container,
            'id': container.id,
            'short_id': container.short_id,
            'name': container.name,
            'image': container.attrs['Config'].get('Image'),
            'status': container.status,
            'labels': container.labels,
            'env': self._split_env(container.attrs['Config'].get('Env'))
        }

        self.update(info)
        self.update(kwargs)

    @staticmethod
    def _split_env(values):
        key_value_pairs = map(lambda x: x.split('=', 1), values)
        return {key: value for key, value in key_value_pairs}

    def __getattr__(self, item):
        return self[item]


class DockerApi(object):
    def __init__(self):
        self.client = docker.DockerClient()

    def list(self):
        return map(ContainerInfo, self.client.containers.list())
