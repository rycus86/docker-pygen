import threading
import time

import six
from six.moves import BaseHTTPServer

from utils import get_logger

logger = get_logger('pygen-http')


class HttpServer(object):
    def __init__(self, app, **kwargs):
        self.app = app
        self.port = kwargs['http']

        self._httpd = None

    def _run_server(self):
        update_handler = self.app.update_target

        class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
            def do_POST(self):
                try:
                    update_handler()

                    self.send_response(200)
                    self.end_headers()

                    self.wfile.write(six.b('OK\n'))

                except:
                    self.send_error(500)
                    self.end_headers()

                    raise

        self._httpd = BaseHTTPServer.HTTPServer(('', self.port), RequestHandler)
        self._httpd.serve_forever()

    def start(self):
        thread = threading.Thread(target=self._run_server)
        thread.setDaemon(True)
        thread.start()

        self._wait_for_server()

        self.port = self._httpd.server_port

        logger.info('HTTP server listening on port %s', self.port)

    def _wait_for_server(self):
        for _ in range(50):
            if self._httpd:
                break

            time.sleep(0.1)

    def shutdown(self):
        if self._httpd:
            logger.info('Shutting down HTTP server ...')

            self._httpd.shutdown()
