try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rope.base import libutils
from rope.base.pyobjects import get_base_type
from ropetest import testutils


class PyCoreScopesTest(unittest.TestCase):

    def setUp(self):
        super(PyCoreScopesTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore

    def tearDown(self):
        testutils.remove_project(self.project)
        super(PyCoreScopesTest, self).tearDown()

    def test_simple_scope(self):
        scope = libutils.get_string_scope(
            self.project, 'def sample_func():\n    pass\n')
        sample_func = scope['sample_func'].get_object()
        self.assertEqual(get_base_type('Function'), sample_func.get_type())

    def test_simple_function_scope(self):
        scope = libutils.get_string_scope(
            self.project, 'def sample_func():\n    a = 10\n')
        self.assertEqual(1, len(scope.get_scopes()))
        sample_func_scope = scope.get_scopes()[0]
        self.assertEqual(1, len(sample_func_scope.get_names()))
        self.assertEqual(0, len(sample_func_scope.get_scopes()))

    def test_classes_inside_function_scopes(self):
        scope = libutils.get_string_scope(
            self.project,
            'def sample_func():\n'
            '    class SampleClass(object):\n        pass\n')
        self.assertEqual(1, len(scope.get_scopes()))
        sample_func_scope = scope.get_scopes()[0]  # noqa
        self.assertEqual(get_base_type('Type'),
                          scope.get_scopes()[0]['SampleClass'].
                          get_object().get_type())

    def test_list_comprehension_scope_inside_assignment(self):
        scope = libutils.get_string_scope(
            self.project, 'a_var = [b_var + d_var for b_var, c_var in e_var]\n')
        self.assertEqual(
            list(sorted(scope.get_defined_names())),
            ['a_var', 'b_var', 'c_var'],
        )

    def test_list_comprehension_scope(self):
        scope = libutils.get_string_scope(
            self.project, '[b_var + d_var for b_var, c_var in e_var]\n')
        self.assertEqual(
            list(sorted(scope.get_defined_names())),
            ['b_var', 'c_var'],
        )

    def test_set_comprehension_scope(self):
        scope = libutils.get_string_scope(
            self.project, '{b_var + d_var for b_var, c_var in e_var}\n')
        self.assertEqual(
            list(sorted(scope.get_defined_names())),
            ['b_var', 'c_var'],
        )

    def test_generator_comprehension_scope(self):
        scope = libutils.get_string_scope(
            self.project, '(b_var + d_var for b_var, c_var in e_var)\n')
        self.assertEqual(
            list(sorted(scope.get_defined_names())),
            ['b_var', 'c_var'],
        )

    def test_dict_comprehension_scope(self):
        scope = libutils.get_string_scope(
            self.project, '{b_var: d_var for b_var, c_var in e_var}\n')
        self.assertEqual(
            list(sorted(scope.get_defined_names())),
            ['b_var', 'c_var'],
        )

    @testutils.only_for_versions_higher('3.8')
    def test_inline_assignment_in_comprehensions(self):
        scope = libutils.get_string_scope(
            self.project, '''[
                (a_var := b_var + (f_var := g_var))
                for b_var in [(j_var := i_var)
                for i_var in c_var] if a_var + (h_var := d_var)
            ]''')
        self.assertEqual(
            list(sorted(scope.get_defined_names())),
            ['a_var', 'b_var', 'f_var', 'h_var', 'i_var', 'j_var'],
        )

    def test_nested_comprehension(self):
        scope = libutils.get_string_scope(
            self.project, '''[
                b_var + d_var for b_var, c_var in [
                    e_var for e_var in f_var
                ]
            ]\n''')
        self.assertEqual(
            list(sorted(scope.get_defined_names())),
            ['b_var', 'c_var', 'e_var'],
        )

    def test_simple_class_scope(self):
        scope = libutils.get_string_scope(
            self.project,
            'class SampleClass(object):\n'
            '    def f(self):\n        var = 10\n')
        self.assertEqual(1, len(scope.get_scopes()))
        sample_class_scope = scope.get_scopes()[0]
        self.assertTrue('f' in sample_class_scope)
        self.assertEqual(1, len(sample_class_scope.get_scopes()))
        f_in_class = sample_class_scope.get_scopes()[0]
        self.assertTrue('var' in f_in_class)

    def test_get_lineno(self):
        scope = libutils.get_string_scope(
            self.project, '\ndef sample_func():\n    a = 10\n')
        self.assertEqual(1, len(scope.get_scopes()))
        sample_func_scope = scope.get_scopes()[0]
        self.assertEqual(1, scope.get_start())
        self.assertEqual(2, sample_func_scope.get_start())

    def test_scope_kind(self):
        scope = libutils.get_string_scope(
            self.project,
            'class SampleClass(object):\n    pass\n'
            'def sample_func():\n    pass\n')
        sample_class_scope = scope.get_scopes()[0]
        sample_func_scope = scope.get_scopes()[1]
        self.assertEqual('Module', scope.get_kind())
        self.assertEqual('Class', sample_class_scope.get_kind())
        self.assertEqual('Function', sample_func_scope.get_kind())

    def test_function_parameters_in_scope_names(self):
        scope = libutils.get_string_scope(
            self.project, 'def sample_func(param):\n    a = 10\n')
        sample_func_scope = scope.get_scopes()[0]
        self.assertTrue('param' in sample_func_scope)

    def test_get_names_contains_only_names_defined_in_a_scope(self):
        scope = libutils.get_string_scope(
            self.project,
            'var1 = 10\ndef sample_func(param):\n    var2 = 20\n')
        sample_func_scope = scope.get_scopes()[0]
        self.assertTrue('var1' not in sample_func_scope)

    def test_scope_lookup(self):
        scope = libutils.get_string_scope(
            self.project,
            'var1 = 10\ndef sample_func(param):\n    var2 = 20\n')
        self.assertTrue(scope.lookup('var2') is None)
        self.assertEqual(get_base_type('Function'),
                          scope.lookup('sample_func').get_object().get_type())
        sample_func_scope = scope.get_scopes()[0]
        self.assertTrue(sample_func_scope.lookup('var1') is not None)

    def test_function_scopes(self):
        scope = libutils.get_string_scope(
            self.project, 'def func():\n    var = 10\n')
        func_scope = scope.get_scopes()[0]
        self.assertTrue('var' in func_scope)

    def test_function_scopes_classes(self):
        scope = libutils.get_string_scope(
            self.project,
            'def func():\n    class Sample(object):\n        pass\n')
        func_scope = scope.get_scopes()[0]
        self.assertTrue('Sample' in func_scope)

    def test_function_getting_scope(self):
        mod = libutils.get_string_module(
            self.project, 'def func():    var = 10\n')
        func_scope = mod['func'].get_object().get_scope()
        self.assertTrue('var' in func_scope)

    def test_scopes_in_function_scopes(self):
        scope = libutils.get_string_scope(
            self.project,
            'def func():\n    def inner():\n        var = 10\n')
        func_scope = scope.get_scopes()[0]
        inner_scope = func_scope.get_scopes()[0]
        self.assertTrue('var' in inner_scope)

    def test_for_variables_in_scopes(self):
        scope = libutils.get_string_scope(
            self.project, 'for a_var in range(10):\n    pass\n')
        self.assertTrue('a_var' in scope)

    def test_assists_inside_fors(self):
        scope = libutils.get_string_scope(
            self.project, 'for i in range(10):\n    a_var = i\n')
        self.assertTrue('a_var' in scope)

    def test_first_parameter_of_a_method(self):
        code = 'class AClass(object):\n' \
               '    def a_func(self, param):\n        pass\n'
        a_class = libutils.get_string_module(self.project, code)['AClass'].\
            get_object()
        function_scope = a_class['a_func'].get_object().get_scope()
        self.assertEqual(a_class,
                          function_scope['self'].get_object().get_type())
        self.assertNotEqual(a_class, function_scope['param'].
                             get_object().get_type())

    def test_first_parameter_of_static_methods(self):
        code = 'class AClass(object):\n' \
               '    @staticmethod\n    def a_func(param):\n        pass\n'
        a_class = libutils.get_string_module(self.project, code)['AClass'].\
            get_object()
        function_scope = a_class['a_func'].\
            get_object().get_scope()
        self.assertNotEqual(a_class,
                             function_scope['param'].get_object().get_type())

    def test_first_parameter_of_class_methods(self):
        code = 'class AClass(object):\n' \
            '    @classmethod\n    def a_func(cls):\n        pass\n'
        a_class = libutils.get_string_module(self.project, code)['AClass'].\
            get_object()
        function_scope = a_class['a_func'].get_object().get_scope()
        self.assertEqual(a_class, function_scope['cls'].get_object())

    def test_first_parameter_with_self_as_name_and_unknown_decorator(self):
        code = 'def my_decorator(func):\n    return func\n'\
               'class AClass(object):\n' \
               '    @my_decorator\n    def a_func(self):\n        pass\n'
        a_class = libutils.get_string_module(self.project, code)['AClass'].\
            get_object()
        function_scope = a_class['a_func'].get_object().get_scope()
        self.assertEqual(a_class, function_scope['self'].
                          get_object().get_type())

    def test_inside_class_scope_attribute_lookup(self):
        scope = libutils.get_string_scope(
            self.project,
            'class C(object):\n'
            '    an_attr = 1\n'
            '    def a_func(self):\n        pass')
        self.assertEqual(1, len(scope.get_scopes()))
        c_scope = scope.get_scopes()[0]
        self.assertTrue('an_attr'in c_scope.get_names())
        self.assertTrue(c_scope.lookup('an_attr') is not None)
        f_in_c = c_scope.get_scopes()[0]
        self.assertTrue(f_in_c.lookup('an_attr') is None)

    def test_inside_class_scope_attribute_lookup2(self):
        scope = libutils.get_string_scope(
            self.project,
            'class C(object):\n'
            '    def __init__(self):\n        self.an_attr = 1\n'
            '    def a_func(self):\n        pass')
        self.assertEqual(1, len(scope.get_scopes()))
        c_scope = scope.get_scopes()[0]
        f_in_c = c_scope.get_scopes()[0]
        self.assertTrue(f_in_c.lookup('an_attr') is None)

    def test_get_inner_scope_for_staticmethods(self):
        scope = libutils.get_string_scope(
            self.project,
            'class C(object):\n'
            '    @staticmethod\n'
            '    def a_func(self):\n        pass\n')
        c_scope = scope.get_scopes()[0]
        f_in_c = c_scope.get_scopes()[0]
        self.assertEqual(f_in_c, scope.get_inner_scope_for_line(4))

    def test_getting_overwritten_scopes(self):
        scope = libutils.get_string_scope(
            self.project, 'def f():\n    pass\ndef f():\n    pass\n')
        self.assertEqual(2, len(scope.get_scopes()))
        f1_scope = scope.get_scopes()[0]
        f2_scope = scope.get_scopes()[1]
        self.assertNotEqual(f1_scope, f2_scope)

    def test_assigning_builtin_names(self):
        mod = libutils.get_string_module(self.project, 'range = 1\n')
        range = mod.get_scope().lookup('range')
        self.assertEqual((mod, 1), range.get_definition_location())

    def test_get_inner_scope_and_logical_lines(self):
        scope = libutils.get_string_scope(
            self.project,
            'class C(object):\n'
            '    def f():\n        s = """\n1\n2\n"""\n        a = 1\n')
        c_scope = scope.get_scopes()[0]
        f_in_c = c_scope.get_scopes()[0]
        self.assertEqual(f_in_c, scope.get_inner_scope_for_line(7))

    def test_getting_defined_names_for_classes(self):
        scope = libutils.get_string_scope(
            self.project,
            'class A(object):\n    def a(self):\n        pass\n'
            'class B(A):\n    def b(self):\n        pass\n')
        a_scope = scope['A'].get_object().get_scope()  # noqa
        b_scope = scope['B'].get_object().get_scope()
        self.assertTrue('a' in b_scope.get_names())
        self.assertTrue('b' in b_scope.get_names())
        self.assertTrue('a' not in b_scope.get_defined_names())
        self.assertTrue('b' in b_scope.get_defined_names())

    def test_getting_defined_names_for_modules(self):
        scope = libutils.get_string_scope(
            self.project, 'class A(object):\n    pass\n')
        self.assertTrue('open' in scope.get_names())
        self.assertTrue('A' in scope.get_names())
        self.assertTrue('open' not in scope.get_defined_names())
        self.assertTrue('A' in scope.get_defined_names())


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(PyCoreScopesTest))
    return result


if __name__ == '__main__':
    unittest.main()
