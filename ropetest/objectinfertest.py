import unittest
from textwrap import dedent

import rope.base.builtins  # Use fully-qualified names for clarity.
from rope.base import libutils
from ropetest import testutils


class ObjectInferTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def test_simple_type_inferencing(self):
        code = dedent("""\
            class Sample(object):
                pass
            a_var = Sample()
        """)
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope["Sample"].get_object()
        a_var = scope["a_var"].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_simple_type_inferencing_classes_defined_in_holding_scope(self):
        code = dedent("""\
            class Sample(object):
                pass
            def a_func():
                a_var = Sample()
        """)
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope["Sample"].get_object()
        a_var = scope["a_func"].get_object().get_scope()["a_var"].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_simple_type_inferencing_classes_in_class_methods(self):
        code = dedent("""\
            class Sample(object):
                pass
            class Another(object):
                def a_method():
                    a_var = Sample()
        """)
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope["Sample"].get_object()
        another_class = scope["Another"].get_object()
        a_var = another_class["a_method"].get_object().get_scope()["a_var"].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_simple_type_inferencing_class_attributes(self):
        code = dedent("""\
            class Sample(object):
                pass
            class Another(object):
                def __init__(self):
                    self.a_var = Sample()
        """)
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope["Sample"].get_object()
        another_class = scope["Another"].get_object()
        a_var = another_class["a_var"].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_simple_type_inferencing_for_in_class_assignments(self):
        code = dedent("""\
            class Sample(object):
                pass
            class Another(object):
                an_attr = Sample()
        """)
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope["Sample"].get_object()
        another_class = scope["Another"].get_object()
        an_attr = another_class["an_attr"].get_object()
        self.assertEqual(sample_class, an_attr.get_type())

    def test_simple_type_inferencing_for_chained_assignments(self):
        mod = dedent("""\
            class Sample(object):
                pass
            copied_sample = Sample""")
        mod_scope = libutils.get_string_scope(self.project, mod)
        sample_class = mod_scope["Sample"]
        copied_sample = mod_scope["copied_sample"]
        self.assertEqual(sample_class.get_object(), copied_sample.get_object())

    def test_following_chained_assignments_avoiding_circles(self):
        mod = dedent("""\
            class Sample(object):
                pass
            sample_class = Sample
            sample_class = sample_class
        """)
        mod_scope = libutils.get_string_scope(self.project, mod)
        sample_class = mod_scope["Sample"]
        sample_class_var = mod_scope["sample_class"]
        self.assertEqual(sample_class.get_object(), sample_class_var.get_object())

    def test_function_returned_object_static_type_inference1(self):
        src = dedent("""\
            class Sample(object):
                pass
            def a_func():
                return Sample
            a_var = a_func()
        """)
        scope = libutils.get_string_scope(self.project, src)
        sample_class = scope["Sample"]
        a_var = scope["a_var"]
        self.assertEqual(sample_class.get_object(), a_var.get_object())

    def test_function_returned_object_static_type_inference2(self):
        src = dedent("""\
            class Sample(object):
                pass
            def a_func():
                return Sample()
            a_var = a_func()
        """)
        scope = libutils.get_string_scope(self.project, src)
        sample_class = scope["Sample"].get_object()
        a_var = scope["a_var"].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_recursive_function_returned_object_static_type_inference(self):
        src = dedent("""\
            class Sample(object):
                pass
            def a_func():
                if True:
                    return Sample()
                else:
                    return a_func()
            a_var = a_func()
        """)
        scope = libutils.get_string_scope(self.project, src)
        sample_class = scope["Sample"].get_object()
        a_var = scope["a_var"].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_func_returned_obj_using_call_spec_func_static_type_infer(self):
        src = dedent("""\
            class Sample(object):
                def __call__(self):
                    return Sample
            sample = Sample()
            a_var = sample()""")
        scope = libutils.get_string_scope(self.project, src)
        sample_class = scope["Sample"]
        a_var = scope["a_var"]
        self.assertEqual(sample_class.get_object(), a_var.get_object())

    def test_list_type_inferencing(self):
        src = dedent("""\
            class Sample(object):
                pass
            a_var = [Sample()]
        """)
        scope = libutils.get_string_scope(self.project, src)
        sample_class = scope["Sample"].get_object()
        a_var = scope["a_var"].get_object()
        self.assertNotEqual(sample_class, a_var.get_type())

    def test_attributed_object_inference(self):
        src = dedent("""\
            class Sample(object):
                def __init__(self):
                    self.a_var = None
                def set(self):
                    self.a_var = Sample()
        """)
        scope = libutils.get_string_scope(self.project, src)
        sample_class = scope["Sample"].get_object()
        a_var = sample_class["a_var"].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_getting_property_attributes(self):
        src = dedent("""\
            class A(object):
                pass
            def f(*args):
                return A()
            class B(object):
                p = property(f)
            a_var = B().p
        """)
        pymod = libutils.get_string_module(self.project, src)
        a_class = pymod["A"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(a_class, a_var.get_type())

    def test_getting_property_attributes_with_method_getters(self):
        src = dedent("""\
            class A(object):
                pass
            class B(object):
                def p_get(self):
                    return A()
                p = property(p_get)
            a_var = B().p
        """)
        pymod = libutils.get_string_module(self.project, src)
        a_class = pymod["A"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(a_class, a_var.get_type())

    def test_lambda_functions(self):
        code = dedent("""\
            class C(object):
                pass
            l = lambda: C()
            a_var = l()""")
        mod = libutils.get_string_module(self.project, code)
        c_class = mod["C"].get_object()
        a_var = mod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_mixing_subscript_with_tuple_assigns(self):
        code = dedent("""\
            class C(object):
                attr = 0
            d = {}
            d[0], b = (0, C())
        """)
        mod = libutils.get_string_module(self.project, code)
        c_class = mod["C"].get_object()
        a_var = mod["b"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_mixing_ass_attr_with_tuple_assignment(self):
        code = dedent("""\
            class C(object):
                attr = 0
            c = C()
            c.attr, b = (0, C())
        """)
        mod = libutils.get_string_module(self.project, code)
        c_class = mod["C"].get_object()
        a_var = mod["b"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_mixing_slice_with_tuple_assigns(self):
        code = dedent("""\
            class C(object):
                attr = 0
            d = [None] * 3
            d[0:2], b = ((0,), C())
        """)
        mod = libutils.get_string_module(self.project, code)

        c_class = mod["C"].get_object()
        a_var = mod["b"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_nested_tuple_assignments(self):
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            a, (b, c) = (C1(), (C2(), C1()))
        """)
        mod = libutils.get_string_module(self.project, code)

        c1_class = mod["C1"].get_object()
        c2_class = mod["C2"].get_object()
        a_var = mod["a"].get_object()
        b_var = mod["b"].get_object()
        c_var = mod["c"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())
        self.assertEqual(c1_class, c_var.get_type())

    def test_empty_tuples(self):
        code = dedent("""\
            t = ()
            a, b = t
        """)
        mod = libutils.get_string_module(self.project, code)

        a = mod["a"].get_object()  # noqa

    def test_handling_generator_functions(self):
        code = dedent("""\
            class C(object):
                pass
            def f():
                yield C()
            for c in f():
                a_var = c
        """)
        mod = libutils.get_string_module(self.project, code)
        c_class = mod["C"].get_object()
        a_var = mod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_handling_generator_functions_for_strs(self):
        mod = testutils.create_module(self.project, "mod")
        mod.write(dedent("""\
            def f():
                yield ""
            for s in f():
                a_var = s
        """))
        pymod = self.project.get_pymodule(mod)
        a_var = pymod["a_var"].get_object()
        self.assertTrue(isinstance(a_var.get_type(), rope.base.builtins.Str))

    def test_considering_nones_to_be_unknowns(self):
        code = dedent("""\
            class C(object):
                pass
            a_var = None
            a_var = C()
            a_var = None
        """)
        mod = libutils.get_string_module(self.project, code)
        c_class = mod["C"].get_object()
        a_var = mod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_basic_list_comprehensions(self):
        code = dedent("""\
            class C(object):
                pass
            l = [C() for i in range(1)]
            a_var = l[0]
        """)
        mod = libutils.get_string_module(self.project, code)
        c_class = mod["C"].get_object()
        a_var = mod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_basic_generator_expressions(self):
        code = dedent("""\
            class C(object):
                pass
            l = (C() for i in range(1))
            a_var = list(l)[0]
        """)
        mod = libutils.get_string_module(self.project, code)
        c_class = mod["C"].get_object()
        a_var = mod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_list_comprehensions_and_loop_var(self):
        code = dedent("""\
            class C(object):
                pass
            c_objects = [C(), C()]
            l = [c for c in c_objects]
            a_var = l[0]
        """)
        mod = libutils.get_string_module(self.project, code)
        c_class = mod["C"].get_object()
        a_var = mod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_list_comprehensions_and_multiple_loop_var(self):
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            l = [(c1, c2) for c1 in [C1()] for c2 in [C2()]]
            a, b = l[0]
        """)
        mod = libutils.get_string_module(self.project, code)
        c1_class = mod["C1"].get_object()
        c2_class = mod["C2"].get_object()
        a_var = mod["a"].get_object()
        b_var = mod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_list_comprehensions_and_multiple_iters(self):
        code = dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            l = [(c1, c2) for c1, c2 in [(C1(), C2())]]
            a, b = l[0]
        """)
        mod = libutils.get_string_module(self.project, code)

        c1_class = mod["C1"].get_object()
        c2_class = mod["C2"].get_object()
        a_var = mod["a"].get_object()
        b_var = mod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_we_know_the_type_of_caught_exceptions(self):
        code = dedent("""\
            class MyError(Exception):
                pass
            try:

                raise MyError()
            except MyError as e:
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        my_error = mod["MyError"].get_object()
        e_var = mod["e"].get_object()
        self.assertEqual(my_error, e_var.get_type())

    def test_we_know_the_type_of_caught_multiple_excepts(self):
        code = dedent("""\
            class MyError(Exception):
                pass
            try:
                raise MyError()
            except (MyError, Exception) as e:
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        my_error = mod["MyError"].get_object()
        e_var = mod["e"].get_object()
        self.assertEqual(my_error, e_var.get_type())

    def test_using_property_as_decorators(self):
        code = dedent("""\
            class A(object):
                pass
            class B(object):
                @property
                def f(self):
                    return A()
            b = B()
            var = b.f
        """)
        mod = libutils.get_string_module(self.project, code)
        var = mod["var"].get_object()
        a = mod["A"].get_object()
        self.assertEqual(a, var.get_type())

    def test_using_property_as_decorators_and_passing_parameter(self):
        code = dedent("""\
            class B(object):
                @property
                def f(self):
                    return self
            b = B()
            var = b.f
        """)
        mod = libutils.get_string_module(self.project, code)
        var = mod["var"].get_object()
        a = mod["B"].get_object()
        self.assertEqual(a, var.get_type())
