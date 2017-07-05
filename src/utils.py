import logging

logging.basicConfig(format='%(asctime)s [%(levelname)s] %(module)s.%(funcName)s - %(message)s')


def get_logger(name):
    return logging.getLogger(name)


def set_log_level(level):
    logging.root.setLevel(level)
