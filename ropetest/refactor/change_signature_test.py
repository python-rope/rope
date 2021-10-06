from textwrap import dedent
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import rope.base.exceptions
from rope.refactor import change_signature
from ropetest import testutils


class ChangeSignatureTest(unittest.TestCase):
    def setUp(self):
        super(ChangeSignatureTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, "mod")

    def tearDown(self):
        testutils.remove_project(self.project)
        super(ChangeSignatureTest, self).tearDown()

    def test_normalizing_parameters_for_trivial_case(self):
        code = dedent("""\
            def a_func():
                pass
            a_func()""")
        self.mod.write(code)
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentNormalizer()]))
        self.assertEqual(code, self.mod.read())

    def test_normalizing_parameters_for_trivial_case2(self):
        code = dedent("""\
            def a_func(param):
                pass
            a_func(2)""")
        self.mod.write(code)
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentNormalizer()]))
        self.assertEqual(code, self.mod.read())

    def test_normalizing_parameters_for_unneeded_keyword(self):
        self.mod.write(
            dedent("""\
                def a_func(param):
                    pass
                a_func(param=1)"""
            )
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentNormalizer()]))
        self.assertEqual(
            dedent("""\
                def a_func(param):
                    pass
                a_func(1)"""
            ),
            self.mod.read()
        )

    def test_normalizing_parameters_for_unneeded_keyword_for_methods(self):
        code = dedent("""\
            class A(object):
                def a_func(self, param):
                    pass
            a_var = A()
            a_var.a_func(param=1)
        """)
        self.mod.write(code)
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentNormalizer()]))
        expected = dedent("""\
            class A(object):
                def a_func(self, param):
                    pass
            a_var = A()
            a_var.a_func(1)
        """)
        self.assertEqual(expected, self.mod.read())

    def test_normalizing_parameters_for_unsorted_keyword(self):
        self.mod.write(
            dedent("""\
                def a_func(p1, p2):
                    pass
                a_func(p2=2, p1=1)"""
            )
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentNormalizer()]))
        self.assertEqual(
            dedent("""\
                def a_func(p1, p2):
                    pass
                a_func(1, 2)"""
            ),
            self.mod.read()
        )

    def test_raising_exceptions_for_non_functions(self):
        self.mod.write("a_var = 10")
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            change_signature.ChangeSignature(
                self.project, self.mod, self.mod.read().index("a_var") + 1
            )

    def test_normalizing_parameters_for_args_parameter(self):
        self.mod.write(
            dedent("""\
                def a_func(*arg):
                    pass
                a_func(1, 2)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentNormalizer()]))
        self.assertEqual(
            dedent("""\
                def a_func(*arg):
                    pass
                a_func(1, 2)
            """),
            self.mod.read(),
        )

    def test_normalizing_parameters_for_args_parameter_and_keywords(self):
        self.mod.write(
            dedent("""\
                def a_func(param, *args):
                    pass
                a_func(*[1, 2, 3])
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentNormalizer()]))
        self.assertEqual(
            dedent("""\
                def a_func(param, *args):
                    pass
                a_func(*[1, 2, 3])
            """),
            self.mod.read(),
        )

    def test_normalizing_functions_from_other_modules(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(
            dedent("""\
                def a_func(param):
                    pass
            """)
        )
        self.mod.write(
            dedent("""\
                import mod1
                mod1.a_func(param=1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, mod1, mod1.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentNormalizer()]))
        self.assertEqual(
            dedent("""\
                import mod1
                mod1.a_func(1)
            """),
            self.mod.read(),
        )

    def test_normalizing_parameters_for_keyword_parameters(self):
        self.mod.write(
            dedent("""\
                def a_func(p1, **kwds):
                    pass
                a_func(p2=2, p1=1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentNormalizer()]))
        self.assertEqual(
            dedent("""\
                def a_func(p1, **kwds):
                    pass
                a_func(1, p2=2)
            """),
            self.mod.read(),
        )

    def test_removing_arguments(self):
        self.mod.write(
            dedent("""\
                def a_func(p1):
                    pass
                a_func(1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentRemover(0)]))
        self.assertEqual(
            dedent("""\
                def a_func():
                    pass
                a_func()
            """),
            self.mod.read(),
        )

    def test_removing_arguments_with_multiple_args(self):
        self.mod.write(
            dedent("""\
                def a_func(p1, p2):
                    pass
                a_func(1, 2)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentRemover(0)]))
        self.assertEqual(
            dedent("""\
                def a_func(p2):
                    pass
                a_func(2)
            """),
            self.mod.read(),
        )

    def test_removing_arguments_passed_as_keywords(self):
        self.mod.write(
            dedent("""\
                def a_func(p1):
                    pass
                a_func(p1=1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentRemover(0)]))
        self.assertEqual(
            dedent("""\
                def a_func():
                    pass
                a_func()
            """),
            self.mod.read(),
        )

    def test_removing_arguments_with_defaults(self):
        self.mod.write(
            dedent("""\
                def a_func(p1=1):
                    pass
                a_func(1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentRemover(0)]))
        self.assertEqual(
            dedent("""\
                def a_func():
                    pass
                a_func()
            """),
            self.mod.read(),
        )

    def test_removing_arguments_star_args(self):
        self.mod.write(
            dedent("""\
                def a_func(p1, *args):
                    pass
                a_func(1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentRemover(1)]))
        self.assertEqual(
            dedent("""\
                def a_func(p1):
                    pass
                a_func(1)
            """),
            self.mod.read(),
        )

    def test_removing_keyword_arg(self):
        self.mod.write(
            dedent("""\
                def a_func(p1, **kwds):
                    pass
                a_func(1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentRemover(1)]))
        self.assertEqual(
            dedent("""\
                def a_func(p1):
                    pass
                a_func(1)
            """),
            self.mod.read(),
        )

    def test_removing_keyword_arg2(self):
        self.mod.write(
            dedent("""\
                def a_func(p1, *args, **kwds):
                    pass
                a_func(1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentRemover(2)]))
        self.assertEqual(
            dedent("""\
                def a_func(p1, *args):
                    pass
                a_func(1)
            """),
            self.mod.read(),
        )

    # XXX: What to do here for star args?
    @unittest.skip("How to deal with start args?")
    def xxx_test_removing_arguments_star_args2(self):
        self.mod.write(
            dedent("""\
                def a_func(p1, *args):
                    pass
                a_func(2, 3, p1=1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentRemover(1)]))
        self.assertEqual(
            dedent("""\
                def a_func(p1):
                    pass
                a_func(p1=1)
            """),
            self.mod.read(),
        )

    # XXX: What to do here for star args?
    def xxx_test_removing_arguments_star_args3(self):
        self.mod.write(
            dedent("""\
                def a_func(p1, *args):
                    pass
                a_func(*[1, 2, 3])
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentRemover(1)]))
        self.assertEqual(
            dedent("""\
                def a_func(p1):
                    pass
                a_func(*[1, 2, 3])
            """),
            self.mod.read(),
        )

    def test_adding_arguments_for_normal_args_changing_definition(self):
        self.mod.write(
            dedent("""\
                def a_func():
                    pass
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(
            signature.get_changes([change_signature.ArgumentAdder(0, "p1")])
        )
        self.assertEqual(
            dedent("""\
                def a_func(p1):
                    pass
            """),
            self.mod.read(),
        )

    def test_adding_arguments_for_normal_args_with_defaults(self):
        self.mod.write(
            dedent("""\
                def a_func():
                    pass
                a_func()
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        adder = change_signature.ArgumentAdder(0, "p1", "None")
        self.project.do(signature.get_changes([adder]))
        self.assertEqual(
            dedent("""\
                def a_func(p1=None):
                    pass
                a_func()
            """),
            self.mod.read(),
        )

    def test_adding_arguments_for_normal_args_changing_calls(self):
        self.mod.write(
            dedent("""\
                def a_func():
                    pass
                a_func()
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        adder = change_signature.ArgumentAdder(0, "p1", "None", "1")
        self.project.do(signature.get_changes([adder]))
        self.assertEqual(
            dedent("""\
                def a_func(p1=None):
                    pass
                a_func(1)
            """),
            self.mod.read(),
        )

    def test_adding_arguments_for_norm_args_chang_calls_with_kwords(self):
        self.mod.write(
            dedent("""\
                def a_func(p1=0):
                    pass
                a_func()
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        adder = change_signature.ArgumentAdder(1, "p2", "0", "1")
        self.project.do(signature.get_changes([adder]))
        self.assertEqual(
            dedent("""\
                def a_func(p1=0, p2=0):
                    pass
                a_func(p2=1)
            """),
            self.mod.read(),
        )

    def test_adding_arguments_for_norm_args_chang_calls_with_no_value(self):
        self.mod.write(
            dedent("""\
                def a_func(p2=0):
                    pass
                a_func(1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        adder = change_signature.ArgumentAdder(0, "p1", "0", None)
        self.project.do(signature.get_changes([adder]))
        self.assertEqual(
            dedent("""\
                def a_func(p1=0, p2=0):
                    pass
                a_func(p2=1)
            """),
            self.mod.read(),
        )

    def test_adding_duplicate_parameter_and_raising_exceptions(self):
        self.mod.write(
            dedent("""\
                def a_func(p1):
                    pass
            """)
        )
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            signature = change_signature.ChangeSignature(
                self.project, self.mod, self.mod.read().index("a_func") + 1
            )
            self.project.do(
                signature.get_changes([change_signature.ArgumentAdder(1, "p1")])
            )

    def test_inlining_default_arguments(self):
        self.mod.write(
            dedent("""\
                def a_func(p1=0):
                    pass
                a_func()
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(
            signature.get_changes([change_signature.ArgumentDefaultInliner(0)])
        )
        self.assertEqual(
            dedent("""\
                def a_func(p1=0):
                    pass
                a_func(0)
            """),
            self.mod.read(),
        )

    def test_inlining_default_arguments2(self):
        self.mod.write(
            dedent("""\
                def a_func(p1=0):
                    pass
                a_func(1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(
            signature.get_changes([change_signature.ArgumentDefaultInliner(0)])
        )
        self.assertEqual(
            dedent("""\
                def a_func(p1=0):
                    pass
                a_func(1)
            """),
            self.mod.read(),
        )

    def test_preserving_args_and_keywords_order(self):
        self.mod.write(
            dedent("""\
                def a_func(*args, **kwds):
                    pass
                a_func(3, 1, 2, a=1, c=3, b=2)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentNormalizer()]))
        self.assertEqual(
            dedent("""\
                def a_func(*args, **kwds):
                    pass
                a_func(3, 1, 2, a=1, c=3, b=2)
            """),
            self.mod.read(),
        )

    def test_change_order_for_only_one_parameter(self):
        self.mod.write(
            dedent("""\
                def a_func(p1):
                    pass
                a_func(1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(
            signature.get_changes([change_signature.ArgumentReorderer([0])])
        )
        self.assertEqual(
            dedent("""\
                def a_func(p1):
                    pass
                a_func(1)
            """),
            self.mod.read(),
        )

    def test_change_order_for_two_parameter(self):
        self.mod.write(
            dedent("""\
                def a_func(p1, p2):
                    pass
                a_func(1, 2)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(
            signature.get_changes([change_signature.ArgumentReorderer([1, 0])])
        )
        self.assertEqual(
            dedent("""\
                def a_func(p2, p1):
                    pass
                a_func(2, 1)
            """),
            self.mod.read(),
        )

    def test_reordering_multi_line_function_headers(self):
        self.mod.write(
            dedent("""\
                def a_func(p1,
                 p2):
                    pass
                a_func(1, 2)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(
            signature.get_changes([change_signature.ArgumentReorderer([1, 0])])
        )
        self.assertEqual(
            dedent("""\
                def a_func(p2, p1):
                    pass
                a_func(2, 1)
            """),
            self.mod.read(),
        )

    def test_changing_order_with_static_params(self):
        self.mod.write(
            dedent("""\
                def a_func(p1, p2=0, p3=0):
                    pass
                a_func(1, 2)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(
            signature.get_changes([change_signature.ArgumentReorderer([0, 2, 1])])
        )
        self.assertEqual(
            dedent("""\
                def a_func(p1, p3=0, p2=0):
                    pass
                a_func(1, p2=2)
            """),
            self.mod.read(),
        )

    def test_doing_multiple_changes(self):
        changers = []
        self.mod.write(
            dedent("""\
                def a_func(p1):
                    pass
                a_func(1)
            """)
        )
        changers.append(change_signature.ArgumentRemover(0))
        changers.append(change_signature.ArgumentAdder(0, "p2", None, None))
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        signature.get_changes(changers).do()
        self.assertEqual(
            dedent("""\
                def a_func(p2):
                    pass
                a_func()
            """),
            self.mod.read(),
        )

    def test_doing_multiple_changes2(self):
        changers = []
        self.mod.write(
            dedent("""\
                def a_func(p1, p2):
                    pass
                a_func(p2=2)
            """)
        )
        changers.append(change_signature.ArgumentAdder(2, "p3", None, "3"))
        changers.append(change_signature.ArgumentReorderer([1, 0, 2]))
        changers.append(change_signature.ArgumentRemover(1))
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        signature.get_changes(changers).do()
        self.assertEqual(
            dedent("""\
                def a_func(p2, p3):
                    pass
                a_func(2, 3)
            """),
            self.mod.read(),
        )

    def test_changing_signature_in_subclasses(self):
        self.mod.write(
            dedent("""\
                class A(object):
                    def a_method(self):
                        pass
                class B(A):
                    def a_method(self):
                        pass
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_method") + 1
        )
        signature.get_changes(
            [change_signature.ArgumentAdder(1, "p1")], in_hierarchy=True
        ).do()
        self.assertEqual(
            dedent("""\
                class A(object):
                    def a_method(self, p1):
                        pass
                class B(A):
                    def a_method(self, p1):
                        pass
            """),
            self.mod.read(),
        )

    def test_differentiating_class_accesses_from_instance_accesses(self):
        self.mod.write(
            dedent("""\
                class A(object):
                    def a_func(self, param):
                        pass
                a_var = A()
                A.a_func(a_var, param=1)"""
            )
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("a_func") + 1
        )
        self.project.do(signature.get_changes([change_signature.ArgumentRemover(1)]))
        self.assertEqual(
            dedent("""\
                class A(object):
                    def a_func(self):
                        pass
                a_var = A()
                A.a_func(a_var)"""
            ),
            self.mod.read()
        )

    def test_changing_signature_for_constructors(self):
        self.mod.write(
            dedent("""\
                class C(object):
                    def __init__(self, p):
                        pass
                c = C(1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("C") + 1
        )
        signature.get_changes([change_signature.ArgumentRemover(1)]).do()
        self.assertEqual(
            dedent("""\
                class C(object):
                    def __init__(self):
                        pass
                c = C()
            """),
            self.mod.read(),
        )

    def test_changing_signature_for_constructors2(self):
        self.mod.write(
            dedent("""\
                class C(object):
                    def __init__(self, p):
                        pass
                c = C(1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("__init__") + 1
        )
        signature.get_changes([change_signature.ArgumentRemover(1)]).do()
        self.assertEqual(
            dedent("""\
                class C(object):
                    def __init__(self):
                        pass
                c = C()
            """),
            self.mod.read(),
        )

    def test_changing_signature_for_constructors_when_using_super(self):
        self.mod.write(
            dedent("""\
                class A(object):
                    def __init__(self, p):
                        pass
                class B(A):
                    def __init__(self, p):
                        super(B, self).__init__(p)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index("__init__") + 1
        )
        signature.get_changes([change_signature.ArgumentRemover(1)]).do()
        self.assertEqual(
            dedent("""\
                class A(object):
                    def __init__(self):
                        pass
                class B(A):
                    def __init__(self, p):
                        super(B, self).__init__()
            """),
            self.mod.read(),
        )

    def test_redordering_arguments_reported_by_mft(self):
        self.mod.write(
            dedent("""\
                def f(a, b, c):
                    pass
                f(1, 2, 3)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().rindex("f")
        )
        signature.get_changes([change_signature.ArgumentReorderer([1, 2, 0])]).do()
        self.assertEqual(
            dedent("""\
                def f(b, c, a):
                    pass
                f(2, 3, 1)
            """),
            self.mod.read(),
        )

    def test_resources_parameter(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write("def a_func(param):\n    pass\n")
        self.mod.write(
            dedent("""\
                import mod1
                mod1.a_func(1)
            """)
        )
        signature = change_signature.ChangeSignature(
            self.project, mod1, mod1.read().index("a_func") + 1
        )
        signature.get_changes(
            [change_signature.ArgumentRemover(0)], resources=[mod1]
        ).do()
        self.assertEqual(
            dedent("""\
                import mod1
                mod1.a_func(1)
            """),
            self.mod.read(),
        )
        self.assertEqual(
            dedent("""\
                def a_func():
                    pass
            """),
            mod1.read(),
        )

    def test_reordering_and_automatic_defaults(self):
        code = dedent("""\
            def f(p1, p2=2):
                pass
            f(1, 2)
        """)
        self.mod.write(code)
        signature = change_signature.ChangeSignature(
            self.project, self.mod, code.index("f(")
        )
        reorder = change_signature.ArgumentReorderer([1, 0], autodef="1")
        signature.get_changes([reorder]).do()
        expected = dedent("""\
            def f(p2=2, p1=1):
                pass
            f(2, 1)
        """)
        self.assertEqual(expected, self.mod.read())
