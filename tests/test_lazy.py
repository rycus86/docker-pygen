import unittest

from utils import Lazy, EnhancedList, EnhancedDict


class LazyTest(unittest.TestCase):
    def test_range(self):
        lazy = Lazy(lambda: range(5))

        for i, a in enumerate(lazy):
            self.assertEqual(a, i)

        self.assertEqual(len(lazy), 5)

    def test_hash(self):
        lazy = Lazy(lambda: 3)
        
        self.assertEqual(hash(lazy), 3)

    def test_enhanced_types(self):
        lazy = Lazy(lambda: EnhancedDict(key='value'))

        self.assertEqual(lazy.key, 'value')
        
        lazy = Lazy(lambda: EnhancedList([1, 2, 3]))

        self.assertEqual((lazy.first, lazy[1], lazy.last), (1, 2, 3))

    def test_callable(self):
        lazy = Lazy(lambda: str)

        self.assertEqual(lazy(0.4), '0.4')
    
    def test_init(self):
        lazy = Lazy(str, 6)

        self.assertEqual(str(lazy), '6')

        lazy = Lazy(EnhancedDict, key='lazy')

        self.assertEqual(lazy.key, 'lazy')

