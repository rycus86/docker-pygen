import sys
import signal
import logging


def initialize_logging():
    if '--debug' in sys.argv:
        logging.basicConfig(
            format='[%(levelname)s] %(asctime)s (%(name)s) @ %(module)s.%(funcName)s:%(lineno)s\n%(message)s')
    else:
        logging.basicConfig(format='%(asctime)s [%(levelname)s] %(module)s.%(funcName)s - %(message)s')


# need to check if we are in debug mode before argparse can process the arguments
initialize_logging()


def get_logger(name):
    return logging.getLogger(name)


def set_log_level(level):
    logging.root.setLevel(level)


def handle_signal(num, _):  # pragma: no cover
    if num == signal.SIGTERM:
        exit(0)

    else:
        exit(1)


def update_on_sighup(app):
    def sighup_handler(*args):
        app.update_target()

    signal.signal(signal.SIGHUP, sighup_handler)


def setup_signals(app):
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    update_on_sighup(app)


class EnhancedDict(dict):
    default_value = None

    def default(self, value):
        self.default_value = value
        return self

    def __getattr__(self, item):
        if item in self:
            return self[item]

        elif hasattr(item, 'lower'):
            for key in self:
                if hasattr(key, 'lower') and key.lower() == item.lower():
                    return self[key]

        return self.default_value

    def __hash__(self):
        if 'raw' in self:
            return hash(self.raw)

        elif 'id' in self:
            return hash(self.id)

        else:
            raise TypeError('unhashable dict content')


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


class Lazy(object):
    def __init__(self, delegate, *args, **kwargs):
        self.__delegate = delegate
        self.__args = args
        self.__kwargs = kwargs

        self._value = None

    @property
    def __value(self):
        if self._value is None:
            self._value = self.__delegate(*self.__args, **self.__kwargs)

        return self._value

    def __getattr__(self, name):
        return getattr(self.__value, name)

    def __getitem__(self, item):
        return self.__value[item]

    def __call__(self, *args, **kwargs):
        return self.__value(*args, **kwargs)

    def __iter__(self):
        return iter(self.__value)

    def __len__(self):
        return len(self.__value)

    def __hash__(self):
        return hash(self.__value)

    def __str__(self):
        return str(self.__value)

