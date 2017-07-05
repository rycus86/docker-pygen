import tempfile
import threading
from datetime import datetime, timedelta
from unittest_helper import BaseDockerTestCase

import pygen


class UpdateTest(BaseDockerTestCase):
    def setUp(self):
        super(UpdateTest, self).setUp()

        self.target_file = tempfile.NamedTemporaryFile()
        self.target_path = self.target_file.name

        self.count_signal_calls = 0

    def tearDown(self):
        super(UpdateTest, self).tearDown()

        self.target_file.close()

    def read_contents(self):
        with open(self.target_path, 'r') as output_file:
            return output_file.read()

    def test_updates_target(self):
        app = pygen.PyGen(target=self.target_path,
                          template="""#
            {% for container in containers %}
                __{{ container.name }}__
            {% endfor %}""")

        c1 = self.start_container()

        app.update_target()

        content = self.read_contents()

        self.assertIn('__%s__' % c1.name, content)

        c2 = self.start_container()
        
        app.update_target()

        content = self.read_contents()

        self.assertIn('__%s__' % c1.name, content)
        self.assertIn('__%s__' % c2.name, content)

        c1.stop()

        app.update_target()

        content = self.read_contents()

        self.assertNotIn('__%s__' % c1.name, content)
        self.assertIn('__%s__' % c2.name, content)

    def test_does_not_replace_unchanged_content(self):
        app = pygen.PyGen(target=self.target_path,
                          template="""#
            {% for container in containers %}
                __{{ container.name }}__
            {% endfor %}""")
        
        original_signal_func = app.signal

        def counting_signal(*args, **kwargs):
            self.count_signal_calls += 1
            original_signal_func(*args, **kwargs)

        app.signal = counting_signal

        self.start_container()

        self.assertEqual(0, self.count_signal_calls)

        app.update_target()

        self.assertEqual(1, self.count_signal_calls)

        app.update_target()

        self.assertEqual(1, self.count_signal_calls)

        app.update_target()

        self.assertEqual(1, self.count_signal_calls)

    def test_watch(self):
        app = pygen.PyGen(target=self.target_path,
                          template="""#
            {% for container in containers %}
                __{{ container.name }}__
            {% endfor %}""")
        
        original_signal_func = app.signal

        def counting_signal(*args, **kwargs):
            self.count_signal_calls += 1
            original_signal_func(*args, **kwargs)

        app.signal = counting_signal
        
        self.assertEqual(0, self.count_signal_calls)
        
        def run(flags):
            since = datetime.utcnow()

            while flags['run']:
                until = datetime.utcnow() + timedelta(seconds=1)
                app.watch(until=until)

                since = datetime.utcnow()
        
        flags = {'run': True}
        try:
            thread = threading.Thread(target=run, args=(flags,))
            thread.start()

            self.assertEqual(0, self.count_signal_calls)

            c1 = self.start_container()

            self.assertEqual(1, self.count_signal_calls)

            import time
            time.sleep(2)
            self.assertIn('__%s__' % c1.name, self.read_contents())

            c2 = self.start_container()

            self.assertEqual(2, self.count_signal_calls)

            time.sleep(2)

            self.assertIn('__%s__' % c1.name, self.read_contents())
            self.assertIn('__%s__' % c2.name, self.read_contents())

            c1.stop()

            self.assertEqual(3, self.count_signal_calls)
            
            time.sleep(2)

            self.assertNotIn('__%s__' % c1.name, self.read_contents())
            self.assertIn('__%s__' % c2.name, self.read_contents())

            flags['run'] = False
            thread.join()

        except:
            flags['run'] = False
            raise

