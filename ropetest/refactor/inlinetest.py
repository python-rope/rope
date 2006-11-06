import unittest
import rope.base.exceptions
import rope.base.project
import ropetest


class InlineTest(unittest.TestCase):

    def setUp(self):
        super(InlineTest, self).setUp()
        self.project_root = 'sample_project'
        ropetest.testutils.remove_recursively(self.project_root)
        self.project = rope.base.project.Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()
        self.mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')

    def tearDown(self):
        ropetest.testutils.remove_recursively(self.project_root)
        super(InlineTest, self).tearDown()
    
    def _inline(self, code, offset):
        self.mod.write(code)
        self.refactoring.inline(self.mod, offset)
        return self.mod.read()
    
    def test_simple_case(self):
        code = 'a_var = 10\nanother_var = a_var\n'
        refactored = self._inline(code, code.index('a_var') + 1)
        self.assertEquals('another_var = 10\n', refactored)        

    def test_empty_case(self):
        code = 'a_var = 10\n'
        refactored = self._inline(code, code.index('a_var') + 1)
        self.assertEquals('', refactored)        

    def test_long_definition(self):
        code = 'a_var = 10 + (10 + 10)\nanother_var = a_var\n'
        refactored = self._inline(code, code.index('a_var') + 1)
        self.assertEquals('another_var = 10 + (10 + 10)\n', refactored)        

    def test_explicit_continuation(self):
        code = 'a_var = (10 +\n 10)\nanother_var = a_var\n'
        refactored = self._inline(code, code.index('a_var') + 1)
        self.assertEquals('another_var = (10 + 10)\n', refactored)        

    def test_implicit_continuation(self):
        code = 'a_var = 10 +\\\n       10\nanother_var = a_var\n'
        refactored = self._inline(code, code.index('a_var') + 1)
        self.assertEquals('another_var = 10 + 10\n', refactored)        

    def test_inlining_at_the_end_of_input(self):
        code = 'a = 1\nb = a'
        refactored = self._inline(code, code.index('a') + 1)
        self.assertEquals('b = 1', refactored)

    @ropetest.testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_on_classes(self):
        code = 'class AClass(object):\n    pass\n'
        refactored = self._inline(code, code.index('AClass') + 1)

    @ropetest.testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_multiple_assignments(self):
        code = 'a_var = 10\na_var = 20\n'
        refactored = self._inline(code, code.index('a_var') + 1)

    @ropetest.testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_on_parameters(self):
        code = 'def a_func(a_param):\n    pass\n'
        refactored = self._inline(code, code.index('a_param') + 1)

    @ropetest.testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_tuple_assignments(self):
        code = 'a_var, another_var = (20, 30)\n'
        refactored = self._inline(code, code.index('a_var') + 1)

    def test_attribute_inlining(self):
        code = 'class A(object):\n    def __init__(self):\n' \
               '        self.an_attr = 3\n        range(self.an_attr)\n'
        refactored = self._inline(code, code.index('an_attr') + 1)
        expected = 'class A(object):\n    def __init__(self):\n' \
                   '        range(3)\n'
        self.assertEquals(expected, refactored)

    def test_attribute_inlining2(self):
        code = 'class A(object):\n    def __init__(self):\n' \
               '        self.an_attr = 3\n        range(self.an_attr)\n' \
               'a = A()\nrange(a.an_attr)'
        refactored = self._inline(code, code.index('an_attr') + 1)
        expected = 'class A(object):\n    def __init__(self):\n' \
                   '        range(3)\n' \
                   'a = A()\nrange(3)'
        self.assertEquals(expected, refactored)


    def test_a_function_with_no_occurance(self):
        self.mod.write('def a_func():\n    pass\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('', self.mod.read())

    def test_a_function_with_no_occurance2(self):
        self.mod.write('a_var = 10\ndef a_func():\n    pass\nprint a_var\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('a_var = 10\nprint a_var\n', self.mod.read())

    # Implement this
    def xxx_test_a_function_with_no_occurance2(self):
        self.mod.write('def a_func():\n    print 1\n')
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('import mod\nmod.a_func()\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('import mod\nprint 1\n', self.mod.read())

    
def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(InlineTest))
    return result


if __name__ == '__main__':
    unittest.main()
