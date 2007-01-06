import unittest
import rope.base.exceptions
import rope.base.project
from ropetest import testutils


class InlineTest(unittest.TestCase):

    def setUp(self):
        super(InlineTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = rope.base.project.Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()
        self.mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
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

    @testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_on_classes(self):
        code = 'class AClass(object):\n    pass\n'
        refactored = self._inline(code, code.index('AClass') + 1)

    @testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_multiple_assignments(self):
        code = 'a_var = 10\na_var = 20\n'
        refactored = self._inline(code, code.index('a_var') + 1)

    @testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_on_parameters(self):
        code = 'def a_func(a_param):\n    pass\n'
        refactored = self._inline(code, code.index('a_param') + 1)

    @testutils.assert_raises(rope.base.exceptions.RefactoringException)
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

    def test_replacing_calls_with_function_definition_in_other_modules(self):
        self.mod.write('def a_func():\n    print 1\n')
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('import mod\nmod.a_func()\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('import mod\nprint 1\n', mod1.read())

    def test_replacing_calls_with_function_definition_in_other_modules2(self):
        self.mod.write('def a_func():\n    print 1\n')
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('import mod\nif True:\n    mod.a_func()\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('import mod\nif True:\n    print 1\n', mod1.read())

    def test_replacing_calls_with_method_definition_in_other_modules(self):
        self.mod.write('class A(object):\n    var = 10\n    def a_func(self):\n        print 1\n')
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('import mod\nmod.A().a_func()\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('import mod\nprint 1\n', mod1.read())
        self.assertEquals('class A(object):\n    var = 10\n', self.mod.read())

    def test_replacing_calls_with_function_definition_in_defining_module(self):
        self.mod.write('def a_func():\n    print 1\na_func()\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('print 1\n', self.mod.read())

    def test_replacing_calls_with_function_definition_in_defining_module2(self):
        self.mod.write('def a_func():\n    for i in range(10):\n        print 1\na_func()\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('for i in range(10):\n    print 1\n', self.mod.read())

    def test_replacing_calls_with_method_definition_in_defining_modules(self):
        self.mod.write('class A(object):\n    var = 10\n'
                       '    def a_func(self):\n        print 1\nA().a_func()')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('class A(object):\n    var = 10\nprint 1\n', self.mod.read())

    def test_parameters_with_the_same_name_as_passed(self):
        self.mod.write('def a_func(var):\n    print var\nvar = 1\na_func(var)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('var = 1\nprint var\n', self.mod.read())

    def test_parameters_with_the_same_name_as_passed2(self):
        self.mod.write('def a_func(var):\n    print var\nvar = 1\na_func(var=var)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('var = 1\nprint var\n', self.mod.read())

    def test_simple_parameters_renaming(self):
        self.mod.write('def a_func(param):\n    print param\nvar = 1\na_func(var)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('var = 1\nprint var\n', self.mod.read())

    def test_simple_parameters_renaming_for_multiple_params(self):
        self.mod.write('def a_func(param1, param2):\n    p = param1 + param2\n'
                       'var1 = 1\nvar2 = 1\na_func(var1, var2)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('var1 = 1\nvar2 = 1\np = var1 + var2\n', self.mod.read())

    def test_parameters_renaming_for_passed_constants(self):
        self.mod.write('def a_func(param):\n    print param\na_func(1)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('print 1\n', self.mod.read())

    def test_parameters_renaming_for_passed_statements(self):
        self.mod.write('def a_func(param):\n    print param\na_func((1 + 2) / 3)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('print (1 + 2) / 3\n', self.mod.read())

    def test_simple_parameters_renaming_for_multiple_params_using_keywords(self):
        self.mod.write('def a_func(param1, param2):\n    p = param1 + param2\n'
                       'var1 = 1\nvar2 = 1\na_func(param2=var1, param1=var2)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('var1 = 1\nvar2 = 1\np = var2 + var1\n', self.mod.read())

    def test_simple_parameters_renaming_for_multiple_params_using_mixed_keywords(self):
        self.mod.write('def a_func(param1, param2):\n    p = param1 + param2\n'
                       'var1 = 1\nvar2 = 1\na_func(var2, param2=var1)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('var1 = 1\nvar2 = 1\np = var2 + var1\n', self.mod.read())

    def test_simple_putting_in_default_arguments(self):
        self.mod.write('def a_func(param=None):\n    print param\n'
                       'a_func()\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('print None\n', self.mod.read())

    def test_overriding_default_arguments(self):
        self.mod.write('def a_func(param1=1, param2=2):\n    print param1, param2\n'
                       'a_func(param2=3)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('print 1, 3\n', self.mod.read())

    def test_badly_formatted_text(self):
        self.mod.write('def a_func  (  param1 =  1 ,param2 = 2 )  :\n    print param1, param2\n'
                       'a_func  ( param2 \n  = 3 )  \n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('print 1, 3\n', self.mod.read())

    def test_passing_first_arguments_for_methods(self):
        a_class = 'class A(object):\n' \
                  '    def __init__(self):\n' \
                  '        self.var = 1\n' \
                  '        self.a_func(self.var)\n' \
                  '    def a_func(self, param):\n' \
                  '        print param\n'
        self.mod.write(a_class)
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        expected = 'class A(object):\n' \
                   '    def __init__(self):\n' \
                   '        self.var = 1\n' \
                   '        print self.var\n'
        self.assertEquals(expected, self.mod.read())

    def test_passing_first_arguments_for_methods2(self):
        a_class = 'class A(object):\n' \
                  '    def __init__(self):\n' \
                  '        self.var = 1\n' \
                  '    def a_func(self, param):\n' \
                  '        print param, self.var\n' \
                  'an_a = A()\n' \
                  'an_a.a_func(1)\n'
        self.mod.write(a_class)
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        expected = 'class A(object):\n' \
                   '    def __init__(self):\n' \
                   '        self.var = 1\n' \
                   'an_a = A()\n' \
                   'print 1, an_a.var\n'
        self.assertEquals(expected, self.mod.read())

    # XXX: Handling ``AClass.a_method(a_var, param)``
    def xxx_test_passing_first_arguments_for_methods3(self):
        a_class = 'class A(object):\n' \
                  '    def __init__(self):\n' \
                  '        self.var = 1\n' \
                  '    def a_func(self, param):\n' \
                  '        print param, self.var\n' \
                  'an_a = A()\n' \
                  'A.a_func(an_a, 1)\n'
        self.mod.write(a_class)
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        expected = 'class A(object):\n' \
                   '    def __init__(self):\n' \
                   '        self.var = 1\n' \
                   'an_a = A()\n' \
                   'print 1, an_a.var\n'
        self.assertEquals(expected, self.mod.read())

    # XXX: The decorator should be removed, too
    def xxx_test_static_methods(self):
        a_class = 'class A(object):\n' \
                  '    var = 10\n' \
                  '    @staticmethod\n' \
                  '    def a_func(param):\n' \
                  '        print param\n' \
                  'an_a = A()\n' \
                  'an_a.a_func(1)\n' \
                  'A.a_func(2)\n'
        self.mod.write(a_class)
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        expected = 'class A(object):\n' \
                  '    var = 10\n' \
                  'an_a = A()\n' \
                  'print 1\n' \
                  'print 2\n'
        self.assertEquals(expected, self.mod.read())

    def test_simple_return_values_and_inlining_functions(self):
        self.mod.write('def a_func():\n    return 1\na = a_func()\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('a_func_result = 1\na = a_func_result\n',
                          self.mod.read())

    def test_simple_return_values_and_inlining_lonely_functions(self):
        self.mod.write('def a_func():\n    return 1\na_func()\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('1\n', self.mod.read())

    def test_empty_returns_and_inlining_lonely_functions(self):
        self.mod.write('def a_func():\n    if True:\n        return\na_func()\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('if True:\n    pass\n', self.mod.read())

    @testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_multiple_returns(self):
        self.mod.write('def less_than_five(var):\n    if var < 5:\n'
                       '        return True\n    return False\n'
                       'a = less_than_five(2)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('less') + 1)

    def test_multiple_returns_and_not_using_the_value(self):
        self.mod.write('def less_than_five(var):\n    if var < 5:\n'
                       '        return True\n    return False\nless_than_five(2)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('less') + 1)
        self.assertEquals('if 2 < 5:\n    True\nFalse\n', self.mod.read())

    @testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_raising_exception_for_list_arguments(self):
        self.mod.write('def a_func(*args):\n    print args\na_func(1)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)

    @testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_raising_exception_for_list_keywods(self):
        self.mod.write('def a_func(**kwds):\n    print kwds\na_func(n=1)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)

    def test_function_parameters_and_returns_in_other_functions(self):
        self.mod.write('def a_func(param1, param2):\n    return param1 + param2\n'
                       'range(a_func(20, param2=abs(10)))\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('a_func_result = 20 + abs(10)\nrange(a_func_result)\n',
                          self.mod.read())

    @testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_function_references_other_than_call(self):
        self.mod.write('def a_func(param):\n    print param\nf = a_func\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)

    @testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_function_referencing_itself(self):
        self.mod.write('def a_func(var):\n    func = a_func\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)

    @testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_recursive_functions(self):
        self.mod.write('def a_func(var):\n    a_func(var)\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)

    # TODO: inlining on function parameters
    def xxx_test_inlining_function_default_parameters(self):
        self.mod.write('def a_func(p1=1):\n    pass\na_func()\n')
        self.refactoring.inline(self.mod, self.mod.read().index('p1') + 1)
        self.assertEquals('def a_func(p1=1):\n    pass\na_func()\n', self.mod.read())

    def test_simple_inlining_after_extra_indented_lines(self):
        self.mod.write('def a_func():\n    for i in range(10):\n        pass\n'
                       'if True:\n    pass\na_func()\n')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('if True:\n    pass\nfor i in range(10):\n    pass\n',
                          self.mod.read())

    def test_inlining_a_function_with_pydoc(self):
        self.mod.write('def a_func():\n    """docs"""\n    a = 1\na_func()')
        self.refactoring.inline(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEquals('a = 1\n', self.mod.read())

    def test_inlining_methods(self):
        self.mod.write("class A(object):\n    name = 'hey'\n"
                       "    def get_name(self):\n        return self.name\n"
                       "a = A()\nname = a.get_name()\n")
        self.refactoring.inline(self.mod, self.mod.read().rindex('get_name') + 1)
        self.assertEquals("class A(object):\n    name = 'hey'\n"
                          "a = A()\nget_name_result = a.name\nname = get_name_result\n",
                          self.mod.read())


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(InlineTest))
    return result


if __name__ == '__main__':
    unittest.main()
