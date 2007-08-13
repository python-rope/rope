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

    def _do_sort(self, offset, sorter=None):
        sort_scopes = sort.SortScopes(self.project, self.mod, offset)
        self.project.do(sort_scopes.get_changes(sorter))

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

    def test_handling_statements(self):
        self.mod.write('\ndef b():\n    pass\nprint(b())\n'
                       'def a():\n    pass\n')
        self._do_sort(0)
        self.assertEquals(
            '\ndef a():\n    pass\ndef b():\n    pass\nprint(b())\n',
            self.mod.read())

    def test_nested_scopes(self):
        self.mod.write(
            'class C(object):\n\n    def b():\n        pass\n\n    print(b())\n\n'
            '    def a():\n        pass\n\n\ndef a():\n    pass\n')
        self._do_sort(2)
        self.assertEquals(
            'class C(object):\n\n    def a():\n        pass\n\n'
            '    def b():\n        pass\n\n    print(b())\n\n\ndef a():\n    pass\n',
            self.mod.read())

    def test_classes_first(self):
        self.mod.write('\ndef a():\n    pass\n\nclass b():\n    pass\n')
        self._do_sort(0, sort.KindSorter())
        self.assertEquals('\nclass b():\n    pass\n\ndef a():\n    pass\n',
                          self.mod.read())

    def test_functions_first(self):
        self.mod.write('\ndef a():\n    pass\n\nclass b():\n    pass\n')
        self._do_sort(0, sort.KindSorter(reverse=True))
        self.assertEquals('\ndef a():\n    pass\n\nclass b():\n    pass\n',
                          self.mod.read())

    def test_underlined_last(self):
        self.mod.write('\ndef _a():\n    pass\n\ndef a():\n    pass\n')
        self._do_sort(0, sort.UnderlinedSorter(reverse=True))
        self.assertEquals('\ndef a():\n    pass\n\ndef _a():\n    pass\n',
                          self.mod.read())

    def test_special_last(self):
        self.mod.write('\ndef __a__():\n    pass\n\ndef a():\n    pass\n')
        self._do_sort(0, sort.SpecialSorter(reverse=True))
        self.assertEquals('\ndef a():\n    pass\n\ndef __a__():\n    pass\n',
                          self.mod.read())

    def test_classes_first(self):
        self.mod.write('\ndef a():\n    pass\n\nclass b():\n    """pydoc"""\n')
        self._do_sort(0, sort.PydocSorter())
        self.assertEquals('\nclass b():\n    """pydoc"""\n\ndef a():\n    pass\n',
                          self.mod.read())


if __name__ == '__main__':
    unittest.main()
