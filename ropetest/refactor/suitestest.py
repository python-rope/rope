try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rope.base import ast
from rope.refactor import suites


class SuiteTest(unittest.TestCase):

    def setUp(self):
        super(SuiteTest, self).setUp()

    def tearDown(self):
        super(SuiteTest, self).tearDown()

    def test_trivial_case(self):
        root = source_suite_tree('')
        self.assertEquals(1, root.get_start())
        self.assertEquals(0, len(root.get_children()))

    def test_simple_ifs(self):
        root = source_suite_tree('if True:\n    pass')
        self.assertEquals(1, len(root.get_children()))

    def test_simple_else(self):
        root = source_suite_tree(
            'if True:\n    pass\nelse:\n    pass\n')
        self.assertEquals(2, len(root.get_children()))
        self.assertEquals(1, root.get_children()[1].get_start())

    def test_for(self):
        root = source_suite_tree(
            '\nfor i in range(10):\n    pass\nelse:\n    pass\n')
        self.assertEquals(2, len(root.get_children()))
        self.assertEquals(2, root.get_children()[1].get_start())

    def test_while(self):
        root = source_suite_tree(
            'while True:\n    pass\n')
        self.assertEquals(1, len(root.get_children()))
        self.assertEquals(1, root.get_children()[0].get_start())

    def test_with(self):
        root = source_suite_tree(
            'from __future__ import with_statement\nwith file(x):    pass\n')
        self.assertEquals(1, len(root.get_children()))
        self.assertEquals(2, root.get_children()[0].get_start())

    def test_try_finally(self):
        root = source_suite_tree(
            'try:\n    pass\nfinally:\n    pass\n')
        self.assertEquals(2, len(root.get_children()))
        self.assertEquals(1, root.get_children()[0].get_start())

    def test_try_except(self):
        root = source_suite_tree(
            'try:\n    pass\nexcept:\n    pass\nelse:\n    pass\n')
        self.assertEquals(3, len(root.get_children()))
        self.assertEquals(1, root.get_children()[2].get_start())

    def test_try_except_finally(self):
        root = source_suite_tree(
            'try:\n    pass\nexcept:\n    pass\nfinally:\n    pass\n')
        self.assertEquals(3, len(root.get_children()))
        self.assertEquals(1, root.get_children()[2].get_start())

    def test_local_start_and_end(self):
        root = source_suite_tree('if True:\n    pass\nelse:\n    pass\n')
        self.assertEquals(1, root.local_start())
        self.assertEquals(4, root.local_end())
        if_suite = root.get_children()[0]
        self.assertEquals(2, if_suite.local_start())
        self.assertEquals(2, if_suite.local_end())
        else_suite = root.get_children()[1]
        self.assertEquals(4, else_suite.local_start())
        self.assertEquals(4, else_suite.local_end())

    def test_find_suite(self):
        root = source_suite_tree('\n')
        self.assertEquals(root, root.find_suite(1))

    def test_find_suite_for_ifs(self):
        root = source_suite_tree('if True:\n    pass\n')
        if_suite = root.get_children()[0]
        self.assertEquals(if_suite, root.find_suite(2))

    def test_find_suite_for_between_suites(self):
        root = source_suite_tree(
            'if True:\n    pass\nprint(1)\nif True:\n    pass\n')
        if_suite1 = root.get_children()[0]
        if_suite2 = root.get_children()[1]
        self.assertEquals(if_suite1, root.find_suite(2))
        self.assertEquals(if_suite2, root.find_suite(5))
        self.assertEquals(root, root.find_suite(3))

    def test_simple_find_visible(self):
        root = source_suite_tree('a = 1\n')
        self.assertEquals(1, suites.find_visible_for_suite(root, [1]))

    def test_simple_find_visible_ifs(self):
        root = source_suite_tree('\nif True:\n    a = 1\n    b = 2\n')
        self.assertEquals(root.find_suite(3), root.find_suite(4))
        self.assertEquals(3, suites.find_visible_for_suite(root, [3, 4]))

    def test_simple_find_visible_for_else(self):
        root = source_suite_tree('\nif True:\n    pass\nelse:    pass\n')
        self.assertEquals(2, suites.find_visible_for_suite(root, [2, 4]))

    def test_simple_find_visible_for_different_suites(self):
        root = source_suite_tree('if True:\n    pass\na = 1\n'
                                 'if False:\n    pass\n')
        self.assertEquals(1, suites.find_visible_for_suite(root, [2, 3]))
        self.assertEquals(5, suites.find_visible_for_suite(root, [5]))
        self.assertEquals(1, suites.find_visible_for_suite(root, [2, 5]))

    def test_not_always_selecting_scope_start(self):
        root = source_suite_tree(
            'if True:\n    a = 1\n    if True:\n        pass\n'
            '    else:\n        pass\n')
        self.assertEquals(3, suites.find_visible_for_suite(root, [4, 6]))
        self.assertEquals(3, suites.find_visible_for_suite(root, [3, 5]))
        self.assertEquals(3, suites.find_visible_for_suite(root, [4, 5]))

    def test_ignoring_functions(self):
        root = source_suite_tree(
            'def f():\n    pass\na = 1\n')
        self.assertEquals(3, suites.find_visible_for_suite(root, [2, 3]))

    def test_ignoring_classes(self):
        root = source_suite_tree(
            'a = 1\nclass C():\n    pass\n')
        self.assertEquals(1, suites.find_visible_for_suite(root, [1, 3]))


def source_suite_tree(source):
    return suites.ast_suite_tree(ast.parse(source))


if __name__ == '__main__':
    unittest.main()
