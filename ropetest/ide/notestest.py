import unittest

from rope.ide import notes
from ropetest import testutils


class AnnotationsTest(unittest.TestCase):

    def setUp(self):
        super(AnnotationsTest, self).setUp()
        self.project = testutils.sample_project()
        self.tags = notes.Codetags()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(AnnotationsTest, self).tearDown()

    def test_tags_empty_input(self):
        self.assertEquals([], self.tags.tags(''))

    def test_tags_trivial_case(self):
        self.assertEquals([(1, 'TODO: todo')], self.tags.tags('# TODO: todo\n'))

    def test_two_codetags(self):
        self.assertEquals(
            [(1, 'XXX: todo'), (3, 'FIXME: fix me')],
             self.tags.tags('# XXX: todo\n\n# FIXME: fix me\n'))

    def test_errors_empty_input(self):
        errors = notes.Errors()
        self.assertEquals([], errors.errors(''))

    def test_errors_trival_error(self):
        errors = notes.Errors()
        self.assertEquals([(1, 'invalid syntax')],
                          errors.errors('error input\n'))

    def test_warnings_empty_input(self):
        warnings = notes.Warnings()
        self.assertEquals([], warnings.warnings(''))

    def test_warnings_redefining_functions_in_global_scope(self):
        warnings = notes.Warnings()
        self.assertEquals([(3, 'Rebinding defined name <f>')],
                          warnings.warnings('def f():\n    pass\nf = 1\n'))

    def test_warnings_redefining_classes_in_global_scope(self):
        warnings = notes.Warnings()
        self.assertEquals([(3, 'Rebinding defined name <C>')],
                          warnings.warnings('class C(object):\n    pass\nC = 1\n'))

    def test_warnings_redefining_nested_scopes(self):
        warnings = notes.Warnings()
        self.assertEquals(
            [(4, 'Rebinding defined name <g>')], warnings.warnings(
            'def f():\n    def g():\n        pass\n    g = 1\n'))

    def test_warnings_not_redefining_in_nested_scopes(self):
        warnings = notes.Warnings()
        self.assertEquals([], warnings.warnings(
                          'def f():\n    def g():\n        pass\ng = 1\n'))

    def test_warnings_redefining_functions_by_functions(self):
        warnings = notes.Warnings()
        self.assertEquals([(3, 'Rebinding defined name <f>')],
                          warnings.warnings('def f():\n    pass\n'
                                            'def f():\n    pass\n'))

    def test_self_assignment_warnings(self):
        warnings = notes.Warnings()
        self.assertEquals([(2, 'Assigning <a> to itself')],
                          warnings.warnings('a = 1\na = a\n'))

    def test_self_assignment_warnings(self):
        warnings = notes.Warnings()
        self.assertEquals([(2, 'Assigning <a.b> to itself')],
                          warnings.warnings('a = None\na.b = a.b\n'))


if __name__ == '__main__':
    unittest.main()
