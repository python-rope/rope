import unittest

from rope.base.project import Project
import rope.base.builtins
from ropetest import testutils
from rope.base.oi import dynamicoi

class ObjectInferTest(unittest.TestCase):

    def setUp(self):
        super(ObjectInferTest, self).setUp()
        self.project_root = 'sampleproject'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(ObjectInferTest, self).tearDown()

    def test_simple_type_inferencing(self):
        scope = self.pycore.get_string_scope('class Sample(object):\n    pass\na_var = Sample()\n')
        sample_class = scope.get_name('Sample').get_object()
        a_var = scope.get_name('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_simple_type_inferencing_classes_defined_in_holding_scope(self):
        scope = self.pycore.get_string_scope('class Sample(object):\n    pass\n' +
                                             'def a_func():\n    a_var = Sample()\n')
        sample_class = scope.get_name('Sample').get_object()
        a_var = scope.get_name('a_func').get_object().\
                get_scope().get_name('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_simple_type_inferencing_classes_in_class_methods(self):
        code = 'class Sample(object):\n    pass\n' \
               'class Another(object):\n' \
               '    def a_method():\n        a_var = Sample()\n'
        scope = self.pycore.get_string_scope(code)
        sample_class = scope.get_name('Sample').get_object()
        another_class = scope.get_name('Another').get_object()
        a_var = another_class.get_attribute('a_method').\
                get_object().get_scope().get_name('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_simple_type_inferencing_class_attributes(self):
        code = 'class Sample(object):\n    pass\n' \
               'class Another(object):\n' \
               '    def __init__(self):\n        self.a_var = Sample()\n'
        scope = self.pycore.get_string_scope(code)
        sample_class = scope.get_name('Sample').get_object()
        another_class = scope.get_name('Another').get_object()
        a_var = another_class.get_attribute('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_simple_type_inferencing_for_in_class_assignments(self):
        scope = self.pycore.get_string_scope('class Sample(object):\n    pass\n' +
                                             'class Another(object):\n    an_attr = Sample()\n')
        sample_class = scope.get_name('Sample').get_object()
        another_class = scope.get_name('Another').get_object()
        an_attr = another_class.get_attribute('an_attr').get_object()
        self.assertEquals(sample_class, an_attr.get_type())

    def test_simple_type_inferencing_for_chained_assignments(self):
        mod = 'class Sample(object):\n    pass\n' \
              'copied_sample = Sample'
        mod_scope = self.project.get_pycore().get_string_scope(mod)
        sample_class = mod_scope.get_name('Sample')
        copied_sample = mod_scope.get_name('copied_sample')
        self.assertEquals(sample_class.get_object(),
                          copied_sample.get_object())

    def test_following_chained_assignments_avoiding_circles(self):
        mod = 'class Sample(object):\n    pass\n' \
              'sample_class = Sample\n' \
              'sample_class = sample_class\n'
        mod_scope = self.project.get_pycore().get_string_scope(mod)
        sample_class = mod_scope.get_name('Sample')
        sample_class_var = mod_scope.get_name('sample_class')
        self.assertEquals(sample_class.get_object(),
                          sample_class_var.get_object())

    def test_function_returned_object_static_type_inference1(self):
        src = 'class Sample(object):\n    pass\n' \
              'def a_func():\n    return Sample\n' \
              'a_var = a_func()\n'
        scope = self.project.get_pycore().get_string_scope(src)
        sample_class = scope.get_name('Sample')
        a_var = scope.get_name('a_var')
        self.assertEquals(sample_class.get_object(), a_var.get_object())

    def test_function_returned_object_static_type_inference2(self):
        src = 'class Sample(object):\n    pass\n' \
              'def a_func():\n    return Sample()\n' \
              'a_var = a_func()\n'
        scope = self.project.get_pycore().get_string_scope(src)
        sample_class = scope.get_name('Sample').get_object()
        a_var = scope.get_name('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_recursive_function_returned_object_static_type_inference(self):
        src = 'class Sample(object):\n    pass\n' \
              'def a_func():\n' \
              '    if True:\n        return Sample()\n' \
              '    else:\n        return a_func()\n' \
              'a_var = a_func()\n'
        scope = self.project.get_pycore().get_string_scope(src)
        sample_class = scope.get_name('Sample').get_object()
        a_var = scope.get_name('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_function_returned_object_using_call_special_function_static_type_inference(self):
        src = 'class Sample(object):\n' \
              '    def __call__(self):\n        return Sample\n' \
              'sample = Sample()\na_var = sample()'
        scope = self.project.get_pycore().get_string_scope(src)
        sample_class = scope.get_name('Sample')
        a_var = scope.get_name('a_var')
        self.assertEquals(sample_class.get_object(), a_var.get_object())

    def test_list_type_inferencing(self):
        src = 'class Sample(object):\n    pass\na_var = [Sample()]\n'
        scope = self.pycore.get_string_scope(src)
        sample_class = scope.get_name('Sample').get_object()
        a_var = scope.get_name('a_var').get_object()
        self.assertNotEquals(sample_class, a_var.get_type())

    def test_attributed_object_inference(self):
        src = 'class Sample(object):\n' \
              '    def __init__(self):\n        self.a_var = None\n' \
              '    def set(self):\n        self.a_var = Sample()\n'
        scope = self.pycore.get_string_scope(src)
        sample_class = scope.get_name('Sample').get_object()
        a_var = sample_class.get_attribute('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_getting_property_attributes(self):
        src = 'class A(object):\n    pass\n' \
              'def f(*args):\n    return A()\n' \
              'class B(object):\n    p = property(f)\n' \
              'a_var = B().p\n'
        pymod = self.pycore.get_string_module(src)
        a_class = pymod.get_attribute('A').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(a_class, a_var.get_type())

    def test_getting_property_attributes_with_method_getters(self):
        src = 'class A(object):\n    pass\n' \
              'class B(object):\n    def p_get(self):\n        return A()\n' \
              '    p = property(p_get)\n' \
              'a_var = B().p\n'
        pymod = self.pycore.get_string_module(src)
        a_class = pymod.get_attribute('A').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(a_class, a_var.get_type())

    def test_lambda_functions(self):
        mod = self.pycore.get_string_module(
            'class C(object):\n    pass\n'
            'l = lambda: C()\na_var = l()')
        c_class = mod.get_attribute('C').get_object()
        a_var = mod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_mixing_subscript_with_tuple_assigns(self):
        mod = self.pycore.get_string_module(
            'class C(object):\n    attr = 0\n'
            'd = {}\nd[0], b = (0, C())\n')
        c_class = mod.get_attribute('C').get_object()
        a_var = mod.get_attribute('b').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_mixing_ass_attr_with_tuple_assignment(self):
        mod = self.pycore.get_string_module(
            'class C(object):\n    attr = 0\n'
            'c = C()\nc.attr, b = (0, C())\n')
        c_class = mod.get_attribute('C').get_object()
        a_var = mod.get_attribute('b').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_mixing_slice_with_tuple_assigns(self):
        mod = self.pycore.get_string_module(
            'class C(object):\n    attr = 0\n'
            'd = [None] * 3\nd[0:2], b = ((0,), C())\n')
        c_class = mod.get_attribute('C').get_object()
        a_var = mod.get_attribute('b').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_nested_tuple_assignments(self):
        mod = self.pycore.get_string_module(
            'class C1(object):\n    pass\nclass C2(object):\n    pass\n'
            'a, (b, c) = (C1(), (C2(), C1()))\n')
        c1_class = mod.get_attribute('C1').get_object()
        c2_class = mod.get_attribute('C2').get_object()
        a_var = mod.get_attribute('a').get_object()
        b_var = mod.get_attribute('b').get_object()
        c_var = mod.get_attribute('c').get_object()
        self.assertEquals(c1_class, a_var.get_type())
        self.assertEquals(c2_class, b_var.get_type())
        self.assertEquals(c1_class, c_var.get_type())


class DynamicOITest(unittest.TestCase):

    def setUp(self):
        super(DynamicOITest, self).setUp()
        self.project_root = 'sampleproject'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(DynamicOITest, self).tearDown()

    def test_simple_dti(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'def a_func(arg):\n    return arg\n' \
               'a_var = a_func(a_func)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        self.assertEquals(pymod.get_attribute('a_func').get_object(),
                          pymod.get_attribute('a_var').get_object())

    def test_module_dti(self):
        mod1 = self.pycore.create_module(self.project.root, 'mod1')
        mod2 = self.pycore.create_module(self.project.root, 'mod2')
        code = 'import mod1\ndef a_func(arg):\n    return arg\n' \
               'a_var = a_func(mod1)\n'
        mod2.write(code)
        self.pycore.run_module(mod2).wait_process()
        pymod2 = self.pycore.resource_to_pyobject(mod2)
        self.assertEquals(self.pycore.resource_to_pyobject(mod1),
                          pymod2.get_attribute('a_var').get_object())

    def test_class_from_another_module_dti(self):
        mod1 = self.pycore.create_module(self.project.root, 'mod1')
        mod2 = self.pycore.create_module(self.project.root, 'mod2')
        code1 = 'class AClass(object):\n    pass\n'
        code2 = 'from mod1 import AClass\n' \
               '\ndef a_func(arg):\n    return arg\n' \
               'a_var = a_func(AClass)\n'
        mod1.write(code1)
        mod2.write(code2)
        self.pycore.run_module(mod2).wait_process()
        pymod1 = self.pycore.resource_to_pyobject(mod1)
        pymod2 = self.pycore.resource_to_pyobject(mod2)
        self.assertEquals(pymod2.get_attribute('AClass').get_object(),
                          pymod2.get_attribute('a_var').get_object())


    def test_class_dti(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class AClass(object):\n    pass\n' \
               '\ndef a_func(arg):\n    return arg\n' \
               'a_var = a_func(AClass)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        self.assertEquals(pymod.get_attribute('AClass').get_object(),
                          pymod.get_attribute('a_var').get_object())

    def test_instance_dti(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class AClass(object):\n    pass\n' \
               '\ndef a_func(arg):\n    return arg()\n' \
               'a_var = a_func(AClass)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        self.assertEquals(pymod.get_attribute('AClass').get_object(),
                          pymod.get_attribute('a_var').get_object().get_type())

    def test_method_dti(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class AClass(object):\n    def a_method(self, arg):\n        return arg()\n' \
               'an_instance = AClass()\n' \
               'a_var = an_instance.a_method(AClass)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        self.assertEquals(pymod.get_attribute('AClass').get_object(),
                          pymod.get_attribute('a_var').get_object().get_type())

    def test_function_argument_dti(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'def a_func(arg):\n    pass\n' \
               'a_func(a_func)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pyscope = self.pycore.resource_to_pyobject(mod).get_scope()
        self.assertEquals(pyscope.get_name('a_func').get_object(),
                          pyscope.get_scopes()[0].get_name('arg').get_object())

    def test_classes_with_the_same_name(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'def a_func(arg):\n    class AClass(object):\n        pass\n    return arg\n' \
               'class AClass(object):\n    pass\n' \
               'a_var = a_func(AClass)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        self.assertEquals(pymod.get_attribute('AClass').get_object(),
                          pymod.get_attribute('a_var').get_object())

    def test_nested_classes(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'def a_func():\n    class AClass(object):\n        pass\n    return AClass\n' \
               'def another_func(arg):\n    return arg\n' \
               'a_var = another_func(a_func())\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pyscope = self.pycore.resource_to_pyobject(mod).get_scope()
        self.assertEquals(pyscope.get_scopes()[0].get_name('AClass').get_object(),
                          pyscope.get_name('a_var').get_object())

    def test_function_argument_dti2(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'def a_func(arg, a_builtin_type):\n    pass\n' \
               'a_func(a_func, [])\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pyscope = self.pycore.resource_to_pyobject(mod).get_scope()
        self.assertEquals(pyscope.get_name('a_func').get_object(),
                          pyscope.get_scopes()[0].get_name('arg').get_object())

    def test_dti_and_concluded_data_invalidation(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'def a_func(arg):\n    return arg\n' \
               'a_var = a_func(a_func)\n'
        mod.write(code)
        pymod = self.pycore.resource_to_pyobject(mod)
        pymod.get_attribute('a_var').get_object()
        self.pycore.run_module(mod).wait_process()
        self.assertEquals(pymod.get_attribute('a_func').get_object(),
                          pymod.get_attribute('a_var').get_object())

    def test_list_objects_and_dynamicoi(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class C(object):\n    pass\ndef a_func(arg):\n    return arg\n' \
               'a_var = a_func([C()])[0]\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_for_loops_and_dynamicoi(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class C(object):\n    pass\ndef a_func(arg):\n    return arg\n' \
               'for c in a_func([C()]):\n    a_var = c\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_dict_objects_and_dynamicoi(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class C(object):\n    pass\n' \
               'def a_func(arg):\n    return arg\n' \
               'a_var = a_func({1: C()})[1]\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_dict_keys_and_dynamicoi(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class C(object):\n    pass\n' \
               'def a_func(arg):\n    return arg\n' \
               'a_var = a_func({C(): 1}).keys()[0]\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_dict_keys_and_dynamicoi(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'def a_func(arg):\n    return arg\n' \
               'a, b = a_func((C1(), C2()))\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        c1_class = pymod.get_attribute('C1').get_object()
        c2_class = pymod.get_attribute('C2').get_object()
        a_var = pymod.get_attribute('a').get_object()
        b_var = pymod.get_attribute('b').get_object()
        self.assertEquals(c1_class, a_var.get_type())
        self.assertEquals(c2_class, b_var.get_type())

    def test_strs_and_dynamicoi(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'def a_func(arg):\n    return arg\n' \
               'a_var = a_func("hey")\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertTrue(isinstance(a_var.get_type(), rope.base.builtins.Str))

    def test_textual_transformations(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class C(object):\n    pass\ndef f():\n    pass\na_var = C()\n' \
               'a_list = [C()]\na_str = "hey"\n'
        mod.write(code)
        to_pyobject = dynamicoi._TextualToPyObject(self.project)
        to_textual = dynamicoi._PyObjectToTextual(self.project)
        pymod = self.pycore.resource_to_pyobject(mod)
        def complex_to_textual(pyobject):
            return to_textual.transform(
                to_pyobject.transform(to_textual.transform(pyobject)))
        for name in ('C', 'f', 'a_var', 'a_list', 'a_str'):
            var = pymod.get_attribute(name).get_object()
            self.assertEquals(to_textual.transform(var), complex_to_textual(var))
        self.assertEquals(to_textual.transform(pymod), complex_to_textual(pymod))

    def test_arguments_with_keywords(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'def a_func(arg):\n    return arg\n' \
               'a = a_func(arg=C1())\nb = a_func(arg=C2())\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        c1_class = pymod.get_attribute('C1').get_object()
        c2_class = pymod.get_attribute('C2').get_object()
        a_var = pymod.get_attribute('a').get_object()
        b_var = pymod.get_attribute('b').get_object()
        self.assertEquals(c1_class, a_var.get_type())
        self.assertEquals(c2_class, b_var.get_type())

    def test_a_function_with_different_returns(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'def a_func(arg):\n    return arg\n' \
               'a = a_func(C1())\nb = a_func(C2())\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        c1_class = pymod.get_attribute('C1').get_object()
        c2_class = pymod.get_attribute('C2').get_object()
        a_var = pymod.get_attribute('a').get_object()
        b_var = pymod.get_attribute('b').get_object()
        self.assertEquals(c1_class, a_var.get_type())
        self.assertEquals(c2_class, b_var.get_type())

    def test_a_function_with_different_returns2(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'def a_func(p):\n    if p == C1:\n        return C1()\n' \
               '    else:\n        return C2()\n' \
               'a = a_func(C1)\nb = a_func(C2)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        c1_class = pymod.get_attribute('C1').get_object()
        c2_class = pymod.get_attribute('C2').get_object()
        a_var = pymod.get_attribute('a').get_object()
        b_var = pymod.get_attribute('b').get_object()
        self.assertEquals(c1_class, a_var.get_type())
        self.assertEquals(c2_class, b_var.get_type())

    def test_ignoring_star_args(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'def a_func(p, *args):\n    if p == C1:\n        return C1()\n' \
               '    else:\n        return C2()\n' \
               'a = a_func(C1, 1)\nb = a_func(C2, 2)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        c1_class = pymod.get_attribute('C1').get_object()
        c2_class = pymod.get_attribute('C2').get_object()
        a_var = pymod.get_attribute('a').get_object()
        b_var = pymod.get_attribute('b').get_object()
        self.assertEquals(c1_class, a_var.get_type())
        self.assertEquals(c2_class, b_var.get_type())

    def test_ignoring_double_star_args(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'def a_func(p, *kwds, **args):\n    if p == C1:\n        return C1()\n' \
               '    else:\n        return C2()\n' \
               'a = a_func(C1, kwd=1)\nb = a_func(C2, kwd=2)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        c1_class = pymod.get_attribute('C1').get_object()
        c2_class = pymod.get_attribute('C2').get_object()
        a_var = pymod.get_attribute('a').get_object()
        b_var = pymod.get_attribute('b').get_object()
        self.assertEquals(c1_class, a_var.get_type())
        self.assertEquals(c2_class, b_var.get_type())


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ObjectInferTest))
    result.addTests(unittest.makeSuite(DynamicOITest))
    return result

if __name__ == '__main__':
    unittest.main()
