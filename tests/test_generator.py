import pygen
from unittest_helper import BaseDockerTestCase


class GeneratorTest(BaseDockerTestCase):
    app = None

    def tearDown(self):
        super(GeneratorTest, self).tearDown()

        if hasattr(self, 'app') and self.app:
            self.app.api.close()

    def test_generate(self):
        test_container = self.start_container(environment=['GENERATOR=pygen'])

        self.app = pygen.PyGen(template="""#
            {% for container in containers %}
            running: {{ container.name }} ID={{ container.short_id }}
              {% for key, value in container.env.items() %}
              env: {{ key }}=>{{ value }}
              {% endfor %}
            {% endfor %}""")

        content = self.app.generate()

        self.assertIn('running: %s' % test_container.name, content)
        self.assertIn('ID=%s' % test_container.short_id, content)
        self.assertIn('env: GENERATOR=>pygen', content)

    def test_generate_with_groups(self):
        self.start_container(environment=['GENERATOR=pygen'],
                             labels={'instance': '001',
                                     'application': 'web'})
        self.start_container(environment=['GENERATOR=pygen'],
                             labels={'instance': '002',
                                     'application': 'web'})
        self.start_container(environment=['GENERATOR=pygen'],
                             labels={'instance': '003',
                                     'application': 'db'})

        self.app = pygen.PyGen(template="""#
            {% for key, containers in containers|groupby('labels.application') %}
            group: {{ key }}
              {% for container in containers %}
              instance: {{ container.labels.instance }}
              {% endfor %}
            {% endfor %}""")

        content = self.app.generate()

        self.assertIn('group: web', content)
        self.assertIn('group: db', content)

        for num in range(1, 4):
            self.assertIn('instance: %03d' % num, content)

    def test_nginx_template(self):
        self.start_container(name='pygen-test-nginx-1', labels={'virtual-host': 'test.site.com'}, ports={8080: None})
        self.start_container(name='pygen-test-nginx-2', labels={'virtual-host': 'test.site.com'}, ports={8080: None})
        self.start_container(name='pygen-test-nginx-3', labels={'virtual-host': 'www.site.com'}, ports={8080: None})
        self.start_container(name='pygen-test-nginx-4', labels={'virtual-host': 'api.site.com',
                                                                'context-path': '/rest'}, ports={5000: None})
        self.start_container(name='pygen-test-nginx-5', labels={'virtual-host': 'api.site.com',
                                                                'context-path': '/stream'}, ports={5000: None})
        self.start_container(name='pygen-test-nginx-6', labels={'virtual-host': 'api.site.com',
                                                                'context-path': '/no-port-exposed'})
        self.start_container(name='pygen-test-nginx-7', labels={'context-path': '/no-virtual-host'}, ports={9001: None})

        self.app = pygen.PyGen(template=self.relative('templates/nginx.example'))

        content = self.app.generate()

        # pygen-test-nginx-1 : test.site.com/ 8080
        self.assertIn('# pygen-test-nginx-1', content)
        # pygen-test-nginx-2 : test.site.com/ 8080
        self.assertIn('# pygen-test-nginx-2', content)
        # pygen-test-nginx-3 : www.site.com/ 8080
        self.assertIn('# pygen-test-nginx-3', content)
        # pygen-test-nginx-4 : api.site.com/rest 5000
        self.assertIn('# pygen-test-nginx-4', content)
        # pygen-test-nginx-5 : api.site.com/stream 5000
        self.assertIn('# pygen-test-nginx-5', content)
        # pygen-test-nginx-6 : - /no-port-exposed
        self.assertNotIn('pygen-test-nginx-6', content)
        # pygen-test-nginx-7 : - /no-virtual-host 9001
        self.assertNotIn('pygen-test-nginx-7', content)

        for upstream in ('test.site.com___', 'www.site.com___', 'api.site.com___rest', 'api.site.com___stream'):
            self.assertIn('upstream %s ' % upstream, content)
            self.assertIn('proxy_pass http://%s;' % upstream, content)

        self.assertNotIn('upstream api.site.com___ ', content)

        self.assertIn('location / ', content)
        self.assertIn('location /rest ', content)
        self.assertIn('location /stream ', content)

        for num in range(1, 6):
            container = self.docker_client.containers.get('pygen-test-nginx-%d' % num)

            ip_address = next(iter(container.attrs['NetworkSettings']['Networks'].values())).get('IPAddress')
            port = next(iter(container.attrs['Config'].get('ExposedPorts', {}).keys())).split('/')[0]

            self.assertIn('server %s:%s;' % (ip_address, port), content)
