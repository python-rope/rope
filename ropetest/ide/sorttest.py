import unittest
from rope.ide import sort
from ropetest import testutils


class SortScopesTest(unittest.TestCase):

    def setUp(self):
        super(SortScopesTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.get_pycore()
        self.mod = self.pycore.create_module(self.project.root, 'mod')

    def tearDown(self):
        testutils.remove_project(self.project)
        super(SortScopesTest, self).tearDown()

    def _do_sort(self, offset):
        sorter = sort.SortScopes(self.project, self.mod, offset)
        self.project.do(sorter.get_changes())

    def test_trivial_case(self):
        self.mod.write('\ndef a():\n    pass\n')
        self._do_sort(0)
        self.assertEquals('\ndef a():\n    pass\n', self.mod.read())

    def test_alphabetical_sorting_in_module_scope(self):
        self.mod.write('\ndef b():\n    pass\ndef a():\n    pass\n')
        self._do_sort(0)
        self.assertEquals('\ndef a():\n    pass\ndef b():\n    pass\n',
                          self.mod.read())

    def test_handling_blanks(self):
        self.mod.write('\ndef b():\n    pass\n\n\ndef a():\n    pass\n')
        self._do_sort(0)
        self.assertEquals('\ndef a():\n    pass\n\n\ndef b():\n    pass\n',
                          self.mod.read())

    def xxx_test_handling_statements(self):
        self.mod.write('\ndef a():\n    pass\nprint(b())\n'
                       'def b():\n    pass\n')
        self._do_sort(0)
        self.assertEquals(
            '\ndef a():\n    pass\nprint(b())\ndef b():\n    pass\n',
            self.mod.read())


if __name__ == '__main__':
    unittest.main()
