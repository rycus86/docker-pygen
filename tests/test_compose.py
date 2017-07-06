import os
import time
import json
import unittest
from compose.config.config import ConfigFile, ConfigDetails
from compose.config.config import load as load_config
from compose.project import Project
from unittest_helper import relative_path

import pygen


@unittest.skipUnless(os.environ.get('COMPOSE_TESTS'), 'Skipping docker-compose tests')
class DockerComposeTests(unittest.TestCase):
    project = None

    def setUp(self):
        self.app = pygen.PyGen(template=relative_path('templates/mockserver.conf.json'))

    def tearDown(self):
        if self.project:
            self.project.down(False, True, True)

    def test_compose_project(self):
        config = ConfigFile.from_filename(relative_path('compose/sample.yml'))
        details = ConfigDetails(relative_path('compose'), [config])
        self.project = Project.from_config('pygen-test', load_config(details), self.app.api.client.api)
        
        self.project.up(detached=True)
        
        content = self.app.generate()

        parsed = json.loads(content)
        
        self.assertIn('server', parsed)
        self.assertIn('proxy', parsed['server'])

        hosts = parsed['server']['proxy']

        self.assertEquals(len(hosts), 2)

        for host in hosts:
            self.assertIn('host', host)
            self.assertIn(host['host'], ('api.sample.com', 'www.sample.com'))
            
            self.assertIn('backends', host)

            backends = host['backends']

            if host['host'] == 'www.sample.com':
                self.assertEquals(1, len(backends))
                
                backend = backends[0]
                
                self.assertIn('context', backend)
                self.assertEquals(backend.get('context'), '/')
                self.assertIn('servers', backend)
                self.assertEquals(1, len(backend['servers']))

                c_web = self.project.get_service('web').get_container().inspect()
                c_web_ip = next(iter(c_web['NetworkSettings']['Networks'].values())).get('IPAddress')

                self.assertEquals('http://%s:8080/pygen-test_web_1' % c_web_ip, backend['servers'][0])

            else:
                self.assertEquals(2, len(backends))

                for backend in backends:
                    self.assertIn('context', backend)
                    self.assertIn(backend.get('context'), ('/rest', '/stream'))
                    
                    self.assertIn('servers', backend)
                    self.assertEquals(1, len(backend['servers']))

                    if backend['context'] == '/rest':
                        c_app_a = self.project.get_service('app-a').get_container().inspect()
                        c_app_a_ip = next(iter(c_app_a['NetworkSettings']['Networks'].values())).get('IPAddress')

                        self.assertEquals('http://%s:9001/pygen-test_app-a_1' % c_app_a_ip, backend['servers'][0])

                    else:
                        c_app_b = self.project.get_service('app-b').get_container().inspect()
                        c_app_b_ip = next(iter(c_app_b['NetworkSettings']['Networks'].values())).get('IPAddress')

                        self.assertEquals('http://%s:9001/pygen-test_app-b_1' % c_app_b_ip, backend['servers'][0])

    def test_scale_update(self):
        config = ConfigFile.from_filename(relative_path('compose/sample.yml'))
        details = ConfigDetails(relative_path('compose'), [config])
        self.project = Project.from_config('pygen-test', load_config(details), self.app.api.client.api)
        
        self.project.up(detached=True)
        
        content = self.app.generate()

        parsed = json.loads(content)

        self.assertIn('server', parsed)
        self.assertIn('proxy', parsed['server'])

        hosts = parsed['server']['proxy']

        self.assertEquals(len(hosts), 2)

        for host in hosts:
            self.assertIn('host', host)
            self.assertIn(host['host'], ('api.sample.com', 'www.sample.com'))
            
            if host['host'] == 'www.sample.com':
                self.assertIn('backends', host)

                backends = host['backends']

                self.assertEqual(len(backends), 1)

                servers = backends[0].get('servers')

                self.assertIsNotNone(servers)
                self.assertEqual(len(servers), 1)

        service_web = self.project.get_service('web')
        
        service_web.scale(3)

        content = self.app.generate()
        
        parsed = json.loads(content)

        self.assertIn('server', parsed)
        self.assertIn('proxy', parsed['server'])

        hosts = parsed['server']['proxy']

        self.assertEquals(len(hosts), 2)

        for host in hosts:
            self.assertIn('host', host)
            self.assertIn(host['host'], ('api.sample.com', 'www.sample.com'))
            
            if host['host'] == 'www.sample.com':
                self.assertIn('backends', host)

                backends = host['backends']

                self.assertEqual(len(backends), 1)

                servers = backends[0].get('servers')

                self.assertIsNotNone(servers)
                self.assertEqual(len(servers), 3)

