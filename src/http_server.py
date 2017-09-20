import threading
import time

import six
from six.moves import BaseHTTPServer, socketserver

from errors import PyGenException
from utils import get_logger

logger = get_logger('pygen-http-server')


class HttpServer(object):
    def __init__(self, port):
        self.port = port

        self._httpd = None

    def _handle_request(self, request):
        raise PyGenException('Request handler not implemented')

    def _run_server(self):
        handler = self._handle_request

        class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
            def do_POST(self):
                try:
                    handler(self)

                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.send_header('Content-Length', '3')
                    self.end_headers()

                    self.wfile.write(six.b('OK\n'))
                    self.wfile.close()

                except Exception:
                    self.send_error(500)
                    self.end_headers()

                    raise

        class Server(BaseHTTPServer.HTTPServer, socketserver.ThreadingMixIn):
            pass

        self._httpd = Server(('', self.port), RequestHandler)
        self._httpd.serve_forever()

    def start(self):
        thread = threading.Thread(target=self._run_server)
        thread.setDaemon(True)
        thread.start()

        logger.info('HTTP server listening on port %s', self.port)

        self._wait_for_startup()

    def _wait_for_startup(self):
        for _ in range(50):
            if not self._httpd:
                time.sleep(0.1)

    def shutdown(self):
        if self._httpd:
            logger.info('Shutting down HTTP server ...')

            self._httpd.shutdown()
            self._httpd.server_close()
