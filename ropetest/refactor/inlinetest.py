import unittest
from textwrap import dedent

import rope.base.exceptions
from rope.refactor import inline
from ropetest import testutils


class InlineTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, "mod")
        self.mod2 = testutils.create_module(self.project, "mod2")

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

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
        code = dedent("""\
            a_var = 10
            another_var = a_var
        """)
        refactored = self._inline(code, code.index("a_var") + 1)
        self.assertEqual("another_var = 10\n", refactored)

    def test_empty_case(self):
        code = "a_var = 10\n"
        refactored = self._inline(code, code.index("a_var") + 1)
        self.assertEqual("", refactored)

    def test_long_definition(self):
        code = dedent("""\
            a_var = 10 + (10 + 10)
            another_var = a_var
        """)
        refactored = self._inline(code, code.index("a_var") + 1)
        self.assertEqual("another_var = 10 + (10 + 10)\n", refactored)

    def test_explicit_continuation(self):
        code = dedent("""\
            a_var = (10 +
             10)
            another_var = a_var
        """)
        refactored = self._inline(code, code.index("a_var") + 1)
        self.assertEqual(
            dedent("""\
                another_var = (10 +
                 10)
            """),
            refactored,
        )

    def test_implicit_continuation(self):
        code = dedent("""\
            a_var = 10 +\\
                   10
            another_var = a_var
        """)
        refactored = self._inline(code, code.index("a_var") + 1)
        self.assertEqual(
            dedent("""\
                another_var = 10 +\\
                       10
            """),
            refactored,
        )

    def test_inlining_at_the_end_of_input(self):
        code = dedent("""\
            a = 1
            b = a""")
        refactored = self._inline(code, code.index("a") + 1)
        self.assertEqual("b = 1", refactored)

    def test_on_classes(self):
        code = dedent("""\
            class AClass(object):
                pass
        """)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline(code, code.index("AClass") + 1)

    def test_multiple_assignments(self):
        code = dedent("""\
            a_var = 10
            a_var = 20
        """)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline(code, code.index("a_var") + 1)

    def test_tuple_assignments(self):
        code = "a_var, another_var = (20, 30)\n"
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline(code, code.index("a_var") + 1)

    def test_on_unknown_vars(self):
        code = "a_var = another_var\n"
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline(code, code.index("another_var") + 1)

    def test_attribute_inlining(self):
        code = dedent("""\
            class A(object):
                def __init__(self):
                    self.an_attr = 3
                    range(self.an_attr)
        """)
        refactored = self._inline(code, code.index("an_attr") + 1)
        expected = dedent("""\
            class A(object):
                def __init__(self):
                    range(3)
        """)
        self.assertEqual(expected, refactored)

    def test_attribute_inlining2(self):
        code = dedent("""\
            class A(object):
                def __init__(self):
                    self.an_attr = 3
                    range(self.an_attr)
            a = A()
            range(a.an_attr)""")
        refactored = self._inline(code, code.index("an_attr") + 1)
        expected = dedent("""\
            class A(object):
                def __init__(self):
                    range(3)
            a = A()
            range(3)""")
        self.assertEqual(expected, refactored)

    def test_a_function_with_no_occurrence(self):
        self.mod.write(dedent("""\
            def a_func():
                pass
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("", self.mod.read())

    def test_a_function_with_no_occurrence2(self):
        self.mod.write(dedent("""\
            a_var = 10
            def a_func():
                pass
            print(a_var)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                a_var = 10
                print(a_var)
            """),
            self.mod.read(),
        )

    def test_replacing_calls_with_function_definition_in_other_modules(self):
        self.mod.write(dedent("""\
            def a_func():
                print(1)
        """))
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            import mod
            mod.a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                import mod
                print(1)
            """),
            mod1.read(),
        )

    def test_replacing_calls_with_function_definition_in_other_modules2(self):
        self.mod.write(dedent("""\
            def a_func():
                print(1)
        """))
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            import mod
            if True:
                mod.a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                import mod
                if True:
                    print(1)
            """),
            mod1.read(),
        )

    def test_replacing_calls_with_method_definition_in_other_modules(self):
        self.mod.write(dedent("""\
            class A(object):
                var = 10
                def a_func(self):
                    print(1)
        """))
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            import mod
            mod.A().a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                import mod
                print(1)
            """),
            mod1.read(),
        )
        self.assertEqual(
            dedent("""\
                class A(object):
                    var = 10
            """),
            self.mod.read(),
        )

    def test_replacing_calls_with_function_definition_in_defining_module(self):
        self.mod.write(dedent("""\
            def a_func():
                print(1)
            a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("print(1)\n", self.mod.read())

    def test_replac_calls_with_function_definition_in_defining_module2(self):
        self.mod.write(dedent("""\
            def a_func():
                for i in range(10):
                    print(1)
            a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                for i in range(10):
                    print(1)
            """),
            self.mod.read(),
        )

    def test_replacing_calls_with_method_definition_in_defining_modules(self):
        self.mod.write(dedent("""\
            class A(object):
                var = 10
                def a_func(self):
                    print(1)
            A().a_func()"""))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                class A(object):
                    var = 10
                print(1)
            """),
            self.mod.read(),
        )

    def test_parameters_with_the_same_name_as_passed(self):
        self.mod.write(dedent("""\
            def a_func(var):
                print(var)
            var = 1
            a_func(var)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                var = 1
                print(var)
            """),
            self.mod.read(),
        )

    def test_parameters_with_the_same_name_as_passed2(self):
        self.mod.write(dedent("""\
            def a_func(var):
                print(var)
            var = 1
            a_func(var=var)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                var = 1
                print(var)
            """),
            self.mod.read(),
        )

    def test_simple_parameters_renaming(self):
        self.mod.write(dedent("""\
            def a_func(param):
                print(param)
            var = 1
            a_func(var)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                var = 1
                print(var)
            """),
            self.mod.read(),
        )

    def test_simple_parameters_renaming_for_multiple_params(self):
        self.mod.write(dedent("""\
            def a_func(param1, param2):
                p = param1 + param2
            var1 = 1
            var2 = 1
            a_func(var1, var2)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                var1 = 1
                var2 = 1
                p = var1 + var2
            """),
            self.mod.read(),
        )

    def test_parameters_renaming_for_passed_constants(self):
        self.mod.write(dedent("""\
            def a_func(param):
                print(param)
            a_func(1)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("print(1)\n", self.mod.read())

    def test_parameters_renaming_for_passed_statements(self):
        self.mod.write(dedent("""\
            def a_func(param):
                print(param)
            a_func((1 + 2) / 3)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                print((1 + 2) / 3)
            """),
            self.mod.read(),
        )

    def test_simple_parameters_renam_for_multiple_params_using_keywords(self):
        self.mod.write(dedent("""\
            def a_func(param1, param2):
                p = param1 + param2
            var1 = 1
            var2 = 1
            a_func(param2=var1, param1=var2)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                var1 = 1
                var2 = 1
                p = var2 + var1
            """),
            self.mod.read(),
        )

    def test_simple_params_renam_for_multi_params_using_mixed_keywords(self):
        self.mod.write(dedent("""\
            def a_func(param1, param2):
                p = param1 + param2
            var1 = 1
            var2 = 1
            a_func(var2, param2=var1)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                var1 = 1
                var2 = 1
                p = var2 + var1
            """),
            self.mod.read(),
        )

    def test_simple_putting_in_default_arguments(self):
        self.mod.write(dedent("""\
            def a_func(param=None):
                print(param)
            a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("print(None)\n", self.mod.read())

    def test_overriding_default_arguments(self):
        self.mod.write(dedent("""\
            def a_func(param1=1, param2=2):
                print(param1, param2)
            a_func(param2=3)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("print(1, 3)\n", self.mod.read())

    def test_arguments_containing_comparisons(self):
        self.mod.write(dedent("""\
            def a_func(param1, param2, param3):
                param2.name
            a_func(2 <= 1, item, True)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("item.name\n", self.mod.read())

    def test_badly_formatted_text(self):
        self.mod.write(dedent("""\
            def a_func  (  param1 =  1 ,param2 = 2 )  :
                print(param1, param2)
            a_func  ( param2
                = 3 )
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("print(1, 3)\n", self.mod.read())

    def test_passing_first_arguments_for_methods(self):
        a_class = dedent("""\
            class A(object):
                def __init__(self):
                    self.var = 1
                    self.a_func(self.var)
                def a_func(self, param):
                    print(param)
        """)
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        expected = dedent("""\
            class A(object):
                def __init__(self):
                    self.var = 1
                    print(self.var)
        """)
        self.assertEqual(expected, self.mod.read())

    def test_passing_first_arguments_for_methods2(self):
        a_class = dedent("""\
            class A(object):
                def __init__(self):
                    self.var = 1
                def a_func(self, param):
                    print(param, self.var)
            an_a = A()
            an_a.a_func(1)
        """)
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        expected = dedent("""\
            class A(object):
                def __init__(self):
                    self.var = 1
            an_a = A()
            print(1, an_a.var)
        """)
        self.assertEqual(expected, self.mod.read())

    def test_passing_first_arguments_for_methods3(self):
        a_class = dedent("""\
            class A(object):
                def __init__(self):
                    self.var = 1
                def a_func(self, param):
                    print(param, self.var)
            an_a = A()
            A.a_func(an_a, 1)
        """)
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        expected = dedent("""\
            class A(object):
                def __init__(self):
                    self.var = 1
            an_a = A()
            print(1, an_a.var)
        """)
        self.assertEqual(expected, self.mod.read())

    def test_inlining_staticmethods(self):
        a_class = dedent("""\
            class A(object):
                @staticmethod
                def a_func(param):
                    print(param)
            A.a_func(1)
        """)
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        expected = dedent("""\
            class A(object):
                pass
            print(1)
        """)
        self.assertEqual(expected, self.mod.read())

    def test_static_methods2(self):
        a_class = dedent("""\
            class A(object):
                var = 10
                @staticmethod
                def a_func(param):
                    print(param)
            an_a = A()
            an_a.a_func(1)
            A.a_func(2)
        """)
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        expected = dedent("""\
            class A(object):
                var = 10
            an_a = A()
            print(1)
            print(2)
        """)
        self.assertEqual(expected, self.mod.read())

    def test_inlining_classmethods(self):
        a_class = dedent("""\
            class A(object):
                @classmethod
                def a_func(cls, param):
                    print(param)
            A.a_func(1)
        """)
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        expected = dedent("""\
            class A(object):
                pass
            print(1)
        """)
        self.assertEqual(expected, self.mod.read())

    def test_inlining_classmethods2(self):
        a_class = dedent("""\
            class A(object):
                @classmethod
                def a_func(cls, param):
                    return cls
            print(A.a_func(1))
        """)
        self.mod.write(a_class)
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        expected = dedent("""\
            class A(object):
                pass
            print(A)
        """)
        self.assertEqual(expected, self.mod.read())

    def test_simple_return_values_and_inlining_functions(self):
        self.mod.write(dedent("""\
            def a_func():
                return 1
            a = a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("a = 1\n", self.mod.read())

    def test_simple_return_values_and_inlining_lonely_functions(self):
        self.mod.write(dedent("""\
            def a_func():
                return 1
            a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("1\n", self.mod.read())

    def test_empty_returns_and_inlining_lonely_functions(self):
        self.mod.write(dedent("""\
            def a_func():
                if True:
                    return
            a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                if True:
                    pass
            """),
            self.mod.read(),
        )

    def test_multiple_returns(self):
        self.mod.write(dedent("""\
            def less_than_five(var):
                if var < 5:
                    return True
                return False
            a = less_than_five(2)
        """))
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline2(self.mod, self.mod.read().index("less") + 1)

    def test_multiple_returns_and_not_using_the_value(self):
        self.mod.write(dedent("""\
            def less_than_five(var):
                if var < 5:
                    return True
                return False
            less_than_five(2)
        """))
        self._inline2(self.mod, self.mod.read().index("less") + 1)
        self.assertEqual(
            dedent("""\
                if 2 < 5:
                    True
                False
            """),
            self.mod.read(),
        )

    def test_raising_exception_for_list_arguments(self):
        self.mod.write(dedent("""\
            def a_func(*args):
                print(args)
            a_func(1)
        """))
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline2(self.mod, self.mod.read().index("a_func") + 1)

    def test_raising_exception_for_list_keywods(self):
        self.mod.write(dedent("""\
            def a_func(**kwds):
                print(kwds)
            a_func(n=1)
        """))
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline2(self.mod, self.mod.read().index("a_func") + 1)

    def test_function_parameters_and_returns_in_other_functions(self):
        code = dedent("""\
            def a_func(param1, param2):
                return param1 + param2
            range(a_func(20, param2=abs(10)))
        """)
        self.mod.write(code)
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("range(20 + abs(10))\n", self.mod.read())

    def test_function_references_other_than_call(self):
        self.mod.write(dedent("""\
            def a_func(param):
                print(param)
            f = a_func
        """))
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline2(self.mod, self.mod.read().index("a_func") + 1)

    def test_function_referencing_itself(self):
        self.mod.write(dedent("""\
            def a_func(var):
                func = a_func
        """))
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline2(self.mod, self.mod.read().index("a_func") + 1)

    def test_recursive_functions(self):
        self.mod.write(dedent("""\
            def a_func(var):
                a_func(var)
        """))
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self._inline2(self.mod, self.mod.read().index("a_func") + 1)

    # TODO: inlining on function parameters
    def xxx_test_inlining_function_default_parameters(self):
        self.mod.write(dedent("""\
            def a_func(p1=1):
                pass
            a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("p1") + 1)
        self.assertEqual(
            dedent("""\
                def a_func(p1=1):
                    pass
                a_func()
            """),
            self.mod.read(),
        )

    def test_simple_inlining_after_extra_indented_lines(self):
        self.mod.write(dedent("""\
            def a_func():
                for i in range(10):
                    pass
            if True:
                pass
            a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                if True:
                    pass
                for i in range(10):
                    pass
            """),
            self.mod.read(),
        )

    def test_inlining_a_function_with_pydoc(self):
        self.mod.write(dedent('''\
            def a_func():
                """docs"""
                a = 1
            a_func()'''))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("a = 1\n", self.mod.read())

    def test_inlining_methods(self):
        self.mod.write(dedent("""\
            class A(object):
                name = 'hey'
                def get_name(self):
                    return self.name
            a = A()
            name = a.get_name()
        """))
        self._inline2(self.mod, self.mod.read().rindex("get_name") + 1)
        self.assertEqual(
            dedent("""\
                class A(object):
                    name = 'hey'
                a = A()
                name = a.name
            """),
            self.mod.read(),
        )

    def test_simple_returns_with_backslashes(self):
        self.mod.write(dedent("""\
            def a_func():
                return 1\\
                    + 2
            a = a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            "a = 1\\\n    + 2\n",
            dedent("""\
                a = 1\\
                    + 2
            """),
            self.mod.read(),
        )

    def test_a_function_with_pass_body(self):
        self.mod.write(dedent("""\
            def a_func():
                print(1)
            a = a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                print(1)
                a = None
            """),
            self.mod.read(),
        )

    def test_inlining_the_last_method_of_a_class(self):
        self.mod.write(dedent("""\
            class A(object):
                def a_func(self):
                    pass
        """))
        self._inline2(self.mod, self.mod.read().rindex("a_func") + 1)
        self.assertEqual(
            dedent("""\
                class A(object):
                    pass
            """),
            self.mod.read(),
        )

    def test_adding_needed_imports_in_the_dest_module(self):
        self.mod.write(dedent("""\
            import sys

            def ver():
                print(sys.version)
        """))
        self.mod2.write(dedent("""\
            import mod

            mod.ver()"""))
        self._inline2(self.mod, self.mod.read().index("ver") + 1)
        self.assertEqual(
            dedent("""\
                import mod
                import sys

                print(sys.version)
            """),
            self.mod2.read(),
        )

    def test_adding_needed_imports_in_the_dest_module_removing_selfs(self):
        self.mod.write(dedent("""\
            import mod2

            def f():
                print(mod2.var)
        """))
        self.mod2.write(dedent("""\
            import mod

            var = 1
            mod.f()
        """))
        self._inline2(self.mod, self.mod.read().index("f(") + 1)
        self.assertEqual(
            dedent("""\
                import mod

                var = 1
                print(var)
            """),
            self.mod2.read(),
        )

    def test_handling_relative_imports_when_inlining(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod3 = testutils.create_module(self.project, "mod3", pkg)
        mod4 = testutils.create_module(self.project, "mod4", pkg)
        mod4.write("var = 1\n")
        mod3.write(dedent("""\
            from . import mod4

            def f():
                print(mod4.var)
        """))
        self.mod.write(dedent("""\
            import pkg.mod3

            pkg.mod3.f()
        """))
        self._inline2(self.mod, self.mod.read().index("f(") + 1)
        # Cannot determine the exact import
        self.assertTrue("\n\nprint(mod4.var)\n" in self.mod.read())

    def test_adding_needed_imports_for_elements_in_source(self):
        self.mod.write(dedent("""\
            def f1():
                return f2()
            def f2():
                return 1
        """))
        self.mod2.write(dedent("""\
            import mod

            print(mod.f1())
        """))
        self._inline2(self.mod, self.mod.read().index("f1") + 1)
        self.assertEqual(
            dedent("""\
                import mod
                from mod import f2

                print(f2())
            """),
            self.mod2.read(),
        )

    def test_relative_imports_and_changing_inlining_body(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod3 = testutils.create_module(self.project, "mod3", pkg)
        mod4 = testutils.create_module(self.project, "mod4", pkg)
        mod4.write("var = 1\n")
        mod3.write(dedent("""\
            import mod4

            def f():
                print(mod4.var)
        """))
        self.mod.write(dedent("""\
            import pkg.mod3

            pkg.mod3.f()
        """))
        self._inline2(self.mod, self.mod.read().index("f(") + 1)
        self.assertEqual(
            dedent("""\
                import pkg.mod3
                import pkg.mod4

                print(pkg.mod4.var)
            """),
            self.mod.read(),
        )

    def test_inlining_with_different_returns(self):
        self.mod.write(dedent("""\
            def f(p):
                return p
            print(f(1))
            print(f(2))
            print(f(1))
        """))
        self._inline2(self.mod, self.mod.read().index("f(") + 1)
        self.assertEqual(
            dedent("""\
                print(1)
                print(2)
                print(1)
            """),
            self.mod.read(),
        )

    def test_not_removing_definition_for_variables(self):
        code = dedent("""\
            a_var = 10
            another_var = a_var
        """)
        refactored = self._inline(code, code.index("a_var") + 1, remove=False)
        self.assertEqual(
            dedent("""\
                a_var = 10
                another_var = 10
            """),
            refactored,
        )

    def test_not_removing_definition_for_methods(self):
        code = dedent("""\
            def func():
                print(1)

            func()
        """)
        refactored = self._inline(code, code.index("func") + 1, remove=False)
        self.assertEqual(
            dedent("""\
                def func():
                    print(1)

                print(1)
            """),
            refactored,
        )

    def test_only_current_for_methods(self):
        code = dedent("""\
            def func():
                print(1)

            func()
            func()
        """)
        refactored = self._inline(
            code, code.rindex("func") + 1, remove=False, only_current=True
        )
        self.assertEqual(
            dedent("""\
                def func():
                    print(1)

                func()
                print(1)
            """),
            refactored,
        )

    def test_only_current_for_variables(self):
        code = dedent("""\
            one = 1

            a = one
            b = one
        """)
        refactored = self._inline(
            code, code.rindex("one") + 1, remove=False, only_current=True
        )
        self.assertEqual(
            dedent("""\
                one = 1

                a = one
                b = 1
            """),
            refactored,
        )

    def test_inlining_one_line_functions(self):
        code = dedent("""\
            def f(): return 1
            var = f()
        """)
        refactored = self._inline(code, code.rindex("f"))
        self.assertEqual("var = 1\n", refactored)

    def test_inlining_one_line_functions_with_breaks(self):
        code = dedent("""\
            def f(
            p): return p
            var = f(1)
        """)
        refactored = self._inline(code, code.rindex("f"))
        self.assertEqual("var = 1\n", refactored)

    def test_inlining_one_line_functions_with_breaks2(self):
        code = dedent("""\
            def f(
            ): return 1
            var = f()
        """)
        refactored = self._inline(code, code.rindex("f"))
        self.assertEqual("var = 1\n", refactored)

    def test_resources_parameter(self):
        self.mod.write(dedent("""\
            def a_func():
                print(1)
        """))
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            import mod
            mod.a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func"), resources=[self.mod])
        self.assertEqual("", self.mod.read())
        self.assertEqual(
            dedent("""\
                import mod
                mod.a_func()
            """),
            mod1.read(),
        )

    def test_inlining_parameters(self):
        code = dedent("""\
            def f(p=1):
                pass
            f()
        """)
        result = self._inline(code, code.index("p"))
        self.assertEqual(
            dedent("""\
                def f(p=1):
                    pass
                f(1)
            """),
            result,
        )

    def test_inlining_function_with_line_breaks_in_args(self):
        code = dedent("""\
            def f(p): return p
            var = f(1 +
            1)
        """)
        refactored = self._inline(code, code.rindex("f"))
        self.assertEqual("var = 1 + 1\n", refactored)

    def test_inlining_variables_before_comparison(self):
        code = "start = 1\nprint(start <= 2)\n"
        refactored = self._inline(code, code.index("start"))
        self.assertEqual("print(1 <= 2)\n", refactored)

    def test_inlining_variables_in_other_modules(self):
        self.mod.write("myvar = 1\n")
        self.mod2.write(dedent("""\
            import mod
            print(mod.myvar)
        """))
        self._inline2(self.mod, 2)
        self.assertEqual(
            dedent("""\
                import mod
                print(1)
            """),
            self.mod2.read(),
        )

    def test_inlining_variables_and_back_importing(self):
        self.mod.write(dedent("""\
            mainvar = 1
            myvar = mainvar
        """))
        self.mod2.write(dedent("""\
            import mod
            print(mod.myvar)
        """))
        self._inline2(self.mod, self.mod.read().index("myvar"))
        expected = dedent("""\
            import mod
            from mod import mainvar
            print(mainvar)
        """)
        self.assertEqual(expected, self.mod2.read())

    def test_inlining_variables_and_importing_used_imports(self):
        self.mod.write(dedent("""\
            import sys
            myvar = sys.argv
        """))
        self.mod2.write(dedent("""\
            import mod
            print(mod.myvar)
        """))
        self._inline2(self.mod, self.mod.read().index("myvar"))
        expected = dedent("""\
            import mod
            import sys
            print(sys.argv)
        """)
        self.assertEqual(expected, self.mod2.read())

    def test_inlining_variables_and_removing_old_froms(self):
        self.mod.write("var = 1\n")
        self.mod2.write(dedent("""\
            from mod import var
            print(var)
        """))
        self._inline2(self.mod2, self.mod2.read().rindex("var"))
        self.assertEqual("print(1)\n", self.mod2.read())

    def test_inlining_method_and_removing_old_froms(self):
        self.mod.write(dedent("""\
            def f():    return 1
        """))
        self.mod2.write(dedent("""\
            from mod import f
            print(f())
        """))
        self._inline2(self.mod2, self.mod2.read().rindex("f"))
        self.assertEqual("print(1)\n", self.mod2.read())

    def test_inlining_functions_in_other_modules_and_only_current(self):
        code1 = dedent("""\
            def f():
                return 1
            print(f())
        """)
        code2 = dedent("""\
            import mod
            print(mod.f())
            print(mod.f())
        """)
        self.mod.write(code1)
        self.mod2.write(code2)
        self._inline2(
            self.mod2, self.mod2.read().rindex("f"), remove=False, only_current=True
        )
        expected2 = dedent("""\
            import mod
            print(mod.f())
            print(1)
        """)
        self.assertEqual(code1, self.mod.read())
        self.assertEqual(expected2, self.mod2.read())

    def test_inlining_variables_in_other_modules_and_only_current(self):
        code1 = dedent("""\
            var = 1
            print(var)
        """)
        code2 = dedent("""\
            import mod
            print(mod.var)
            print(mod.var)
        """)
        self.mod.write(code1)
        self.mod2.write(code2)
        self._inline2(
            self.mod2, self.mod2.read().rindex("var"), remove=False, only_current=True
        )
        expected2 = "import mod\n" "print(mod.var)\n" "print(1)\n"
        self.assertEqual(code1, self.mod.read())
        self.assertEqual(expected2, self.mod2.read())

    def test_inlining_does_not_change_string_constants(self):
        code = dedent("""\
            var = 1
            print("var\\
            ")
        """)
        expected = dedent("""\
            var = 1
            print("var\\
            ")
        """)
        refactored = self._inline(
            code, code.rindex("var"), remove=False, only_current=True, docs=False
        )
        self.assertEqual(expected, refactored)

    def test_inlining_does_change_string_constants_if_docs_is_set(self):
        code = dedent("""\
            var = 1
            print("var\\
            ")
        """)
        expected = dedent("""\
            var = 1
            print("1\\
            ")
        """)
        refactored = self._inline(
            code, code.rindex("var"), remove=False, only_current=True, docs=True
        )
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.6")
    def test_inlining_into_format_string(self):
        code = dedent("""\
            var = 123
            print(f"{var}")
        """)
        expected = dedent("""\
            print(f"{123}")
        """)

        refactored = self._inline(code, code.rindex("var"))

        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.6")
    def test_inlining_into_format_string_containing_quotes(self):
        code = dedent('''\
            var = 123
            print(f" '{var}' ")
            print(f""" "{var}" """)
            print(f' "{var}" ')
        ''')
        expected = dedent('''\
            print(f" '{123}' ")
            print(f""" "{123}" """)
            print(f' "{123}" ')
        ''')

        refactored = self._inline(code, code.rindex("var"))

        self.assertEqual(expected, refactored)

    def test_parameters_with_the_same_name_as_passed_with_type_hints(self):
        self.mod.write(dedent("""\
            def a_func(var: int):
                print(var)
            var = 1
            a_func(var)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                var = 1
                print(var)
            """),
            self.mod.read(),
        )

    def test_parameters_with_the_same_name_as_passed_as_kwargs_with_type_hints(self):
        self.mod.write(dedent("""\
            def a_func(var: int):
                print(var)
            var = 1
            a_func(var=var)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                var = 1
                print(var)
            """),
            self.mod.read(),
        )

    def test_simple_parameters_renaming_with_type_hints(self):
        self.mod.write(dedent("""\
            def a_func(param: int):
                print(param)
            var = 1
            a_func(var)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                var = 1
                print(var)
            """),
            self.mod.read(),
        )

    def test_simple_parameters_renaming_for_multiple_params_with_type_hints(self):
        self.mod.write(dedent("""\
            def a_func(param1, param2: int):
                p = param1 + param2
            var1 = 1
            var2 = 1
            a_func(var1, var2)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                var1 = 1
                var2 = 1
                p = var1 + var2
            """),
            self.mod.read(),
        )

    def test_parameters_renaming_for_passed_constants_with_type_hints(self):
        self.mod.write(dedent("""\
            def a_func(param: int):
                print(param)
            a_func(1)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("print(1)\n", self.mod.read())

    def test_parameters_renaming_for_passed_statements_with_type_hints(self):
        self.mod.write(dedent("""\
            def a_func(param: int):
                print(param)
            a_func((1 + 2) / 3)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                print((1 + 2) / 3)
            """),
            self.mod.read(),
        )

    def test_simple_parameters_renaming_for_multiple_params_using_keywords_with_type_hints(
        self,
    ):
        self.mod.write(dedent("""\
            def a_func(param1, param2: int):
                p = param1 + param2
            var1 = 1
            var2 = 1
            a_func(param2=var1, param1=var2)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                var1 = 1
                var2 = 1
                p = var2 + var1
            """),
            self.mod.read(),
        )

    def test_simple_params_renaming_for_multi_params_using_mixed_keywords_with_type_hints(
        self,
    ):
        self.mod.write(dedent("""\
            def a_func(param1, param2: int):
                p = param1 + param2
            var1 = 1
            var2 = 1
            a_func(var2, param2=var1)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual(
            dedent("""\
                var1 = 1
                var2 = 1
                p = var2 + var1
            """),
            self.mod.read(),
        )

    def test_simple_putting_in_default_arguments_with_type_hints(self):
        self.mod.write(dedent("""\
            def a_func(param: Optional[int] = None):
                print(param)
            a_func()
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("print(None)\n", self.mod.read())

    def test_overriding_default_arguments_with_type_hints(self):
        self.mod.write(dedent("""\
            def a_func(param1=1, param2: int = 2):
                print(param1, param2)
            a_func(param2=3)
        """))
        self._inline2(self.mod, self.mod.read().index("a_func") + 1)
        self.assertEqual("print(1, 3)\n", self.mod.read())

    def test_dictionary_with_inline_comment(self):
        code = dedent("""\
            myvar = {
                "key": "value",  # noqa
            }
            print(myvar)
        """)
        refactored = self._inline(code, code.index("myvar") + 1)
        expected = dedent("""\
            print({
                "key": "value",  # noqa
            })
        """)
        self.assertEqual(expected, refactored)

    def test_function_call_with_callsite_inline_comment(self):
        code = dedent("""\
            def a_func(arg1, arg2):
                return arg1 + arg2 + 1
            myvar = a_func(
                1,  # some comment
                2,  # another comment
            )
        """)
        refactored = self._inline(code, code.index("a_func") + 1)
        expected = dedent("""\
            myvar = 1 + 2 + 1
        """)
        self.assertEqual(expected, refactored)

    def test_function_call_with_callsite_interline_comment(self):
        code = dedent("""\
            def a_func(arg1, arg2):
                return arg1 + arg2 + 1
            myvar = a_func(
                # some comment
                1,
                # another comment
                2,
                # another comment
            )
        """)
        refactored = self._inline(code, code.index("a_func") + 1)
        expected = dedent("""\
            myvar = 1 + 2 + 1
        """)
        self.assertEqual(expected, refactored)

    def test_function_call_with_defsite_inline_comment(self):
        code = dedent("""\
            def a_func(
                arg1,   # noqa
                arg2,
            ):
                return arg1 + arg2 + 1
            myvar = a_func(1, 2)
        """)
        refactored = self._inline(code, code.index("a_func") + 1)
        expected = dedent("""\
            myvar = 1 + 2 + 1
        """)
        self.assertEqual(expected, refactored)

    def test_function_call_with_defsite_interline_comment(self):
        code = dedent("""\
            def a_func(
                # blah
                arg1,
                # blah blah
                arg2,
                # blah blah
            ):
                return arg1 + arg2 + 1
            myvar = a_func(1, 2)
        """)
        refactored = self._inline(code, code.index("a_func") + 1)
        expected = dedent("""\
            myvar = 1 + 2 + 1
        """)
        self.assertEqual(expected, refactored)

    def test_function_call_with_posonlyargs(self):
        code = dedent("""\
            def a_func(arg1, /, arg2):
                return arg1 + arg2 + 1
            myvar = a_func(1, 2)
        """)
        refactored = self._inline(code, code.index("a_func") + 1)
        expected = dedent("""\
            myvar = 1 + 2 + 1
        """)
        self.assertEqual(expected, refactored)

    def test_function_call_with_kwonlyargs(self):
        code = dedent("""\
            def a_func(arg1, *, arg2):
                return arg1 + arg2 + 1
            myvar = a_func(1, arg2=2)
        """)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            refactored = self._inline(code, code.index("a_func") + 1)

    def test_function_call_with_kwonlyargs2(self):
        code = dedent("""\
            def a_func(arg1, *, arg2=2):
                return arg1 + arg2 + 1
            myvar = a_func(1)
        """)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            refactored = self._inline(code, code.index("a_func") + 1)
