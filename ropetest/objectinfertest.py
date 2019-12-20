try:
    import unittest2 as unittest
except ImportError:
    import unittest

import rope.base.project
import rope.base.builtins
from rope.base import libutils
from ropetest import testutils


class ObjectInferTest(unittest.TestCase):

    def setUp(self):
        super(ObjectInferTest, self).setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(ObjectInferTest, self).tearDown()

    def test_simple_type_inferencing(self):
        code = 'class Sample(object):\n    pass\na_var = Sample()\n'
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope['Sample'].get_object()
        a_var = scope['a_var'].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_simple_type_inferencing_classes_defined_in_holding_scope(self):
        code = 'class Sample(object):\n    pass\n' \
               'def a_func():\n    a_var = Sample()\n'
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope['Sample'].get_object()
        a_var = scope['a_func'].get_object().\
            get_scope()['a_var'].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_simple_type_inferencing_classes_in_class_methods(self):
        code = 'class Sample(object):\n    pass\n' \
               'class Another(object):\n' \
               '    def a_method():\n        a_var = Sample()\n'
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope['Sample'].get_object()
        another_class = scope['Another'].get_object()
        a_var = another_class['a_method'].\
            get_object().get_scope()['a_var'].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_simple_type_inferencing_class_attributes(self):
        code = 'class Sample(object):\n    pass\n' \
               'class Another(object):\n' \
               '    def __init__(self):\n        self.a_var = Sample()\n'
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope['Sample'].get_object()
        another_class = scope['Another'].get_object()
        a_var = another_class['a_var'].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_simple_type_inferencing_for_in_class_assignments(self):
        code = 'class Sample(object):\n    pass\n' \
               'class Another(object):\n    an_attr = Sample()\n'
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope['Sample'].get_object()
        another_class = scope['Another'].get_object()
        an_attr = another_class['an_attr'].get_object()
        self.assertEqual(sample_class, an_attr.get_type())

    def test_simple_type_inferencing_for_chained_assignments(self):
        mod = 'class Sample(object):\n    pass\n' \
              'copied_sample = Sample'
        mod_scope = libutils.get_string_scope(self.project, mod)
        sample_class = mod_scope['Sample']
        copied_sample = mod_scope['copied_sample']
        self.assertEqual(sample_class.get_object(),
                          copied_sample.get_object())

    def test_following_chained_assignments_avoiding_circles(self):
        mod = 'class Sample(object):\n    pass\n' \
              'sample_class = Sample\n' \
              'sample_class = sample_class\n'
        mod_scope = libutils.get_string_scope(self.project, mod)
        sample_class = mod_scope['Sample']
        sample_class_var = mod_scope['sample_class']
        self.assertEqual(sample_class.get_object(),
                          sample_class_var.get_object())

    def test_function_returned_object_static_type_inference1(self):
        src = 'class Sample(object):\n    pass\n' \
              'def a_func():\n    return Sample\n' \
              'a_var = a_func()\n'
        scope = libutils.get_string_scope(self.project, src)
        sample_class = scope['Sample']
        a_var = scope['a_var']
        self.assertEqual(sample_class.get_object(), a_var.get_object())

    def test_function_returned_object_static_type_inference2(self):
        src = 'class Sample(object):\n    pass\n' \
              'def a_func():\n    return Sample()\n' \
              'a_var = a_func()\n'
        scope = libutils.get_string_scope(self.project, src)
        sample_class = scope['Sample'].get_object()
        a_var = scope['a_var'].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_recursive_function_returned_object_static_type_inference(self):
        src = 'class Sample(object):\n    pass\n' \
              'def a_func():\n' \
              '    if True:\n        return Sample()\n' \
              '    else:\n        return a_func()\n' \
              'a_var = a_func()\n'
        scope = libutils.get_string_scope(self.project, src)
        sample_class = scope['Sample'].get_object()
        a_var = scope['a_var'].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_func_returned_obj_using_call_spec_func_static_type_infer(self):
        src = 'class Sample(object):\n' \
              '    def __call__(self):\n        return Sample\n' \
              'sample = Sample()\na_var = sample()'
        scope = libutils.get_string_scope(self.project, src)
        sample_class = scope['Sample']
        a_var = scope['a_var']
        self.assertEqual(sample_class.get_object(), a_var.get_object())

    def test_list_type_inferencing(self):
        src = 'class Sample(object):\n    pass\na_var = [Sample()]\n'
        scope = libutils.get_string_scope(self.project, src)
        sample_class = scope['Sample'].get_object()
        a_var = scope['a_var'].get_object()
        self.assertNotEqual(sample_class, a_var.get_type())

    def test_attributed_object_inference(self):
        src = 'class Sample(object):\n' \
              '    def __init__(self):\n        self.a_var = None\n' \
              '    def set(self):\n        self.a_var = Sample()\n'
        scope = libutils.get_string_scope(self.project, src)
        sample_class = scope['Sample'].get_object()
        a_var = sample_class['a_var'].get_object()
        self.assertEqual(sample_class, a_var.get_type())

    def test_getting_property_attributes(self):
        src = 'class A(object):\n    pass\n' \
              'def f(*args):\n    return A()\n' \
              'class B(object):\n    p = property(f)\n' \
              'a_var = B().p\n'
        pymod = libutils.get_string_module(self.project, src)
        a_class = pymod['A'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(a_class, a_var.get_type())

    def test_getting_property_attributes_with_method_getters(self):
        src = 'class A(object):\n    pass\n' \
              'class B(object):\n    def p_get(self):\n        return A()\n' \
              '    p = property(p_get)\n' \
              'a_var = B().p\n'
        pymod = libutils.get_string_module(self.project, src)
        a_class = pymod['A'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(a_class, a_var.get_type())

    def test_lambda_functions(self):
        code = 'class C(object):\n    pass\n' \
               'l = lambda: C()\na_var = l()'
        mod = libutils.get_string_module(self.project, code)
        c_class = mod['C'].get_object()
        a_var = mod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_mixing_subscript_with_tuple_assigns(self):
        code = 'class C(object):\n    attr = 0\n' \
               'd = {}\nd[0], b = (0, C())\n'
        mod = libutils.get_string_module(self.project, code)
        c_class = mod['C'].get_object()
        a_var = mod['b'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_mixing_ass_attr_with_tuple_assignment(self):
        code = 'class C(object):\n    attr = 0\n' \
               'c = C()\nc.attr, b = (0, C())\n'
        mod = libutils.get_string_module(self.project, code)
        c_class = mod['C'].get_object()
        a_var = mod['b'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_mixing_slice_with_tuple_assigns(self):
        mod = libutils.get_string_module(
            self.project,
            'class C(object):\n    attr = 0\n'
            'd = [None] * 3\nd[0:2], b = ((0,), C())\n')
        c_class = mod['C'].get_object()
        a_var = mod['b'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_nested_tuple_assignments(self):
        mod = libutils.get_string_module(
            self.project,
            'class C1(object):\n    pass\nclass C2(object):\n    pass\n'
            'a, (b, c) = (C1(), (C2(), C1()))\n')
        c1_class = mod['C1'].get_object()
        c2_class = mod['C2'].get_object()
        a_var = mod['a'].get_object()
        b_var = mod['b'].get_object()
        c_var = mod['c'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())
        self.assertEqual(c1_class, c_var.get_type())

    def test_empty_tuples(self):
        mod = libutils.get_string_module(
            self.project, 't = ()\na, b = t\n')
        a = mod['a'].get_object()  # noqa

    def test_handling_generator_functions(self):
        code = 'class C(object):\n    pass\n' \
               'def f():\n    yield C()\n' \
               'for c in f():\n    a_var = c\n'
        mod = libutils.get_string_module(self.project, code)
        c_class = mod['C'].get_object()
        a_var = mod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_handling_generator_functions_for_strs(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('def f():\n    yield ""\n'
                  'for s in f():\n    a_var = s\n')
        pymod = self.project.get_pymodule(mod)
        a_var = pymod['a_var'].get_object()
        self.assertTrue(isinstance(a_var.get_type(), rope.base.builtins.Str))

    def test_considering_nones_to_be_unknowns(self):
        code = 'class C(object):\n    pass\n' \
               'a_var = None\na_var = C()\na_var = None\n'
        mod = libutils.get_string_module(self.project, code)
        c_class = mod['C'].get_object()
        a_var = mod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_basic_list_comprehensions(self):
        code = 'class C(object):\n    pass\n' \
               'l = [C() for i in range(1)]\na_var = l[0]\n'
        mod = libutils.get_string_module(self.project, code)
        c_class = mod['C'].get_object()
        a_var = mod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_basic_generator_expressions(self):
        code = 'class C(object):\n    pass\n' \
               'l = (C() for i in range(1))\na_var = list(l)[0]\n'
        mod = libutils.get_string_module(self.project, code)
        c_class = mod['C'].get_object()
        a_var = mod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_list_comprehensions_and_loop_var(self):
        code = 'class C(object):\n    pass\n' \
               'c_objects = [C(), C()]\n' \
               'l = [c for c in c_objects]\na_var = l[0]\n'
        mod = libutils.get_string_module(self.project, code)
        c_class = mod['C'].get_object()
        a_var = mod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_list_comprehensions_and_multiple_loop_var(self):
        code = 'class C1(object):\n    pass\n' \
               'class C2(object):\n    pass\n' \
               'l = [(c1, c2) for c1 in [C1()] for c2 in [C2()]]\n' \
               'a, b = l[0]\n'
        mod = libutils.get_string_module(self.project, code)
        c1_class = mod['C1'].get_object()
        c2_class = mod['C2'].get_object()
        a_var = mod['a'].get_object()
        b_var = mod['b'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_list_comprehensions_and_multiple_iters(self):
        mod = libutils.get_string_module(
            self.project,
            'class C1(object):\n    pass\nclass C2(object):\n    pass\n'
            'l = [(c1, c2) for c1, c2 in [(C1(), C2())]]\n'
            'a, b = l[0]\n')
        c1_class = mod['C1'].get_object()
        c2_class = mod['C2'].get_object()
        a_var = mod['a'].get_object()
        b_var = mod['b'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_we_know_the_type_of_catched_exceptions(self):
        code = 'class MyError(Exception):\n    pass\n' \
               'try:\n    raise MyError()\n' \
               'except MyError as e:\n    pass\n'
        mod = libutils.get_string_module(self.project, code)
        my_error = mod['MyError'].get_object()
        e_var = mod['e'].get_object()
        self.assertEqual(my_error, e_var.get_type())

    def test_we_know_the_type_of_catched_multiple_excepts(self):
        code = 'class MyError(Exception):\n    pass\n' \
               'try:\n    raise MyError()\n' \
               'except (MyError, Exception) as e:\n    pass\n'
        mod = libutils.get_string_module(self.project, code)
        my_error = mod['MyError'].get_object()
        e_var = mod['e'].get_object()
        self.assertEqual(my_error, e_var.get_type())

    def test_using_property_as_decorators(self):
        code = 'class A(object):\n    pass\n' \
               'class B(object):\n' \
               '    @property\n    def f(self):\n        return A()\n' \
               'b = B()\nvar = b.f\n'
        mod = libutils.get_string_module(self.project, code)
        var = mod['var'].get_object()
        a = mod['A'].get_object()
        self.assertEqual(a, var.get_type())

    def test_using_property_as_decorators_and_passing_parameter(self):
        code = 'class B(object):\n' \
               '    @property\n    def f(self):\n        return self\n' \
               'b = B()\nvar = b.f\n'
        mod = libutils.get_string_module(self.project, code)
        var = mod['var'].get_object()
        a = mod['B'].get_object()
        self.assertEqual(a, var.get_type())


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ObjectInferTest))
    return result


if __name__ == '__main__':
    unittest.main()
