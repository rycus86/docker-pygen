from http_server import HttpServer
from utils import get_logger

logger = get_logger('pygen-http')


class Manager(HttpServer):
    manager_port = 9411

    def __init__(self, app):
        super(Manager, self).__init__(self.manager_port)

        self.app = app

    def _handle_request(self, request):
        self.app.update_target()
