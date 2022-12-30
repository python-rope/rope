import unittest
from textwrap import dedent

import rope.base.libutils
import rope.base.oi
from rope.base.builtins import Str
from ropetest import testutils


class DynamicOITest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project(validate_objectdb=True)
        self.pycore = self.project.pycore

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def test_simple_dti(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            def a_func(arg):
                return eval("arg")
            a_var = a_func(a_func)
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        self.assertEqual(pymod["a_func"].get_object(), pymod["a_var"].get_object())

    def test_module_dti(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        code = dedent("""\
            import mod1
            def a_func(arg):
                return eval("arg")
            a_var = a_func(mod1)
        """)
        mod2.write(code)
        self.pycore.run_module(mod2).wait_process()
        pymod2 = self.project.get_pymodule(mod2)
        self.assertEqual(self.project.get_pymodule(mod1), pymod2["a_var"].get_object())

    def test_class_from_another_module_dti(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        code1 = dedent("""\
            class AClass(object):
                pass
        """)
        code2 = dedent("""\
            from mod1 import AClass

            def a_func(arg):
                return eval("arg")
            a_var = a_func(AClass)
        """)
        mod1.write(code1)
        mod2.write(code2)
        self.pycore.run_module(mod2).wait_process()
        # pymod1 = self.project.get_pymodule(mod1)
        pymod2 = self.project.get_pymodule(mod2)
        self.assertEqual(pymod2["AClass"].get_object(), pymod2["a_var"].get_object())

    def test_class_dti(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class AClass(object):
                pass

            def a_func(arg):
                return eval("arg")
            a_var = a_func(AClass)
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        self.assertEqual(pymod["AClass"].get_object(), pymod["a_var"].get_object())

    def test_instance_dti(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class AClass(object):
                pass

            def a_func(arg):
                return eval("arg()")
            a_var = a_func(AClass)
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        self.assertEqual(
            pymod["AClass"].get_object(), pymod["a_var"].get_object().get_type()
        )

    def test_method_dti(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class AClass(object):
                def a_method(self, arg):
                    return eval("arg()")
            an_instance = AClass()
            a_var = an_instance.a_method(AClass)
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        self.assertEqual(
            pymod["AClass"].get_object(), pymod["a_var"].get_object().get_type()
        )

    def test_function_argument_dti(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            def a_func(arg):
                pass
            a_func(a_func)
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pyscope = self.project.get_pymodule(mod).get_scope()
        self.assertEqual(
            pyscope["a_func"].get_object(), pyscope.get_scopes()[0]["arg"].get_object()
        )

    def test_classes_with_the_same_name(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            def a_func(arg):
                class AClass(object):
                    pass
                return eval("arg")
            class AClass(object):
                pass
            a_var = a_func(AClass)
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        self.assertEqual(pymod["AClass"].get_object(), pymod["a_var"].get_object())

    def test_nested_classes(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            def a_func():
                class AClass(object):
                    pass
                return AClass
            def another_func(arg):
                return eval("arg")
            a_var = another_func(a_func())
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pyscope = self.project.get_pymodule(mod).get_scope()
        self.assertEqual(
            pyscope.get_scopes()[0]["AClass"].get_object(),
            pyscope["a_var"].get_object(),
        )

    def test_function_argument_dti2(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            def a_func(arg, a_builtin_type):
                pass
            a_func(a_func, [])
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pyscope = self.project.get_pymodule(mod).get_scope()
        self.assertEqual(
            pyscope["a_func"].get_object(), pyscope.get_scopes()[0]["arg"].get_object()
        )

    def test_dti_and_concluded_data_invalidation(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            def a_func(arg):
                return eval("arg")
            a_var = a_func(a_func)
        """)
        mod.write(code)
        pymod = self.project.get_pymodule(mod)
        pymod["a_var"].get_object()
        self.pycore.run_module(mod).wait_process()
        self.assertEqual(pymod["a_func"].get_object(), pymod["a_var"].get_object())

    def test_list_objects_and_dynamicoi(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C(object):
                pass
            def a_func(arg):
                return eval("arg")
            a_var = a_func([C()])[0]
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_for_loops_and_dynamicoi(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C(object):
                pass
            def a_func(arg):
                return eval("arg")
            for c in a_func([C()]):
                a_var = c
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_dict_objects_and_dynamicoi(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C(object):
                pass
            def a_func(arg):
                return eval("arg")
            a_var = a_func({1: C()})[1]
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_dict_keys_and_dynamicoi(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
                class C(object):
                    pass
                def a_func(arg):
                    return eval("arg")
                a_var = list(a_func({C(): 1}))[0]
            """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_dict_keys_and_dynamicoi2(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            def a_func(arg):
                return eval("arg")
            a, b = a_func((C1(), C2()))
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_strs_and_dynamicoi(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            def a_func(arg):
                return eval("arg")
            a_var = a_func("hey")
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        a_var = pymod["a_var"].get_object()
        self.assertTrue(isinstance(a_var.get_type(), rope.base.builtins.Str))

    def test_textual_transformations(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C(object):
                pass
            def f():
                pass
            a_var = C()
            a_list = [C()]
            a_str = "hey"
            a_file = open("file.txt")
        """)
        mod.write(code)
        to_pyobject = rope.base.oi.transform.TextualToPyObject(self.project)
        to_textual = rope.base.oi.transform.PyObjectToTextual(self.project)
        pymod = self.project.get_pymodule(mod)

        def complex_to_textual(pyobject):
            return to_textual.transform(
                to_pyobject.transform(to_textual.transform(pyobject))
            )

        test_variables = [
            ("C", ("defined", "mod.py", "C")),
            ("f", ("defined", "mod.py", "f")),
            ("a_var", ("instance", ("defined", "mod.py", "C"))),
            ("a_list", ("builtin", "list", ("instance", ("defined", "mod.py", "C")))),
            ("a_str", ("builtin", "str")),
            ("a_file", ("builtin", "file")),
        ]
        test_cases = [(pymod[v].get_object(), r) for v, r in test_variables]
        test_cases += [
            (pymod, ("defined", "mod.py")),
            (
                rope.base.builtins.builtins["enumerate"].get_object(),
                ("builtin", "function", "enumerate"),
            ),
        ]
        for var, result in test_cases:
            self.assertEqual(to_textual.transform(var), result)
            self.assertEqual(complex_to_textual(var), result)

    def test_arguments_with_keywords(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            def a_func(arg):
                return eval("arg")
            a = a_func(arg=C1())
            b = a_func(arg=C2())
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_a_function_with_different_returns(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            def a_func(arg):
                return eval("arg")
            a = a_func(C1())
            b = a_func(C2())
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_a_function_with_different_returns2(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            def a_func(p):
                if p == C1:
                    return C1()
                else:
                    return C2()
            a = a_func(C1)
            b = a_func(C2)
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_ignoring_star_args(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            def a_func(p, *args):
                if p == C1:
                    return C1()
                else:
                    return C2()
            a = a_func(C1, 1)
            b = a_func(C2, 2)
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_ignoring_double_star_args(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            def a_func(p, *kwds, **args):
                if p == C1:
                    return C1()
                else:
                    return C2()
            a = a_func(C1, kwd=1)
            b = a_func(C2, kwd=2)
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_invalidating_data_after_changing(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            def a_func(arg):
                return eval("arg")
            a_var = a_func(a_func)
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        mod.write(code.replace("a_func", "newfunc"))
        mod.write(code)
        pymod = self.project.get_pymodule(mod)
        self.assertNotEqual(pymod["a_func"].get_object(), pymod["a_var"].get_object())

    def test_invalidating_data_after_moving(self):
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write("class C(object):\n    pass\n")
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            import mod2
            def a_func(arg):
                return eval(arg)
            a_var = a_func("mod2.C")
        """)
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        mod.move("newmod.py")
        pymod = self.project.get_module("newmod")
        pymod2 = self.project.get_pymodule(mod2)
        self.assertEqual(pymod2["C"].get_object(), pymod["a_var"].get_object())


class NewStaticOITest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project(validate_objectdb=True)
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, "mod")

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def test_static_oi_for_simple_function_calls(self):
        code = dedent("""\
            class C(object):
                pass
            def f(p):
                pass
            f(C())
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        f_scope = pymod["f"].get_object().get_scope()
        p_type = f_scope["p"].get_object().get_type()
        self.assertEqual(c_class, p_type)

    def test_static_oi_not_failing_when_callin_callables(self):
        code = dedent("""\
            class C(object):
                pass
            C()
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)

    def test_static_oi_for_nested_calls(self):
        code = dedent("""\
            class C(object):
                pass
            def f(p):
                pass
            def g(p):
                return p
            f(g(C()))
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        f_scope = pymod["f"].get_object().get_scope()
        p_type = f_scope["p"].get_object().get_type()
        self.assertEqual(c_class, p_type)

    def test_static_oi_class_methods(self):
        code = dedent("""\
            class C(object):
                def f(self, p):
                    pass
            C().f(C())""")
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        f_scope = c_class["f"].get_object().get_scope()
        p_type = f_scope["p"].get_object().get_type()
        self.assertEqual(c_class, p_type)

    def test_static_oi_preventing_soi_maximum_recursion_exceptions(self):
        code = dedent("""\
            item = {}
            for item in item.keys():
                pass
        """)
        self.mod.write(code)
        try:
            self.pycore.analyze_module(self.mod)
        except RuntimeError as e:
            self.fail(str(e))

    def test_static_oi_for_infer_return_typs_from_funcs_based_on_params(self):
        code = dedent("""\
            class C(object):
                pass
            def func(p):
                return p
            a_var = func(C())
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_a_function_with_different_returns(self):
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            def a_func(arg):
                return arg
            a = a_func(C1())
            b = a_func(C2())
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_not_reporting_out_of_date_information(self):
        code = dedent("""\
            class C1(object):
                pass
            def f(arg):
                return C1()
            a_var = f()
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c1_class, a_var.get_type())

        self.mod.write(code.replace("C1", "C2"))
        pymod = self.project.get_pymodule(self.mod)
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c2_class, a_var.get_type())

    def test_invalidating_concluded_data_in_a_function(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write(dedent("""\
            def func(arg):
                temp = arg
                return temp
        """))
        mod2.write(dedent("""\
            import mod1
            class C1(object):
                pass
            class C2(object):
                pass
            a_var = mod1.func(C1())
        """))
        pymod2 = self.project.get_pymodule(mod2)
        c1_class = pymod2["C1"].get_object()
        a_var = pymod2["a_var"].get_object()
        self.assertEqual(c1_class, a_var.get_type())

        mod2.write(mod2.read()[: mod2.read().rfind("C1()")] + "C2())\n")
        pymod2 = self.project.get_pymodule(mod2)
        c2_class = pymod2["C2"].get_object()
        a_var = pymod2["a_var"].get_object()
        self.assertEqual(c2_class, a_var.get_type())

    def test_handling_generator_functions_for_strs(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            def f(p):
                yield p()
            for c in f(C):
                a_var = c
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    # TODO: Returning a generator for functions that yield unknowns
    @unittest.skip("Returning a generator that yields unknowns")
    def xxx_test_handl_generator_functions_when_unknown_type_is_yielded(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            def f():
                yield eval("C()")
            a_var = f()
        """))
        pymod = self.project.get_pymodule(self.mod)
        a_var = pymod["a_var"].get_object()
        self.assertTrue(isinstance(a_var.get_type(), rope.base.builtins.Generator))

    def test_static_oi_for_lists_depending_on_append_function(self):
        code = dedent("""\
            class C(object):
                pass
            l = list()
            l.append(C())
            a_var = l.pop()
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_static_oi_for_lists_per_object_for_get_item(self):
        code = dedent("""\
            class C(object):
                pass
            l = list()
            l.append(C())
            a_var = l[0]
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_static_oi_for_lists_per_object_for_fields(self):
        code = dedent("""\
            class C(object):
                pass
            class A(object):
                def __init__(self):
                    self.l = []
                def set(self):
                    self.l.append(C())
            a = A()
            a.set()
            a_var = a.l[0]
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_static_oi_for_lists_per_object_for_set_item(self):
        code = dedent("""\
            class C(object):
                pass
            l = [None]
            l[0] = C()
            a_var = l[0]
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_static_oi_for_lists_per_object_for_extending_lists(self):
        code = dedent("""\
            class C(object):
                pass
            l = []
            l.append(C())
            l2 = []
            l2.extend(l)
            a_var = l2[0]
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_static_oi_for_lists_per_object_for_iters(self):
        code = dedent("""\
            class C(object):
                pass
            l = []
            l.append(C())
            for c in l:
                a_var = c
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_static_oi_for_dicts_depending_on_append_function(self):
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            d = {}
            d[C1()] = C2()
            a, b = d.popitem()
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_static_oi_for_dicts_depending_on_for_loops(self):
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            d = {}
            d[C1()] = C2()
            for k, v in d.items():
                a = k
                b = v
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_static_oi_for_dicts_depending_on_update(self):
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            d = {}
            d[C1()] = C2()
            d2 = {}
            d2.update(d)
            a, b = d2.popitem()
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_static_oi_for_dicts_depending_on_update_on_seqs(self):
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            d = {}
            d.update([(C1(), C2())])
            a, b = d.popitem()
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_static_oi_for_sets_per_object_for_set_item(self):
        code = dedent("""\
            class C(object):
                pass
            s = set()
            s.add(C())
            a_var = s.pop()
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_properties_and_calling_get_property(self):
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                c1 = C1()
                def get_c1(self):
                    return self.c1
                p = property(get_c1)
            c2 = C2()
            a_var = c2.p
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c1_class, a_var.get_type())

    def test_soi_on_constructors(self):
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                def __init__(self, arg):
                    self.attr = arg
            c2 = C2(C1())
            a_var = c2.attr""")
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c1_class, a_var.get_type())

    def test_soi_on_literal_assignment(self):
        code = 'a_var = ""'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        a_var = pymod["a_var"].get_object()
        self.assertEqual(Str, type(a_var.get_type()))

    @testutils.only_for_versions_higher("3.6")
    def test_soi_on_typed_assignment(self):
        code = "a_var: str"
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        a_var = pymod["a_var"].get_object()
        self.assertEqual(Str, type(a_var.get_type()))

    def test_not_saving_unknown_function_returns(self):
        mod2 = testutils.create_module(self.project, "mod2")
        self.mod.write(dedent("""\
            class C(object):
                pass
            l = []
            l.append(C())
        """))
        mod2.write(dedent("""\
            import mod
            def f():
                return mod.l.pop()
            a_var = f()
        """))
        pymod = self.project.get_pymodule(self.mod)
        pymod2 = self.project.get_pymodule(mod2)
        c_class = pymod["C"].get_object()
        a_var = pymod2["a_var"]

        self.pycore.analyze_module(mod2)
        self.assertNotEqual(c_class, a_var.get_object().get_type())

        self.pycore.analyze_module(self.mod)
        self.assertEqual(c_class, a_var.get_object().get_type())

    def test_using_the_best_callinfo(self):
        code = dedent("""\
            class C1(object):
                pass
            def f(arg1, arg2, arg3):
                pass
            f("", None, C1())
            f("", C1(), None)
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        f_scope = pymod["f"].get_object().get_scope()
        arg2 = f_scope["arg2"].get_object()
        self.assertEqual(c1_class, arg2.get_type())

    def test_call_function_and_parameters(self):
        code = dedent("""\
            class A(object):
                def __call__(self, p):
                    pass
            A()("")
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        scope = self.project.get_pymodule(self.mod).get_scope()
        p_object = scope.get_scopes()[0].get_scopes()[0]["p"].get_object()
        self.assertTrue(isinstance(p_object.get_type(), rope.base.builtins.Str))

    def test_report_change_in_libutils(self):
        self.project.prefs["automatic_soa"] = True
        code = dedent("""\
            class C(object):
                pass
            def f(p):
                pass
            f(C())
        """)
        with open(self.mod.real_path, "w") as mod_file:
            mod_file.write(code)

        rope.base.libutils.report_change(self.project, self.mod.real_path, "")
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        f_scope = pymod["f"].get_object().get_scope()
        p_type = f_scope["p"].get_object().get_type()
        self.assertEqual(c_class, p_type)

    def test_report_libutils_and_analyze_all_modules(self):
        code = dedent("""\
            class C(object):
                pass
            def f(p):
                pass
            f(C())
        """)
        self.mod.write(code)
        rope.base.libutils.analyze_modules(self.project)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        f_scope = pymod["f"].get_object().get_scope()
        p_type = f_scope["p"].get_object().get_type()
        self.assertEqual(c_class, p_type)

    def test_validation_problems_for_objectdb_retrievals(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write(dedent("""\
            l = []
            var = l.pop()
        """))
        mod2.write(dedent("""\
            import mod1

            class C(object):
                pass
            mod1.l.append(C())
        """))
        self.pycore.analyze_module(mod2)

        pymod2 = self.project.get_pymodule(mod2)
        c_class = pymod2["C"].get_object()
        pymod1 = self.project.get_pymodule(mod1)
        var_pyname = pymod1["var"]
        self.assertEqual(c_class, var_pyname.get_object().get_type())
        mod2.write(dedent("""\
            import mod1

            mod1.l.append("")
        """))
        self.assertNotEqual(
            c_class, var_pyname.get_object().get_type(), "Class `C` no more exists"
        )

    def test_validation_problems_for_changing_builtin_types(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            l = []
            l.append("")
        """))
        self.pycore.analyze_module(mod1)

        mod1.write(dedent("""\
            l = {}
            v = l["key"]
        """))
        pymod1 = self.project.get_pymodule(mod1)
        var = pymod1["v"].get_object()  # noqa

    def test_always_returning_containing_class_for_selfs(self):
        code = dedent("""\
            class A(object):
                def f(p):
                    return p
            class B(object):
                pass
            b = B()
            b.f()
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        a_class = pymod["A"].get_object()
        f_scope = a_class.get_scope().get_scopes()[0]
        p_type = f_scope["p"].get_object().get_type()
        self.assertEqual(a_class, p_type)

    def test_following_function_calls_when_asked_to(self):
        code = dedent("""\
            class A(object):
                pass
            class C(object):
                def __init__(self, arg):
                    self.attr = arg
            def f(p):
                return C(p)
            c = f(A())
            x = c.attr
        """)
        self.mod.write(code)
        self.pycore.analyze_module(self.mod, followed_calls=1)
        pymod = self.project.get_pymodule(self.mod)
        a_class = pymod["A"].get_object()
        x_var = pymod["x"].get_object().get_type()
        self.assertEqual(a_class, x_var)

    def test_set_comprehension(self):
        code = dedent("""\
            x = {s.strip() for s in X()}
            x.add('x')
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        x_var = pymod["x"].pyobject.get()
