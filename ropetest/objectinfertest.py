import unittest

from rope.project import Project
from ropetest import testutils

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
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        code = 'def a_func(arg):\n    return arg\n' \
               'a_var = a_func(a_func)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        self.assertEquals(pymod.get_attribute('a_func').get_object(),
                          pymod.get_attribute('a_var').get_object())

    def test_module_dti(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        code = 'import mod1\ndef a_func(arg):\n    return arg\n' \
               'a_var = a_func(mod1)\n'
        mod2.write(code)
        self.pycore.run_module(mod2).wait_process()
        pymod2 = self.pycore.resource_to_pyobject(mod2)
        self.assertEquals(self.pycore.resource_to_pyobject(mod1),
                          pymod2.get_attribute('a_var').get_object())

    def test_class_from_another_module_dti(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
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
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        code = 'class AClass(object):\n    pass\n' \
               '\ndef a_func(arg):\n    return arg\n' \
               'a_var = a_func(AClass)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        self.assertEquals(pymod.get_attribute('AClass').get_object(),
                          pymod.get_attribute('a_var').get_object())

    def test_instance_dti(self):
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        code = 'class AClass(object):\n    pass\n' \
               '\ndef a_func(arg):\n    return arg()\n' \
               'a_var = a_func(AClass)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        self.assertEquals(pymod.get_attribute('AClass').get_object(),
                          pymod.get_attribute('a_var').get_object().get_type())

    def test_method_dti(self):
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        code = 'class AClass(object):\n    def a_method(self, arg):\n        return arg()\n' \
               'an_instance = AClass()\n' \
               'a_var = an_instance.a_method(AClass)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        self.assertEquals(pymod.get_attribute('AClass').get_object(),
                          pymod.get_attribute('a_var').get_object().get_type())

    def test_function_arguement_dti(self):
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        code = 'def a_func(arg):\n    pass\n' \
               'a_func(a_func)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pyscope = self.pycore.resource_to_pyobject(mod).get_scope()
        self.assertEquals(pyscope.get_name('a_func').get_object(),
                          pyscope.get_scopes()[0].get_name('arg').get_object())

    def test_classes_with_the_same_name(self):
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        code = 'def a_func(arg):\n    class AClass(object):\n        pass\n    return arg\n' \
               'class AClass(object):\n    pass\n' \
               'a_var = a_func(AClass)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        self.assertEquals(pymod.get_attribute('AClass').get_object(),
                          pymod.get_attribute('a_var').get_object())

    def test_nested_classes(self):
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        code = 'def a_func():\n    class AClass(object):\n        pass\n    return AClass\n' \
               'def another_func(arg):\n    return arg\n' \
               'a_var = another_func(a_func())\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pyscope = self.pycore.resource_to_pyobject(mod).get_scope()
        self.assertEquals(pyscope.get_scopes()[0].get_name('AClass').get_object(),
                          pyscope.get_name('a_var').get_object())

    def test_function_arguement_dti(self):
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        code = 'def a_func(arg, a_builtin_type):\n    pass\n' \
               'a_func(a_func, [])\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pyscope = self.pycore.resource_to_pyobject(mod).get_scope()
        self.assertEquals(pyscope.get_name('a_func').get_object(),
                          pyscope.get_scopes()[0].get_name('arg').get_object())
        

class CartesianProductDynamicOITest(unittest.TestCase):

    def setUp(self):
        super(CartesianProductDynamicOITest, self).setUp()
        self.project_root = 'sampleproject'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()
        common = self.pycore.create_module(self.project.get_root_folder(), 'common')
        common.write('class AClass(object):\n    pass\n\n'
                     'class AnotherClass(object):\n    pass\n')

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(CartesianProductDynamicOITest, self).tearDown()
    
    def xxx_test_simple_case(self):
        code = 'from common import AClass, AnotherClass\n\n' \
               'def a_func(arg):\n' \
               '    if isinstance(arg, AnotherClass):\n        return AClass\n' \
               '    else:\n        return AnotherClass\n' \
               'a_var = a_func(AnotherClass)\n' \
               'another_var = a_func(AClass)\n'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.pycore.resource_to_pyobject(mod)
        self.assertEquals(pymod.get_attribute('AnotherClass').get_object(),
                          pymod.get_attribute('a_var').get_object())
        self.assertEquals(pymod.get_attribute('AClass').get_object(),
                          pymod.get_attribute('another_var').get_object())


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ObjectInferTest))
    result.addTests(unittest.makeSuite(DynamicOITest))
    result.addTests(unittest.makeSuite(CartesianProductDynamicOITest))
    return result

if __name__ == '__main__':
    unittest.main()
