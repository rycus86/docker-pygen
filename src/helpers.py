from collections import defaultdict
from errors import PyGenException

def group_by(containers, *keys):
    groups = defaultdict(list)

    def get_property(item, name):
        if hasattr(item, name):
            return getattr(item, name)

        elif hasattr(item, '__contains__') and name in item:
            return item[name]

        else:
            raise PyGenException('%s property not found on %s' % (name, item), dir(item))
    
    for container in containers:
        value = container
        
        for key in keys:
            for attr in key.split('.'):
                value = get_property(value, attr)

        groups[value].append(container)
    
    return groups
