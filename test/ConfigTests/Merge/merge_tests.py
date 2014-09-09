#!/usr/bin/env python

import unittest
import sys
import os

sys.path.append("../../../")

from PAV.modules.testConfig import merge

class MergeTest(unittest.TestCase):
    def test_empty_merge(self):
        self.assertEqual({}, merge({}, {}))
        self.assertEqual([], merge([], []))
        self.assertEqual({}, merge([], {}))
        self.assertEqual([], merge({}, []))

    def test_dict_merge(self):
        self.assertEqual({'a': 4}, merge({'a': 4}, {}))
        self.assertEqual({'a': 5}, merge({'a': 4}, {'a': 5}))

    def test_nested_merge(self):
        a = {'a': {'b': 3}}
        b = {'c': {'b': 4}}
        self.assertEqual({'a': {'b': 3}, 'c': {'b': 4}}, merge(a, b))

    def test_same_key_merge(self):
        a = {'b': {'a': 1, 'c': 4}}
        b = {'b': {'a': 2}}
        self.assertEqual({'b': {'a': 2, 'c': 4}}, merge(a, b))

    def test_double_decl(self):
        a = {'b': {'a': 1}}
        b = {'b': {'a': 2}, 'b': {'a': 100}}
        self.assertEqual({'b': {'a': 100}}, merge(a, b))

if __name__ == '__main__':
    unittest.main(verbosity=2)
