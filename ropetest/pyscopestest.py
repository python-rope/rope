try:
    import unittest2 as unittest
except ImportError:
    import unittest

from textwrap import dedent

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
        code = dedent("""\
            def sample_func():
                pass
        """)
        scope = libutils.get_string_scope(self.project, code)

        sample_func = scope["sample_func"].get_object()
        self.assertEqual(get_base_type("Function"), sample_func.get_type())

    def test_simple_function_scope(self):
        code = dedent("""\
            def sample_func():
                a = 10
        """)
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(1, len(scope.get_scopes()))
        sample_func_scope = scope.get_scopes()[0]
        self.assertEqual(1, len(sample_func_scope.get_names()))
        self.assertEqual(0, len(sample_func_scope.get_scopes()))

    def test_classes_inside_function_scopes(self):
        code = dedent("""\
            def sample_func():
                class SampleClass(object):
                    pass
        """)
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(1, len(scope.get_scopes()))
        sample_func_scope = scope.get_scopes()[0]  # noqa
        self.assertEqual(
            get_base_type("Type"),
            scope.get_scopes()[0]["SampleClass"].get_object().get_type(),
        )

    def test_list_comprehension_scope_inside_assignment(self):
        code = "a_var = [b_var + d_var for b_var, c_var in e_var]\n"
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(
            list(sorted(scope.get_defined_names())),
            ["a_var"],
        )
        self.assertEqual(
            list(sorted(scope.get_scopes()[0].get_defined_names())),
            ["b_var", "c_var"],
        )

    def test_list_comprehension_scope(self):
        code = "[b_var + d_var for b_var, c_var in e_var]\n"
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(
            list(sorted(scope.get_scopes()[0].get_defined_names())),
            ["b_var", "c_var"],
        )

    def test_set_comprehension_scope(self):
        code = "{b_var + d_var for b_var, c_var in e_var}\n"
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(
            list(sorted(scope.get_scopes()[0].get_defined_names())),
            ["b_var", "c_var"],
        )

    def test_generator_comprehension_scope(self):
        code = "(b_var + d_var for b_var, c_var in e_var)\n"
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(
            list(sorted(scope.get_scopes()[0].get_defined_names())),
            ["b_var", "c_var"],
        )

    def test_dict_comprehension_scope(self):
        code = "{b_var: d_var for b_var, c_var in e_var}\n"
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(
            list(sorted(scope.get_scopes()[0].get_defined_names())),
            ["b_var", "c_var"],
        )

    @testutils.only_for_versions_higher("3.8")
    def test_inline_assignment(self):
        code = """values = (a_var := 2,)"""
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(
            list(sorted(scope.get_defined_names())),
            ["a_var", "values"],
        )

    @testutils.only_for_versions_higher("3.8")
    def test_inline_assignment_in_comprehensions(self):
        code = dedent("""\
            [
                (a_var := b_var + (f_var := g_var))
                for b_var in [(j_var := i_var)
                for i_var in c_var] if a_var + (h_var := d_var)
            ]
        """)
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(
            list(sorted(scope.get_scopes()[0].get_defined_names())),
            ["a_var", "b_var", "f_var"],
        )
        self.assertEqual(
            list(sorted(scope.get_scopes()[0].get_scopes()[0].get_defined_names())),
            ["i_var", "j_var"],
        )

    def test_nested_comprehension(self):
        code = dedent("""\
            [
                b_var + d_var for b_var, c_var in [
                    e_var for e_var in f_var
                ]
            ]
        """)
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(
            list(sorted(scope.get_scopes()[0].get_defined_names())),
            ["b_var", "c_var"],
        )
        self.assertEqual(
            list(sorted(scope.get_scopes()[0].get_scopes()[0].get_defined_names())),
            ["e_var"],
        )

    def test_simple_class_scope(self):
        code = dedent("""\
            class SampleClass(object):
                def f(self):
                    var = 10
        """)
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(1, len(scope.get_scopes()))
        sample_class_scope = scope.get_scopes()[0]
        self.assertTrue("f" in sample_class_scope)
        self.assertEqual(1, len(sample_class_scope.get_scopes()))
        f_in_class = sample_class_scope.get_scopes()[0]
        self.assertTrue("var" in f_in_class)

    def test_get_lineno(self):
        code = dedent("""\

            def sample_func():
                a = 10
        """)
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(1, len(scope.get_scopes()))
        sample_func_scope = scope.get_scopes()[0]
        self.assertEqual(1, scope.get_start())
        self.assertEqual(2, sample_func_scope.get_start())

    def test_scope_kind(self):
        code = dedent("""\
            class SampleClass(object):
                pass
            def sample_func():
                pass
        """)
        scope = libutils.get_string_scope(self.project, code)

        sample_class_scope = scope.get_scopes()[0]
        sample_func_scope = scope.get_scopes()[1]
        self.assertEqual("Module", scope.get_kind())
        self.assertEqual("Class", sample_class_scope.get_kind())
        self.assertEqual("Function", sample_func_scope.get_kind())

    def test_function_parameters_in_scope_names(self):
        code = dedent("""\
            def sample_func(param):
                a = 10
        """)
        scope = libutils.get_string_scope(self.project, code)

        sample_func_scope = scope.get_scopes()[0]
        self.assertTrue("param" in sample_func_scope)

    def test_get_names_contains_only_names_defined_in_a_scope(self):
        code = dedent("""\
            var1 = 10
            def sample_func(param):
                var2 = 20
        """)
        scope = libutils.get_string_scope(self.project, code)

        sample_func_scope = scope.get_scopes()[0]
        self.assertTrue("var1" not in sample_func_scope)

    def test_scope_lookup(self):
        code = dedent("""\
            var1 = 10
            def sample_func(param):
                var2 = 20
        """)
        scope = libutils.get_string_scope(self.project, code)

        self.assertTrue(scope.lookup("var2") is None)
        self.assertEqual(
            get_base_type("Function"),
            scope.lookup("sample_func").get_object().get_type(),
        )
        sample_func_scope = scope.get_scopes()[0]
        self.assertTrue(sample_func_scope.lookup("var1") is not None)

    def test_function_scopes(self):
        code = dedent("""\
            def func():
                var = 10
        """)
        scope = libutils.get_string_scope(self.project, code)

        func_scope = scope.get_scopes()[0]
        self.assertTrue("var" in func_scope)

    def test_function_scopes_classes(self):
        code = dedent("""\
            def func():
                class Sample(object):
                    pass
        """)
        scope = libutils.get_string_scope(self.project, code)

        func_scope = scope.get_scopes()[0]
        self.assertTrue("Sample" in func_scope)

    def test_function_getting_scope(self):
        code = dedent("""\
            def func():    var = 10
        """)
        mod = libutils.get_string_module(self.project, code)

        func_scope = mod["func"].get_object().get_scope()
        self.assertTrue("var" in func_scope)

    def test_scopes_in_function_scopes(self):
        code = dedent("""\
            def func():
                def inner():
                    var = 10
        """)
        scope = libutils.get_string_scope(self.project, code)

        func_scope = scope.get_scopes()[0]
        inner_scope = func_scope.get_scopes()[0]
        self.assertTrue("var" in inner_scope)

    def test_for_variables_in_scopes(self):
        code = dedent("""\
            for a_var in range(10):
                pass
        """)
        scope = libutils.get_string_scope(self.project, code)

        self.assertTrue("a_var" in scope)

    def test_assists_inside_fors(self):
        code = dedent("""\
            for i in range(10):
                a_var = i
        """)
        scope = libutils.get_string_scope(self.project, code)

        self.assertTrue("a_var" in scope)

    def test_first_parameter_of_a_method(self):
        code = dedent("""\
            class AClass(object):
                def a_func(self, param):
                    pass
        """)
        a_class = libutils.get_string_module(self.project, code)["AClass"].get_object()
        function_scope = a_class["a_func"].get_object().get_scope()
        self.assertEqual(a_class, function_scope["self"].get_object().get_type())
        self.assertNotEqual(a_class, function_scope["param"].get_object().get_type())

    def test_first_parameter_of_static_methods(self):
        code = dedent("""\
            class AClass(object):
                @staticmethod
                def a_func(param):
                    pass
        """)
        a_class = libutils.get_string_module(self.project, code)["AClass"].get_object()
        function_scope = a_class["a_func"].get_object().get_scope()
        self.assertNotEqual(a_class, function_scope["param"].get_object().get_type())

    def test_first_parameter_of_class_methods(self):
        code = dedent("""\
            class AClass(object):
                @classmethod
                def a_func(cls):
                    pass
        """)
        a_class = libutils.get_string_module(self.project, code)["AClass"].get_object()
        function_scope = a_class["a_func"].get_object().get_scope()
        self.assertEqual(a_class, function_scope["cls"].get_object())

    def test_first_parameter_with_self_as_name_and_unknown_decorator(self):
        code = dedent("""\
            def my_decorator(func):
                return func
            class AClass(object):
                @my_decorator
                def a_func(self):
                    pass
        """)
        a_class = libutils.get_string_module(self.project, code)["AClass"].get_object()
        function_scope = a_class["a_func"].get_object().get_scope()
        self.assertEqual(a_class, function_scope["self"].get_object().get_type())

    def test_inside_class_scope_attribute_lookup(self):
        code = dedent("""\
            class C(object):
                an_attr = 1
                def a_func(self):
                    pass""")
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(1, len(scope.get_scopes()))
        c_scope = scope.get_scopes()[0]
        self.assertTrue("an_attr" in c_scope.get_names())
        self.assertTrue(c_scope.lookup("an_attr") is not None)
        f_in_c = c_scope.get_scopes()[0]
        self.assertTrue(f_in_c.lookup("an_attr") is None)

    def test_inside_class_scope_attribute_lookup2(self):
        code = dedent("""\
            class C(object):
                def __init__(self):
                    self.an_attr = 1
                def a_func(self):
                    pass""")
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(1, len(scope.get_scopes()))
        c_scope = scope.get_scopes()[0]
        f_in_c = c_scope.get_scopes()[0]
        self.assertTrue(f_in_c.lookup("an_attr") is None)

    def test_get_inner_scope_for_staticmethods(self):
        code = dedent("""\
            class C(object):
                @staticmethod
                def a_func(self):
                    pass
        """)
        scope = libutils.get_string_scope(self.project, code)

        c_scope = scope.get_scopes()[0]
        f_in_c = c_scope.get_scopes()[0]
        self.assertEqual(f_in_c, scope.get_inner_scope_for_line(4))

    def test_get_scope_for_offset_for_comprehension(self):
        code = "a = [i for i in range(10)]\n"
        scope = libutils.get_string_scope(self.project, code)

        c_scope = scope.get_scopes()[0]
        self.assertEqual(c_scope, scope.get_inner_scope_for_offset(10))
        self.assertEqual(scope, scope.get_inner_scope_for_offset(1))

    def test_get_scope_for_offset_for_in_nested_comprehension(self):
        code = "[i for i in [j for j in k]]\n"
        scope = libutils.get_string_scope(self.project, code)

        c_scope = scope.get_scopes()[0]
        self.assertEqual(c_scope, scope.get_inner_scope_for_offset(5))
        inner_scope = c_scope.get_scopes()[0]
        self.assertEqual(inner_scope, scope.get_inner_scope_for_offset(15))

    def test_get_scope_for_offset_for_scope_with_indent(self):
        code = dedent("""\
            def f(a):
                print(a)
        """)
        scope = libutils.get_string_scope(self.project, code)

        inner_scope = scope.get_scopes()[0]
        self.assertEqual(inner_scope, scope.get_inner_scope_for_offset(10))

    @testutils.only_for("3.5")
    def test_get_scope_for_offset_for_function_scope_and_async_with_statement(self):
        scope = libutils.get_string_scope(
            self.project,
            dedent("""\
                async def func():
                    async with a_func() as var:
                        print(var)
            """),
        )
        inner_scope = scope.get_scopes()[0]
        self.assertEqual(inner_scope, scope.get_inner_scope_for_offset(27))

    def test_getting_overwritten_scopes(self):
        code = dedent("""\
            def f():
                pass
            def f():
                pass
        """)
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(2, len(scope.get_scopes()))
        f1_scope = scope.get_scopes()[0]
        f2_scope = scope.get_scopes()[1]
        self.assertNotEqual(f1_scope, f2_scope)

    def test_assigning_builtin_names(self):
        code = "range = 1\n"
        mod = libutils.get_string_module(self.project, code)

        range = mod.get_scope().lookup("range")
        self.assertEqual((mod, 1), range.get_definition_location())

    def test_get_inner_scope_and_logical_lines(self):
        code = dedent('''\
            class C(object):
                def f():
                    s = """
            1
            2
            """
                    a = 1
        ''')
        scope = libutils.get_string_scope(self.project, code)

        c_scope = scope.get_scopes()[0]
        f_in_c = c_scope.get_scopes()[0]
        self.assertEqual(f_in_c, scope.get_inner_scope_for_line(7))

    def test_getting_defined_names_for_classes(self):
        code = dedent("""\
            class A(object):
                def a(self):
                    pass
            class B(A):
                def b(self):
                    pass
        """)
        scope = libutils.get_string_scope(self.project, code)

        a_scope = scope["A"].get_object().get_scope()  # noqa
        b_scope = scope["B"].get_object().get_scope()
        self.assertTrue("a" in b_scope.get_names())
        self.assertTrue("b" in b_scope.get_names())
        self.assertTrue("a" not in b_scope.get_defined_names())
        self.assertTrue("b" in b_scope.get_defined_names())

    def test_getting_defined_names_for_modules(self):
        code = dedent("""\
            class A(object):
                pass
        """)
        scope = libutils.get_string_scope(self.project, code)

        self.assertTrue("open" in scope.get_names())
        self.assertTrue("A" in scope.get_names())
        self.assertTrue("open" not in scope.get_defined_names())
        self.assertTrue("A" in scope.get_defined_names())

    def test_get_inner_scope_for_list_comprhension_with_many_targets(self):
        code = "a = [(i, j) for i,j in enumerate(range(10))]\n"
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(len(scope.get_scopes()), 1)
        self.assertNotIn("i", scope)
        self.assertNotIn("j", scope)
        self.assertIn("i", scope.get_scopes()[0])
        self.assertIn("j", scope.get_scopes()[0])

    def test_get_inner_scope_for_generator(self):
        code = "a = (i for i in range(10))\n"
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(len(scope.get_scopes()), 1)
        self.assertNotIn("i", scope)
        self.assertIn("i", scope.get_scopes()[0])

    def test_get_inner_scope_for_set_comprehension(self):
        code = "a = {i for i in range(10)}\n"
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(len(scope.get_scopes()), 1)
        self.assertNotIn("i", scope)
        self.assertIn("i", scope.get_scopes()[0])

    def test_get_inner_scope_for_dict_comprehension(self):
        code = "a = {i:i for i in range(10)}\n"
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(len(scope.get_scopes()), 1)
        self.assertNotIn("i", scope)
        self.assertIn("i", scope.get_scopes()[0])

    def test_get_inner_scope_for_nested_list_comprhension(self):
        code = "a = [[i + j for j in range(10)] for i in range(10)]\n"
        scope = libutils.get_string_scope(self.project, code)

        self.assertEqual(len(scope.get_scopes()), 1)
        self.assertNotIn("i", scope)
        self.assertNotIn("j", scope)
        self.assertIn("i", scope.get_scopes()[0])
        self.assertEqual(len(scope.get_scopes()[0].get_scopes()), 1)
        self.assertIn("j", scope.get_scopes()[0].get_scopes()[0])
        self.assertIn("i", scope.get_scopes()[0].get_scopes()[0])

    def test_get_scope_region(self):
        scope = libutils.get_string_scope(
            self.project,
            dedent("""
                def func1(ala):
                   pass

                def func2(o):
                   pass
            """),
        )

        self.assertEqual(scope.get_region(), (0, 48))
        self.assertEqual(scope.get_scopes()[0].get_region(), (1, 24))
        self.assertEqual(scope.get_scopes()[1].get_region(), (26, 47))

    def test_only_get_inner_scope_region(self):
        scope = libutils.get_string_scope(
            self.project,
            dedent("""
                def func1(ala):
                   pass

                def func2(o):
                   pass
            """),
        )

        self.assertEqual(scope.get_scopes()[1].get_region(), (26, 47))
