import os
import unittest

from rope.ide.outline import PythonOutline
from rope.base.project import Project
from ropetest import testutils

class OutlineTest(unittest.TestCase):

    def setUp(self):
        super(OutlineTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        os.mkdir(self.project_root)
        self.project = Project(self.project_root)
        self.outline = PythonOutline(self.project)

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(OutlineTest, self).tearDown()

    def test_simple_outline(self):
        nodes = self.outline.get_root_nodes('')
        self.assertEquals(0, len(nodes))

    def test_simple_outlines(self):
        nodes = self.outline.get_root_nodes('def a_func():\n    pass\n')
        self.assertEquals(1, len(nodes))
        self.assertEquals('a_func', nodes[0].get_name())
        self.assertEquals(1, nodes[0].get_line_number())
        self.assertEquals(0, len(nodes[0].get_children()))

    def test_nested_outlines(self):
        nodes = self.outline.get_root_nodes('class Sample(object):\n    def a_method(self):\n        pass\n')
        self.assertEquals(1, len(nodes))
        self.assertEquals('Sample', nodes[0].get_name())
        sample_class = nodes[0]
        self.assertEquals(1, sample_class.get_line_number())
        self.assertEquals(1, len(sample_class.get_children()))
        a_method = sample_class.get_children()[0]
        self.assertEquals('a_method', a_method.get_name())
        self.assertEquals(2, a_method.get_line_number())

    def test_sorting_by_line_number(self):
        nodes = self.outline.get_root_nodes('def a_func2():\n    pass\ndef a_func1():\n    pass\n')
        self.assertEquals('a_func2', nodes[0].get_name())
        self.assertEquals('a_func1', nodes[1].get_name())

    def test_not_showing_inherited_names(self):
        src = 'class Base(object):\n    def a_method(self):\n        pass\n\n' + \
              'class Derived(Base):\n    pass\n'
        nodes = self.outline.get_root_nodes(src)
        self.assertEquals(0, len(nodes[1].get_children()))


if __name__ == '__main__':
    unittest.main()

