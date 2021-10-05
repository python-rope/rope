from textwrap import dedent

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rope.base import exceptions
from ropetest import testutils
from rope.refactor.usefunction import UseFunction


class UseFunctionTest(unittest.TestCase):
    def setUp(self):
        super(UseFunctionTest, self).setUp()
        self.project = testutils.sample_project()
        self.mod1 = testutils.create_module(self.project, "mod1")
        self.mod2 = testutils.create_module(self.project, "mod2")

    def tearDown(self):
        testutils.remove_project(self.project)
        super(UseFunctionTest, self).tearDown()

    def test_simple_case(self):
        code = dedent("""\
            def f():
                pass
        """)
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex("f"))
        self.project.do(user.get_changes())
        self.assertEqual(code, self.mod1.read())

    def test_simple_function(self):
        code = dedent("""\
            def f(p):
                print(p)
            print(1)
        """)
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex("f"))
        self.project.do(user.get_changes())
        self.assertEqual(
            dedent("""\
                def f(p):
                    print(p)
                f(1)
            """),
            self.mod1.read(),
        )

    def test_simple_function2(self):
        code = dedent("""\
            def f(p):
                print(p + 1)
            print(1 + 1)
        """)
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex("f"))
        self.project.do(user.get_changes())
        self.assertEqual(
            dedent("""\
                def f(p):
                    print(p + 1)
                f(1)
            """),
            self.mod1.read(),
        )

    def test_functions_with_multiple_statements(self):
        code = dedent("""\
            def f(p):
                r = p + 1
                print(r)
            r = 2 + 1
            print(r)
        """)
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex("f"))
        self.project.do(user.get_changes())
        self.assertEqual(
            dedent("""\
                def f(p):
                    r = p + 1
                    print(r)
                f(2)
            """),
            self.mod1.read(),
        )

    def test_returning(self):
        code = dedent("""\
            def f(p):
                return p + 1
            r = 2 + 1
            print(r)
        """)
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex("f"))
        self.project.do(user.get_changes())
        self.assertEqual(
            dedent("""\
                def f(p):
                    return p + 1
                r = f(2)
                print(r)
            """),
            self.mod1.read(),
        )

    def test_returning_a_single_expression(self):
        code = dedent("""\
            def f(p):
                return p + 1
            print(2 + 1)
        """)
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex("f"))
        self.project.do(user.get_changes())
        self.assertEqual(
            dedent("""\
                def f(p):
                    return p + 1
                print(f(2))
            """),
            self.mod1.read(),
        )

    def test_occurrences_in_other_modules(self):
        code = dedent("""\
            def f(p):
                return p + 1
        """)
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex("f"))
        self.mod2.write("print(2 + 1)\n")
        self.project.do(user.get_changes())
        self.assertEqual(
            dedent("""\
                import mod1
                print(mod1.f(2))
            """),
            self.mod2.read(),
        )

    def test_when_performing_on_non_functions(self):
        code = "var = 1\n"
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            UseFunction(self.project, self.mod1, code.rindex("var"))

    def test_differing_in_the_inner_temp_names(self):
        code = dedent("""\
            def f(p):
                a = p + 1
                print(a)
            b = 2 + 1
            print(b)
        """)
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex("f"))
        self.project.do(user.get_changes())
        self.assertEqual(
            dedent("""\
                def f(p):
                    a = p + 1
                    print(a)
                f(2)
            """),
            self.mod1.read(),
        )

    # TODO: probably new options should be added to restructure
    def xxx_test_being_a_bit_more_intelligent_when_returning_assigneds(self):
        code = dedent("""\
            def f(p):
                a = p + 1
                return a
            var = 2 + 1
            print(var)
        """)
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex("f"))
        self.project.do(user.get_changes())
        self.assertEqual(
            dedent("""\
                def f(p):
                    a = p + 1
                    return a
                var = f(p)
                print(var)
            """),
            self.mod1.read(),
        )

    def test_exception_when_performing_a_function_with_yield(self):
        code = dedent("""\
            def func():
                yield 1
        """)
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            UseFunction(self.project, self.mod1, code.index("func"))

    def test_exception_when_performing_a_function_two_returns(self):
        code = dedent("""\
            def func():
                return 1
                return 2
        """)
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            UseFunction(self.project, self.mod1, code.index("func"))

    def test_exception_when_returns_is_not_the_last_statement(self):
        code = dedent("""\
            def func():
                return 2
                a = 1
        """)
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            UseFunction(self.project, self.mod1, code.index("func"))
