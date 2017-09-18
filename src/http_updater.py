import threading

from six.moves import BaseHTTPServer


class HttpServer(object):
    def __init__(self, app, **kwargs):
        self.app = app
        self.port = kwargs.get('http', 9411)

        self._httpd = None

    def _run_server(self):
        update_handler = self.app.update_target

        class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
            def do_POST(self):
                update_handler()

        self._httpd = BaseHTTPServer.HTTPServer(('', self.port), RequestHandler)
        self._httpd.serve_forever()

    def start(self):
        thread = threading.Thread(target=self._run_server)
        thread.start()

    def shutdown(self):
        if self._httpd:
            self._httpd.shutdown()
