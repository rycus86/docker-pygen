import os

from prometheus_client import MetricsHandler
from prometheus_client import Histogram, Summary, Gauge

from http_server import HttpServer


class MetricsServer(HttpServer):
    _instance = None

    def __init__(self, port):
        super(MetricsServer, self).__init__(port)
        MetricsServer._instance = self
        
        self._export_defaults()

    def _export_defaults(self):
        app_info = Gauge(
            'pygen_app_info', 'Application info',
            labelnames=('version',)
        )
        app_info.labels(
            os.environ.get('GIT_COMMIT') or 'unknown'
        ).set(1)

        app_built_at = Gauge(
            'pygen_app_built_at', 'Application build timestamp'
        )
        app_built_at.set(float(os.environ.get('BUILD_TIMESTAMP') or '0'))

    def _get_request_handler(self):
        return MetricsHandler

    @classmethod
    def shutdown_current(cls):
        if cls._instance:
            cls._instance.shutdown()

