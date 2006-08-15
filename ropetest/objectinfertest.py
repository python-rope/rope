import unittest

from rope.project import Project
from ropetest import testutils

class ObjectInferTest(unittest.TestCase):

    def setUp(self):
        super(ObjectInferTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(ObjectInferTest, self).tearDown()

    def test_simple_type_inferencing(self):
        scope = self.pycore.get_string_scope('class Sample(object):\n    pass\na_var = Sample()\n')
        sample_class = scope.get_names()['Sample'].get_object()
        a_var = scope.get_names()['a_var']
        self.assertEquals(sample_class, a_var.get_type())
        
    def test_simple_type_inferencing_classes_defined_in_holding_scope(self):
        scope = self.pycore.get_string_scope('class Sample(object):\n    pass\n' +
                                        'def a_func():\n    a_var = Sample()\n')
        sample_class = scope.get_names()['Sample'].get_object()
        a_var = scope.get_names()['a_func'].get_object().get_scope().get_names()['a_var']
        self.assertEquals(sample_class, a_var.get_type())
        
    def test_simple_type_inferencing_classes_in_class_methods(self):
        scope = self.pycore.get_string_scope('class Sample(object):\n    pass\n' +
                                             'class Another(object):\n' + 
                                             '    def a_method():\n        a_var = Sample()\n')
        sample_class = scope.get_names()['Sample'].get_object()
        another_class = scope.get_names()['Another']
        a_var = another_class.get_attributes()['a_method'].get_object().get_scope().get_names()['a_var']
        self.assertEquals(sample_class, a_var.get_type())
        
    def test_simple_type_inferencing_class_attributes(self):
        scope = self.pycore.get_string_scope('class Sample(object):\n    pass\n' +
                                             'class Another(object):\n' + 
                                             '    def __init__(self):\n        self.a_var = Sample()\n')
        sample_class = scope.get_names()['Sample'].get_object()
        another_class = scope.get_names()['Another']
        a_var = another_class.get_attributes()['a_var']
        self.assertEquals(sample_class, a_var.get_type())

    def test_simple_type_inferencing_for_in_class_assignments(self):
        scope = self.pycore.get_string_scope('class Sample(object):\n    pass\n' +
                                             'class Another(object):\n    an_attr = Sample()\n')
        sample_class = scope.get_names()['Sample'].get_object()
        another_class = scope.get_names()['Another'].get_object()
        an_attr = another_class.get_attributes()['an_attr']
        self.assertEquals(sample_class, an_attr.get_type())

    def test_simple_type_inferencing_for_chained_assignments(self):
        mod = 'class Sample(object):\n    pass\n' \
              'copied_sample = Sample'
        mod_scope = self.project.get_pycore().get_string_scope(mod)
        sample_class = mod_scope.get_names()['Sample']
        copied_sample = mod_scope.get_names()['copied_sample']
        self.assertEquals(sample_class.get_object(), 
                          copied_sample.get_object())

    def test_following_chained_assignments_avoiding_circles(self):
        mod = 'class Sample(object):\n    pass\n' \
              'sample_class = Sample\n' \
              'sample_class = sample_class\n'
        mod_scope = self.project.get_pycore().get_string_scope(mod)
        sample_class = mod_scope.get_names()['Sample']
        sample_class_var = mod_scope.get_names()['sample_class']
        self.assertEquals(sample_class.get_object(), 
                          sample_class_var.get_object())

    def test_function_returned_object_static_type_inference1(self):
        src = 'class Sample(object):\n    pass\n' \
              'def a_func():\n    return Sample\n' \
              'a_var = a_func()\n'
        scope = self.project.get_pycore().get_string_scope(src)
        sample_class = scope.get_names()['Sample']
        a_var = scope.get_names()['a_var']
        self.assertEquals(sample_class.get_object(), a_var.get_object())

    def test_function_returned_object_static_type_inference2(self):
        src = 'class Sample(object):\n    pass\n' \
              'def a_func():\n    return Sample()\n' \
              'a_var = a_func()\n'
        scope = self.project.get_pycore().get_string_scope(src)
        sample_class = scope.get_names()['Sample']
        a_var = scope.get_names()['a_var']
        self.assertEquals(sample_class.get_object(), a_var.get_type())

    def test_recursive_function_returned_object_static_type_inference(self):
        src = 'class Sample(object):\n    pass\n' \
              'def a_func():\n' \
              '    if True:\n        return Sample()\n' \
              '    else:\n        return a_func()\n' \
              'a_var = a_func()\n'
        scope = self.project.get_pycore().get_string_scope(src)
        sample_class = scope.get_names()['Sample']
        a_var = scope.get_names()['a_var']
        self.assertEquals(sample_class.get_object(), a_var.get_type())

    def test_function_returned_object_using_call_special_function_static_type_inference(self):
        src = 'class Sample(object):\n' \
              '    def __call__(self):\n        return Sample\n' \
              'sample = Sample()\na_var = sample()'
        scope = self.project.get_pycore().get_string_scope(src)
        sample_class = scope.get_names()['Sample']
        a_var = scope.get_names()['a_var']
        self.assertEquals(sample_class.get_object(), a_var.get_object())

    def test_list_type_inferencing(self):
        src = 'class Sample(object):\n    pass\na_var = [Sample()]\n'
        scope = self.pycore.get_string_scope(src)
        sample_class = scope.get_names()['Sample'].get_object()
        a_var = scope.get_names()['a_var']
        self.assertNotEquals(sample_class, a_var.get_type())
        

def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ObjectInferTest))
    return result

if __name__ == '__main__':
    unittest.main()
