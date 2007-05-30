import unittest

from rope.refactor import suites


class SuiteTest(unittest.TestCase):

    def setUp(self):
        super(SuiteTest, self).setUp()

    def tearDown(self):
        super(SuiteTest, self).tearDown()

    def test_trivial_case(self):
        root = suites.source_suite_tree('')
        self.assertEquals(1, root.get_start())
        self.assertEquals(0, len(root.get_children()))

    def test_simple_ifs(self):
        root = suites.source_suite_tree('if True:\n    pass')
        self.assertEquals(1, len(root.get_children()))

    def test_simple_else(self):
        root = suites.source_suite_tree(
            'if True:\n    pass\nelse:\n    pass\n')
        self.assertEquals(2, len(root.get_children()))
        self.assertEquals(1, root.get_children()[1].get_start())

    def test_ignoring_function_and_class_defs(self):
        root = suites.source_suite_tree(
            'def f():\n    if True:        pass\nclass C(object):\n    pass\n')
        self.assertEquals(0, len(root.get_children()))

    def test_for(self):
        root = suites.source_suite_tree(
            '\nfor i in range(10):\n    pass\nelse:\n    pass\n')
        self.assertEquals(2, len(root.get_children()))
        self.assertEquals(2, root.get_children()[1].get_start())

    def test_while(self):
        root = suites.source_suite_tree(
            'while True:\n    pass\n')
        self.assertEquals(1, len(root.get_children()))
        self.assertEquals(1, root.get_children()[0].get_start())

    def test_with(self):
        root = suites.source_suite_tree(
            'from __future__ import with_statement\nwith file(x):    pass\n')
        self.assertEquals(1, len(root.get_children()))
        self.assertEquals(2, root.get_children()[0].get_start())

    def test_try_finally(self):
        root = suites.source_suite_tree(
            'try:\n    pass\nfinally:\n    pass\n')
        self.assertEquals(2, len(root.get_children()))
        self.assertEquals(1, root.get_children()[0].get_start())

    def test_try_except(self):
        root = suites.source_suite_tree(
            'try:\n    pass\nexcept:\n    pass\nelse:\n    pass\n')
        self.assertEquals(3, len(root.get_children()))
        self.assertEquals(1, root.get_children()[2].get_start())

    def test_try_except_finally(self):
        root = suites.source_suite_tree(
            'try:\n    pass\nexcept:\n    pass\nfinally:\n    pass\n')
        self.assertEquals(3, len(root.get_children()))
        self.assertEquals(1, root.get_children()[2].get_start())


if __name__ == '__main__':
    unittest.main()
