import unittest

from helpers import *


class HelpersTest(unittest.TestCase):
    @staticmethod
    def get_object_with_attributes(**kwargs):  # TODO rename to something shorter like 'obj'
        class TestObject(object):
            pass

        item = TestObject()

        for key, value in kwargs.items():
            setattr(item, key, value)

        return item

    def test_group_by(self):
        items = [
            self.get_object_with_attributes(name='test-1',
                                            labels={'type': 'example'},
                                            env=self.get_object_with_attributes(path='/usr/bin:/bin',
                                                                                hostname='example001'),
                                            props={
                                                'files': self.get_object_with_attributes(main='main.py',
                                                                                         test='test.py')
                                            }),
            self.get_object_with_attributes(name='test-2',
                                            labels={'type': 'demo'},
                                            env=self.get_object_with_attributes(path='/usr/local/bin:/usr/bin:/bin',
                                                                                hostname='example002'),
                                            props={
                                                'files': self.get_object_with_attributes(main='sample.py',
                                                                                         test='test_sample.py')
                                            }),
            self.get_object_with_attributes(name='test-3',
                                            labels={'type': 'sample'},
                                            env=self.get_object_with_attributes(path='/app:/usr/bin:/bin',
                                                                                hostname='example003'),
                                            props={
                                                'files': self.get_object_with_attributes(main='main.py',
                                                                                         test='test_main.py')
                                            })
        ]

        groups = group_by(items, 'props.files.main')

        self.assertEqual(len(groups), 2)

        for value, hits in groups.items():
            self.assertIn(value, ('main.py', 'sample.py'))

            for item in hits:
                if value == 'main.py':
                    self.assertIn(item.name, ('test-1', 'test-3'))
                    self.assertIn(item.labels.get('type'), ('sample', 'example'))

                else:
                    self.assertEquals(item.name, 'test-2')
                    self.assertEquals(item.labels.get('type'), 'demo')

        self.assertEqual(len(group_by(items, 'name')), 3)
        self.assertEqual(len(group_by(items, 'labels.type')), 3)

