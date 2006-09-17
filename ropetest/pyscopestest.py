import unittest

from rope.pycore import PyObject
from rope.project import Project
from ropetest import testutils


class PyCoreScopesTest(unittest.TestCase):

    def setUp(self):
        super(PyCoreScopesTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(PyCoreScopesTest, self).tearDown()

    def test_simple_scope(self):
        scope = self.pycore.get_string_scope('def sample_func():\n    pass\n')
        sample_func = scope.get_name('sample_func').get_object()
        self.assertEquals(PyObject.get_base_type('Function'), sample_func.get_type())

    def test_simple_function_scope(self):
        scope = self.pycore.get_string_scope('def sample_func():\n    a = 10\n')
        self.assertEquals(1, len(scope.get_scopes()))
        sample_func_scope = scope.get_scopes()[0]
        self.assertEquals(1, len(sample_func_scope.get_names()))
        self.assertEquals(0, len(sample_func_scope.get_scopes()))

    def test_classes_inside_function_scopes(self):
        scope = self.pycore.get_string_scope('def sample_func():\n' +
                                             '    class SampleClass(object):\n        pass\n')
        self.assertEquals(1, len(scope.get_scopes()))
        sample_func_scope = scope.get_scopes()[0]
        self.assertEquals(PyObject.get_base_type('Type'), 
                          scope.get_scopes()[0].
                          get_name('SampleClass').get_object().get_type())

    def test_simple_class_scope(self):
        scope = self.pycore.get_string_scope('class SampleClass(object):\n' +
                                             '    def f(self):\n        var = 10\n')
        self.assertEquals(1, len(scope.get_scopes()))
        sample_class_scope = scope.get_scopes()[0]
        self.assertEquals(0, len(sample_class_scope.get_names()))
        self.assertEquals(1, len(sample_class_scope.get_scopes()))
        f_in_class = sample_class_scope.get_scopes()[0]
        self.assertTrue('var' in f_in_class.get_names())

    def test_get_lineno(self):
        scope = self.pycore.get_string_scope('\ndef sample_func():\n    a = 10\n')
        self.assertEquals(1, len(scope.get_scopes()))
        sample_func_scope = scope.get_scopes()[0]
        self.assertEquals(1, scope.get_start())
        self.assertEquals(2, sample_func_scope.get_start())

    def test_scope_kind(self):
        scope = self.pycore.get_string_scope('class SampleClass(object):\n    pass\n' +
                                             'def sample_func():\n    pass\n')
        sample_class_scope = scope.get_scopes()[0]
        sample_func_scope = scope.get_scopes()[1]
        self.assertEquals('Module', scope.get_kind())
        self.assertEquals('Class', sample_class_scope.get_kind())
        self.assertEquals('Function', sample_func_scope.get_kind())

    def test_function_parameters_in_scope_names(self):
        scope = self.pycore.get_string_scope('def sample_func(param):\n    a = 10\n')
        sample_func_scope = scope.get_scopes()[0]
        self.assertTrue('param' in sample_func_scope.get_names())

    def test_get_names_contains_only_names_defined_in_a_scope(self):
        scope = self.pycore.get_string_scope('var1 = 10\ndef sample_func(param):\n    var2 = 20\n')
        sample_func_scope = scope.get_scopes()[0]
        self.assertTrue('var1' not in sample_func_scope.get_names())

    def test_scope_lookup(self):
        scope = self.pycore.get_string_scope('var1 = 10\ndef sample_func(param):\n    var2 = 20\n')
        self.assertTrue(scope.lookup('var2') is None)
        self.assertEquals(PyObject.get_base_type('Function'),
                          scope.lookup('sample_func').get_object().get_type())
        sample_func_scope = scope.get_scopes()[0]
        self.assertTrue(sample_func_scope.lookup('var1') is not None)

    def test_function_scopes(self):
        scope = self.pycore.get_string_scope('def func():\n    var = 10\n')
        func_scope = scope.get_scopes()[0]
        self.assertTrue('var' in func_scope.get_names())

    def test_function_scopes_classes(self):
        scope = self.pycore.get_string_scope('def func():\n    class Sample(object):\n        pass\n')
        func_scope = scope.get_scopes()[0]
        self.assertTrue('Sample' in func_scope.get_names())

    def test_function_getting_scope(self):
        mod = self.pycore.get_string_module('def func():    var = 10\n')
        func_scope = mod.get_attribute('func').get_object().get_scope()
        self.assertTrue('var' in func_scope.get_names())

    def test_scopes_in_function_scopes(self):
        scope = self.pycore.get_string_scope('def func():\n    def inner():\n        var = 10\n')
        func_scope = scope.get_scopes()[0]
        inner_scope = func_scope.get_scopes()[0]
        self.assertTrue('var' in inner_scope.get_names())


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(PyCoreScopesTest))
    return result


if __name__ == '__main__':
    unittest.main()
