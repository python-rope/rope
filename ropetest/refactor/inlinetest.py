try:
    import unittest2 as unittest
except ImportError:
    import unittest

import rope.base.exceptions
from rope.refactor import inline
from ropetest import testutils


class InlineTest(unittest.TestCase):

    def setUp(self):
        super(InlineTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, 'mod')
        self.mod2 = testutils.create_module(self.project, 'mod2')

    def tearDown(self):
        testutils.remove_project(self.project)
        super(InlineTest, self).tearDown()

    def _inline(self, code, offset, **kwds):
        self.mod.write(code)
        self._inline2(self.mod, offset, **kwds)
        return self.mod.read()

    def _inline2(self, resource, offset, **kwds):
        inliner = inline.create_inline(self.project, resource, offset)
        changes = inliner.get_changes(**kwds)
        self.project.do(changes)
        return self.mod.read()

    def test_simple_case(self):
        code = 'a_var = 10\nanother_var = a_var\n'
        refactored = self._inline(code, code.index('a_var') + 1)
        self.assertEqual('another_var = 10\n', refactored)

    def test_empty_case(self):
        code = 'a_var = 10\n'
        refactored = self._inline(code, code.index('a_var') + 1)
        self.assertEqual('', refactored)

    def test_long_definition(self):
        code = 'a_var = 10 + (10 + 10)\nanother_var = a_var\n'
        refactored = self._inline(code, code.index('a_var') + 1)
        self.assertEqual('another_var = 10 + (10 + 10)\n', refactored)

    def test_explicit_continuation(self):
        code = 'a_var = (10 +\n 10)\nanother_var = a_var\n'
        refactored = self._inline(code, code.index('a_var') + 1)
        self.assertEqual('another_var = (10 + 10)\n', refactored)

    def test_implicit_continuation(self):
        code = 'a_var = 10 +\\\n       10\nanother_var = a_var\n'
        refactored = self._inline(code, code.index('a_var') + 1)
        self.assertEqual('another_var = 10 + 10\n', refactored)

    def test_inlining_at_the_end_of_input(self):
        code = 'a = 1\nb = a'
        refactored = self._inline(code, code.index('a') + 1)
        self.assertEqual('b = 1', refactored)

    def test_on_classes(self):
        code = 'class AClass(object):\n    pass\n'
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline(code, code.index('AClass') + 1)

    def test_multiple_assignments(self):
        code = 'a_var = 10\na_var = 20\n'
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline(code, code.index('a_var') + 1)

    def test_tuple_assignments(self):
        code = 'a_var, another_var = (20, 30)\n'
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline(code, code.index('a_var') + 1)

    def test_on_unknown_vars(self):
        code = 'a_var = another_var\n'
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline(code, code.index('another_var') + 1)

    def test_attribute_inlining(self):
        code = 'class A(object):\n    def __init__(self):\n' \
               '        self.an_attr = 3\n        range(self.an_attr)\n'
        refactored = self._inline(code, code.index('an_attr') + 1)
        expected = 'class A(object):\n    def __init__(self):\n' \
                   '        range(3)\n'
        self.assertEqual(expected, refactored)

    def test_attribute_inlining2(self):
        code = 'class A(object):\n    def __init__(self):\n' \
               '        self.an_attr = 3\n        range(self.an_attr)\n' \
               'a = A()\nrange(a.an_attr)'
        refactored = self._inline(code, code.index('an_attr') + 1)
        expected = 'class A(object):\n    def __init__(self):\n' \
                   '        range(3)\n' \
                   'a = A()\nrange(3)'
        self.assertEqual(expected, refactored)

    def test_a_function_with_no_occurance(self):
        self.mod.write('def a_func():\n    pass\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('', self.mod.read())

    def test_a_function_with_no_occurance2(self):
        self.mod.write('a_var = 10\ndef a_func():\n    pass\nprint(a_var)\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('a_var = 10\nprint(a_var)\n', self.mod.read())

    def test_replacing_calls_with_function_definition_in_other_modules(self):
        self.mod.write('def a_func():\n    print(1)\n')
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('import mod\nmod.a_func()\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('import mod\nprint(1)\n', mod1.read())

    def test_replacing_calls_with_function_definition_in_other_modules2(self):
        self.mod.write('def a_func():\n    print(1)\n')
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('import mod\nif True:\n    mod.a_func()\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('import mod\nif True:\n    print(1)\n', mod1.read())

    def test_replacing_calls_with_method_definition_in_other_modules(self):
        self.mod.write('class A(object):\n    var = 10\n'
                       '    def a_func(self):\n        print(1)\n')
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('import mod\nmod.A().a_func()\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('import mod\nprint(1)\n', mod1.read())
        self.assertEqual('class A(object):\n    var = 10\n', self.mod.read())

    def test_replacing_calls_with_function_definition_in_defining_module(self):
        self.mod.write('def a_func():\n    print(1)\na_func()\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('print(1)\n', self.mod.read())

    def test_replac_calls_with_function_definition_in_defining_module2(self):
        self.mod.write('def a_func():\n    '
                       'for i in range(10):\n        print(1)\na_func()\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('for i in range(10):\n    print(1)\n',
                          self.mod.read())

    def test_replacing_calls_with_method_definition_in_defining_modules(self):
        self.mod.write('class A(object):\n    var = 10\n'
                       '    def a_func(self):\n        print(1)\nA().a_func()')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('class A(object):\n    var = 10\nprint(1)\n',
                          self.mod.read())

    def test_parameters_with_the_same_name_as_passed(self):
        self.mod.write('def a_func(var):\n    '
                       'print(var)\nvar = 1\na_func(var)\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('var = 1\nprint(var)\n', self.mod.read())

    def test_parameters_with_the_same_name_as_passed2(self):
        self.mod.write('def a_func(var):\n    '
                       'print(var)\nvar = 1\na_func(var=var)\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('var = 1\nprint(var)\n', self.mod.read())

    def test_simple_parameters_renaming(self):
        self.mod.write('def a_func(param):\n    '
                       'print(param)\nvar = 1\na_func(var)\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('var = 1\nprint(var)\n', self.mod.read())

    def test_simple_parameters_renaming_for_multiple_params(self):
        self.mod.write('def a_func(param1, param2):\n    p = param1 + param2\n'
                       'var1 = 1\nvar2 = 1\na_func(var1, var2)\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('var1 = 1\nvar2 = 1\np = var1 + var2\n',
                          self.mod.read())

    def test_parameters_renaming_for_passed_constants(self):
        self.mod.write('def a_func(param):\n    print(param)\na_func(1)\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('print(1)\n', self.mod.read())

    def test_parameters_renaming_for_passed_statements(self):
        self.mod.write('def a_func(param):\n    '
                       'print(param)\na_func((1 + 2) / 3)\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('print((1 + 2) / 3)\n', self.mod.read())

    def test_simple_parameters_renam_for_multiple_params_using_keywords(self):
        self.mod.write('def a_func(param1, param2):\n    '
                       'p = param1 + param2\n'
                       'var1 = 1\nvar2 = 1\n'
                       'a_func(param2=var1, param1=var2)\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('var1 = 1\nvar2 = 1\np = var2 + var1\n',
                          self.mod.read())

    def test_simple_params_renam_for_multi_params_using_mixed_keywords(self):
        self.mod.write('def a_func(param1, param2):\n    p = param1 + param2\n'
                       'var1 = 1\nvar2 = 1\na_func(var2, param2=var1)\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('var1 = 1\nvar2 = 1\np = var2 + var1\n',
                          self.mod.read())

    def test_simple_putting_in_default_arguments(self):
        self.mod.write('def a_func(param=None):\n    print(param)\n'
                       'a_func()\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('print(None)\n', self.mod.read())

    def test_overriding_default_arguments(self):
        self.mod.write('def a_func(param1=1, param2=2):'
                       '\n    print(param1, param2)\n'
                       'a_func(param2=3)\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('print(1, 3)\n', self.mod.read())

    def test_arguments_containing_comparisons(self):
        self.mod.write('def a_func(param1, param2, param3):'
                       '\n    param2.name\n'
                       'a_func(2 <= 1, item, True)\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('item.name\n', self.mod.read())

    def test_badly_formatted_text(self):
        self.mod.write('def a_func  (  param1 =  1 ,param2 = 2 )  :'
                       '\n    print(param1, param2)\n'
                       'a_func  ( param2 \n  = 3 )  \n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('print(1, 3)\n', self.mod.read())

    def test_passing_first_arguments_for_methods(self):
        a_class = 'class A(object):\n' \
                  '    def __init__(self):\n' \
                  '        self.var = 1\n' \
                  '        self.a_func(self.var)\n' \
                  '    def a_func(self, param):\n' \
                  '        print(param)\n'
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        expected = 'class A(object):\n' \
                   '    def __init__(self):\n' \
                   '        self.var = 1\n' \
                   '        print(self.var)\n'
        self.assertEqual(expected, self.mod.read())

    def test_passing_first_arguments_for_methods2(self):
        a_class = 'class A(object):\n' \
                  '    def __init__(self):\n' \
                  '        self.var = 1\n' \
                  '    def a_func(self, param):\n' \
                  '        print(param, self.var)\n' \
                  'an_a = A()\n' \
                  'an_a.a_func(1)\n'
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        expected = 'class A(object):\n' \
                   '    def __init__(self):\n' \
                   '        self.var = 1\n' \
                   'an_a = A()\n' \
                   'print(1, an_a.var)\n'
        self.assertEqual(expected, self.mod.read())

    def test_passing_first_arguments_for_methods3(self):
        a_class = 'class A(object):\n' \
                  '    def __init__(self):\n' \
                  '        self.var = 1\n' \
                  '    def a_func(self, param):\n' \
                  '        print(param, self.var)\n' \
                  'an_a = A()\n' \
                  'A.a_func(an_a, 1)\n'
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        expected = 'class A(object):\n' \
                   '    def __init__(self):\n' \
                   '        self.var = 1\n' \
                   'an_a = A()\n' \
                   'print(1, an_a.var)\n'
        self.assertEqual(expected, self.mod.read())

    def test_inlining_staticmethods(self):
        a_class = 'class A(object):\n' \
                  '    @staticmethod\n' \
                  '    def a_func(param):\n' \
                  '        print(param)\n' \
                  'A.a_func(1)\n'
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        expected = 'class A(object):\n' \
            '    pass\n' \
            'print(1)\n'
        self.assertEqual(expected, self.mod.read())

    def test_static_methods2(self):
        a_class = 'class A(object):\n' \
                  '    var = 10\n' \
                  '    @staticmethod\n' \
                  '    def a_func(param):\n' \
                  '        print(param)\n' \
                  'an_a = A()\n' \
                  'an_a.a_func(1)\n' \
                  'A.a_func(2)\n'
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        expected = 'class A(object):\n' \
            '    var = 10\n' \
            'an_a = A()\n' \
            'print(1)\n' \
            'print(2)\n'
        self.assertEqual(expected, self.mod.read())

    def test_inlining_classmethods(self):
        a_class = 'class A(object):\n' \
                  '    @classmethod\n' \
                  '    def a_func(cls, param):\n' \
                  '        print(param)\n' \
                  'A.a_func(1)\n'
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        expected = 'class A(object):\n' \
                   '    pass\n' \
                   'print(1)\n'
        self.assertEqual(expected, self.mod.read())

    def test_inlining_classmethods2(self):
        a_class = 'class A(object):\n' \
                  '    @classmethod\n' \
                  '    def a_func(cls, param):\n' \
                  '        return cls\n' \
                  'print(A.a_func(1))\n'
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        expected = 'class A(object):\n' \
                   '    pass\n' \
                   'print(A)\n'
        self.assertEqual(expected, self.mod.read())

    def test_simple_return_values_and_inlining_functions(self):
        self.mod.write('def a_func():\n    return 1\na = a_func()\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('a = 1\n',
                          self.mod.read())

    def test_simple_return_values_and_inlining_lonely_functions(self):
        self.mod.write('def a_func():\n    return 1\na_func()\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('1\n', self.mod.read())

    def test_empty_returns_and_inlining_lonely_functions(self):
        self.mod.write('def a_func():\n    '
                       'if True:\n        return\na_func()\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('if True:\n    pass\n', self.mod.read())

    def test_multiple_returns(self):
        self.mod.write('def less_than_five(var):\n    if var < 5:\n'
                       '        return True\n    return False\n'
                       'a = less_than_five(2)\n')
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline2(self.mod, self.mod.read().index('less') + 1)

    def test_multiple_returns_and_not_using_the_value(self):
        self.mod.write('def less_than_five(var):\n    if var < 5:\n'
                       '        return True\n    '
                       'return False\nless_than_five(2)\n')
        self._inline2(self.mod, self.mod.read().index('less') + 1)
        self.assertEqual('if 2 < 5:\n    True\nFalse\n', self.mod.read())

    def test_raising_exception_for_list_arguments(self):
        self.mod.write('def a_func(*args):\n    print(args)\na_func(1)\n')
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline2(self.mod, self.mod.read().index('a_func') + 1)

    def test_raising_exception_for_list_keywods(self):
        self.mod.write('def a_func(**kwds):\n    print(kwds)\na_func(n=1)\n')
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline2(self.mod, self.mod.read().index('a_func') + 1)

    def test_function_parameters_and_returns_in_other_functions(self):
        code = 'def a_func(param1, param2):\n' \
               '    return param1 + param2\n' \
               'range(a_func(20, param2=abs(10)))\n'
        self.mod.write(code)
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('range(20 + abs(10))\n', self.mod.read())

    def test_function_references_other_than_call(self):
        self.mod.write('def a_func(param):\n    print(param)\nf = a_func\n')
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline2(self.mod, self.mod.read().index('a_func') + 1)

    def test_function_referencing_itself(self):
        self.mod.write('def a_func(var):\n    func = a_func\n')
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline2(self.mod, self.mod.read().index('a_func') + 1)

    def test_recursive_functions(self):
        self.mod.write('def a_func(var):\n    a_func(var)\n')
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline2(self.mod, self.mod.read().index('a_func') + 1)

    # TODO: inlining on function parameters
    def xxx_test_inlining_function_default_parameters(self):
        self.mod.write('def a_func(p1=1):\n    pass\na_func()\n')
        self._inline2(self.mod, self.mod.read().index('p1') + 1)
        self.assertEqual('def a_func(p1=1):\n    pass\na_func()\n',
                          self.mod.read())

    def test_simple_inlining_after_extra_indented_lines(self):
        self.mod.write('def a_func():\n    for i in range(10):\n        pass\n'
                       'if True:\n    pass\na_func()\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('if True:\n    pass\nfor i in range(10):'
                          '\n    pass\n',
                          self.mod.read())

    def test_inlining_a_function_with_pydoc(self):
        self.mod.write('def a_func():\n    """docs"""\n    a = 1\na_func()')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('a = 1\n', self.mod.read())

    def test_inlining_methods(self):
        self.mod.write("class A(object):\n    name = 'hey'\n"
                       "    def get_name(self):\n        return self.name\n"
                       "a = A()\nname = a.get_name()\n")
        self._inline2(self.mod, self.mod.read().rindex('get_name') + 1)
        self.assertEqual("class A(object):\n    name = 'hey'\n"
                          "a = A()\nname = a.name\n", self.mod.read())

    def test_simple_returns_with_backslashes(self):
        self.mod.write('def a_func():\n    return 1'
                       '\\\n        + 2\na = a_func()\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('a = 1 + 2\n', self.mod.read())

    def test_a_function_with_pass_body(self):
        self.mod.write('def a_func():\n    print(1)\na = a_func()\n')
        self._inline2(self.mod, self.mod.read().index('a_func') + 1)
        self.assertEqual('print(1)\na = None\n', self.mod.read())

    def test_inlining_the_last_method_of_a_class(self):
        self.mod.write('class A(object):\n'
                       '    def a_func(self):\n        pass\n')
        self._inline2(self.mod, self.mod.read().rindex('a_func') + 1)
        self.assertEqual('class A(object):\n    pass\n',
                          self.mod.read())

    def test_adding_needed_imports_in_the_dest_module(self):
        self.mod.write('import sys\n\ndef ver():\n    print(sys.version)\n')
        self.mod2.write('import mod\n\nmod.ver()')
        self._inline2(self.mod, self.mod.read().index('ver') + 1)
        self.assertEqual('import mod\nimport sys\n\nprint(sys.version)\n',
                          self.mod2.read())

    def test_adding_needed_imports_in_the_dest_module_removing_selfs(self):
        self.mod.write('import mod2\n\ndef f():\n    print(mod2.var)\n')
        self.mod2.write('import mod\n\nvar = 1\nmod.f()\n')
        self._inline2(self.mod, self.mod.read().index('f(') + 1)
        self.assertEqual('import mod\n\nvar = 1\nprint(var)\n',
                          self.mod2.read())

    def test_handling_relative_imports_when_inlining(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod3 = testutils.create_module(self.project, 'mod3', pkg)
        mod4 = testutils.create_module(self.project, 'mod4', pkg)
        mod4.write('var = 1\n')
        mod3.write('from . import mod4\n\ndef f():\n    print(mod4.var)\n')
        self.mod.write('import pkg.mod3\n\npkg.mod3.f()\n')
        self._inline2(self.mod, self.mod.read().index('f(') + 1)
        # Cannot determine the exact import
        self.assertTrue('\n\nprint(mod4.var)\n' in self.mod.read())

    def test_adding_needed_imports_for_elements_in_source(self):
        self.mod.write('def f1():\n    return f2()\ndef f2():\n    return 1\n')
        self.mod2.write('import mod\n\nprint(mod.f1())\n')
        self._inline2(self.mod, self.mod.read().index('f1') + 1)
        self.assertEqual('import mod\nfrom mod import f2\n\nprint(f2())\n',
                          self.mod2.read())

    def test_relative_imports_and_changing_inlining_body(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod3 = testutils.create_module(self.project, 'mod3', pkg)
        mod4 = testutils.create_module(self.project, 'mod4', pkg)
        mod4.write('var = 1\n')
        mod3.write('import mod4\n\ndef f():\n    print(mod4.var)\n')
        self.mod.write('import pkg.mod3\n\npkg.mod3.f()\n')
        self._inline2(self.mod, self.mod.read().index('f(') + 1)
        self.assertEqual(
            'import pkg.mod3\nimport pkg.mod4\n\nprint(pkg.mod4.var)\n',
            self.mod.read())

    def test_inlining_with_different_returns(self):
        self.mod.write('def f(p):\n    return p\n'
                       'print(f(1))\nprint(f(2))\nprint(f(1))\n')
        self._inline2(self.mod, self.mod.read().index('f(') + 1)
        self.assertEqual('print(1)\nprint(2)\nprint(1)\n',
                          self.mod.read())

    def test_not_removing_definition_for_variables(self):
        code = 'a_var = 10\nanother_var = a_var\n'
        refactored = self._inline(code, code.index('a_var') + 1,
                                  remove=False)
        self.assertEqual('a_var = 10\nanother_var = 10\n', refactored)

    def test_not_removing_definition_for_methods(self):
        code = 'def func():\n    print(1)\n\nfunc()\n'
        refactored = self._inline(code, code.index('func') + 1,
                                  remove=False)
        self.assertEqual('def func():\n    print(1)\n\nprint(1)\n',
                          refactored)

    def test_only_current_for_methods(self):
        code = 'def func():\n    print(1)\n\nfunc()\nfunc()\n'
        refactored = self._inline(code, code.rindex('func') + 1,
                                  remove=False, only_current=True)
        self.assertEqual('def func():\n    print(1)\n\nfunc()\nprint(1)\n',
                          refactored)

    def test_only_current_for_variables(self):
        code = 'one = 1\n\na = one\nb = one\n'
        refactored = self._inline(code, code.rindex('one') + 1,
                                  remove=False, only_current=True)
        self.assertEqual('one = 1\n\na = one\nb = 1\n', refactored)

    def test_inlining_one_line_functions(self):
        code = 'def f(): return 1\nvar = f()\n'
        refactored = self._inline(code, code.rindex('f'))
        self.assertEqual('var = 1\n', refactored)

    def test_inlining_one_line_functions_with_breaks(self):
        code = 'def f(\np): return p\nvar = f(1)\n'
        refactored = self._inline(code, code.rindex('f'))
        self.assertEqual('var = 1\n', refactored)

    def test_inlining_one_line_functions_with_breaks2(self):
        code = 'def f(\n): return 1\nvar = f()\n'
        refactored = self._inline(code, code.rindex('f'))
        self.assertEqual('var = 1\n', refactored)

    def test_resources_parameter(self):
        self.mod.write('def a_func():\n    print(1)\n')
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('import mod\nmod.a_func()\n')
        self._inline2(self.mod, self.mod.read().index('a_func'),
                      resources=[self.mod])
        self.assertEqual('', self.mod.read())
        self.assertEqual('import mod\nmod.a_func()\n', mod1.read())

    def test_inlining_parameters(self):
        code = 'def f(p=1):\n    pass\nf()\n'
        result = self._inline(code, code.index('p'))
        self.assertEqual('def f(p=1):\n    pass\nf(1)\n', result)

    def test_inlining_function_with_line_breaks_in_args(self):
        code = 'def f(p): return p\nvar = f(1 +\n1)\n'
        refactored = self._inline(code, code.rindex('f'))
        self.assertEqual('var = 1 + 1\n', refactored)

    def test_inlining_variables_before_comparison(self):
        code = 'start = 1\nprint(start <= 2)\n'
        refactored = self._inline(code, code.index('start'))
        self.assertEqual('print(1 <= 2)\n', refactored)

    def test_inlining_variables_in_other_modules(self):
        self.mod.write('myvar = 1\n')
        self.mod2.write('import mod\nprint(mod.myvar)\n')
        self._inline2(self.mod, 2)
        self.assertEqual('import mod\nprint(1)\n', self.mod2.read())

    def test_inlining_variables_and_back_importing(self):
        self.mod.write('mainvar = 1\nmyvar = mainvar\n')
        self.mod2.write('import mod\nprint(mod.myvar)\n')
        self._inline2(self.mod, self.mod.read().index('myvar'))
        expected = 'import mod\n' \
                   'from mod import mainvar\n' \
                   'print(mainvar)\n'
        self.assertEqual(expected, self.mod2.read())

    def test_inlining_variables_and_importing_used_imports(self):
        self.mod.write('import sys\nmyvar = sys.argv\n')
        self.mod2.write('import mod\nprint(mod.myvar)\n')
        self._inline2(self.mod, self.mod.read().index('myvar'))
        expected = 'import mod\n' \
                   'import sys\n' \
                   'print(sys.argv)\n'
        self.assertEqual(expected, self.mod2.read())

    def test_inlining_variables_and_removing_old_froms(self):
        self.mod.write('var = 1\n')
        self.mod2.write('from mod import var\nprint(var)\n')
        self._inline2(self.mod2, self.mod2.read().rindex('var'))
        self.assertEqual('print(1)\n', self.mod2.read())

    def test_inlining_method_and_removing_old_froms(self):
        self.mod.write('def f():    return 1\n')
        self.mod2.write('from mod import f\nprint(f())\n')
        self._inline2(self.mod2, self.mod2.read().rindex('f'))
        self.assertEqual('print(1)\n', self.mod2.read())

    def test_inlining_functions_in_other_modules_and_only_current(self):
        code1 = 'def f():\n' \
                '    return 1\n' \
                'print(f())\n'
        code2 = 'import mod\n' \
                'print(mod.f())\n' \
                'print(mod.f())\n'
        self.mod.write(code1)
        self.mod2.write(code2)
        self._inline2(self.mod2, self.mod2.read().rindex('f'),
                      remove=False, only_current=True)
        expected2 = 'import mod\n' \
                    'print(mod.f())\n' \
                    'print(1)\n'
        self.assertEqual(code1, self.mod.read())
        self.assertEqual(expected2, self.mod2.read())

    def test_inlining_variables_in_other_modules_and_only_current(self):
        code1 = 'var = 1\n' \
                'print(var)\n'
        code2 = 'import mod\n' \
                'print(mod.var)\n' \
                'print(mod.var)\n'
        self.mod.write(code1)
        self.mod2.write(code2)
        self._inline2(self.mod2, self.mod2.read().rindex('var'),
                      remove=False, only_current=True)
        expected2 = 'import mod\n' \
                    'print(mod.var)\n' \
                    'print(1)\n'
        self.assertEqual(code1, self.mod.read())
        self.assertEqual(expected2, self.mod2.read())

    def test_inlining_does_not_change_string_constants(self):
        code = 'var = 1\n' \
               'print("var\\\n' \
               '")\n'
        expected = 'var = 1\n' \
                   'print("var\\\n' \
                   '")\n'
        refactored = self._inline(code, code.rindex('var'),
                                  remove=False, only_current=True, docs=False)
        self.assertEqual(expected, refactored)

    def test_inlining_does_change_string_constants_if_docs_is_set(self):
        code = 'var = 1\n' \
               'print("var\\\n' \
               '")\n'
        expected = 'var = 1\n' \
                   'print("1\\\n' \
                   '")\n'
        refactored = self._inline(code, code.rindex('var'),
                                  remove=False, only_current=True, docs=True)
        self.assertEqual(expected, refactored)


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(InlineTest))
    return result


if __name__ == '__main__':
    unittest.main()
