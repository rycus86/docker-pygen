import logging

logging.basicConfig(format='%(asctime)s [%(levelname)s] %(module)s.%(funcName)s - %(message)s')


def get_logger(name):
    return logging.getLogger(name)


def set_log_level(level):
    logging.root.setLevel(level)


class EnhancedDict(dict):
    def __getattr__(self, item):
        return self.get(item)


class EnhancedList(list):
    @property
    def first(self):
        if len(self):
            return self[0]

    @property
    def first_value(self):
        for item in self:
            if item:
                return item

    @property
    def last(self):
        if len(self):
            return self[-1]

    def __getattr__(self, item):
        return self.__dict__[item]

    def __setattr__(self, key, value):
        self.__dict__[key] = value
