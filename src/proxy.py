import threading
import BaseHTTPServer

import requests


class HttpServer(object):
    
    def __init__(self, app, **kwargs):
        self.app = app
        self.port = kwargs.get('proxy_port', 9411)
        self.is_collector = kwargs.get('collector', False)
        self.target_collector = kwargs.get('target_collector')
        self.target_updater = kwargs.get('target_updater')

        self._httpd = None

    def send_signal(self, event):
        for container in self.app.api.containers().matching(self.target_collector):
            try:
                requests.post('http://%s:%s/collect' % (container.networks.ip_address, container.ports.tcp.first), data=event)
                # TODO error handling 
            except Exception as ex:
                print 'Error:', ex

    def on_collect(self, request):
        for container in self.app.api.containers().matching(self.target_updater):
            requests.post('http://%s:%s/update' % (container.networks.ip_address, container.ports.tcp.first))
            # TODO error handling

        request.send_response(200)
        request.end_headers()

        request.wfile.write('collect\n')

    def on_update(self, request):
        self.app.update_target()
        
        request.send_response(200)
        request.end_headers()

        request.wfile.write('update\n')

    def _run_server(self):
        endpoints = {
            '/collect': self.on_collect,
            '/update': self.on_update
        }

        def dispatch(request):
            if request.path in endpoints:
                endpoints.get(request.path)(request)

            else:
                request.send_error(404)

        class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
            def do_POST(self):
                dispatch(self)

        self._httpd = BaseHTTPServer.HTTPServer(('', self.port), RequestHandler)
        self._httpd.serve_forever()

    def start(self):
        thread = threading.Thread(target=self._run_server)
        thread.start()

    def shutdown(self):
        if self._httpd:
            self._httpd.shutdown()

