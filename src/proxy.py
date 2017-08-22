import json
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
            try:
                requests.post('http://%s:%s/update' % (container.networks.ip_address, container.ports.tcp.first))
                # TODO error handling
            except Exception as ex:
                print 'Error:', ex

        request.send_response(200)
        request.end_headers()

        request.wfile.write('collect\n')

    def on_update(self, request):
        self.app.update_target()
        
        request.send_response(200)
        request.end_headers()

        request.wfile.write('update\n')

    def on_fetch(self, request):
        state = self._strip_raw_information(self.app.state)
        
        request.send_response(200)
        request.send_header('Content-Type', 'application/json')
        request.end_headers()

        json.dump(state, request.wfile)

    def _strip_raw_information(self, state):
        for container in state.containers:
            del container['raw']

        for service in state.services:
            del service['raw']

            for task in service.tasks:
                del task['raw']

        return state

    def _run_server(self):
        endpoints = {
            'GET': {
                '/fetch': self.on_fetch
            },
            'POST': {
                '/collect': self.on_collect,
                '/update': self.on_update
            }
        }

        def dispatch(request):
            if request.path in endpoints.get(request.command, tuple()):
                endpoints.get(request.command).get(request.path)(request)

            else:
                request.send_error(404)

        class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
            def do_GET(self):
                dispatch(self)

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

