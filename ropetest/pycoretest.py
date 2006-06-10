import os
import unittest

from ropetest import testutils
from rope.pycore import PyObject, ModuleNotFoundException
from rope.project import Project

class PyElementHierarchyTest(unittest.TestCase):

    def setUp(self):
        super(PyElementHierarchyTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(PyElementHierarchyTest, self).tearDown()

    def test_simple_module(self):
        self.project.create_module(self.project.get_root_folder(), 'mod')
        result = self.pycore.get_module('mod')
        self.assertEquals(PyObject.get_base_type('Module'), result.type)
        self.assertEquals(0, len(result.get_attributes()))
    
    def test_nested_modules(self):
        pkg = self.project.create_package(self.project.get_root_folder(), 'pkg')
        mod = self.project.create_module(pkg, 'mod')
        package = self.pycore.get_module('pkg')
        self.assertEquals(PyObject.get_base_type('Module'), package.type)
        self.assertEquals(1, len(package.get_attributes()))
        module = package.get_attributes()['mod']
        self.assertEquals(PyObject.get_base_type('Module'), module.get_type())

    def test_package(self):
        pkg = self.project.create_package(self.project.get_root_folder(), 'pkg')
        mod = self.project.create_module(pkg, 'mod')
        result = self.pycore.get_module('pkg')
        self.assertEquals(PyObject.get_base_type('Module'), result.type)
        
    def test_simple_class(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    pass\n')
        mod_element = self.pycore.get_module('mod')
        result = mod_element.get_attributes()['SampleClass']
        self.assertEquals(PyObject.get_base_type('Type'), result.get_type())

    def test_simple_function(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('def sample_function():\n    pass\n')
        mod_element = self.pycore.get_module('mod')
        result = mod_element.get_attributes()['sample_function']
        self.assertEquals(PyObject.get_base_type('Function'), result.get_type())

    def test_class_methods(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    def sample_method(self):\n        pass\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.get_attributes()['SampleClass']
        self.assertEquals(1, len(sample_class.get_attributes()))
        method = sample_class.get_attributes()['sample_method']
        self.assertEquals(PyObject.get_base_type('Function'), method.get_type())

    def test_global_variables(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('var = 10')
        mod_element = self.pycore.get_module('mod')
        result = mod_element.get_attributes()['var']
        
    def test_class_variables(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    var = 10\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.get_attributes()['SampleClass']
        var = sample_class.get_attributes()['var']
        
    def test_class_attributes_set_in_init(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    def __init__(self):\n        self.var = 20\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.get_attributes()['SampleClass']
        var = sample_class.get_attributes()['var']
        
    def test_classes_inside_other_classes(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    class InnerClass(object):\n        pass\n\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.get_attributes()['SampleClass']
        var = sample_class.get_attributes()['InnerClass']
        self.assertEquals(PyObject.get_base_type('Type'), var.get_type())

    def test_non_existant_module(self):
        try:
            self.pycore.get_module('mod')
            self.fail('And exception should have been raised')
        except ModuleNotFoundException:
            pass

    def test_imported_names(self):
        self.project.create_module(self.project.get_root_folder(), 'mod1')
        mod = self.project.create_module(self.project.get_root_folder(), 'mod2')
        mod.write('import mod1\n')
        module = self.pycore.get_module('mod2')
        imported_sys = module.get_attributes()['mod1']
        self.assertEquals(PyObject.get_base_type('Module'), imported_sys.get_type())

    def test_importing_out_of_project_names(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('import sys\n')
        module = self.pycore.get_module('mod')
        imported_sys = module.get_attributes()['sys']
        self.assertEquals(PyObject.get_base_type('Module'), imported_sys.get_type())

    def test_imported_as_names(self):
        self.project.create_module(self.project.get_root_folder(), 'mod1')
        mod = self.project.create_module(self.project.get_root_folder(), 'mod2')
        mod.write('import mod1 as my_import\n')
        module = self.pycore.get_module('mod2')
        imported_mod = module.get_attributes()['my_import']
        self.assertEquals(PyObject.get_base_type('Module'), imported_mod.get_type())

    def test_get_string_module(self):
        mod = self.pycore.get_string_module('class Sample(object):\n    pass\n')
        sample_class = mod.get_attributes()['Sample']
        self.assertEquals(PyObject.get_base_type('Type'), sample_class.get_type())

    def test_parameter_info_for_functions(self):
        mod = self.pycore.get_string_module('def sample_function(param1, param2=10,' +
                                            ' *param3, **param4):\n    pass')
        sample_function = mod.get_attributes()['sample_function']
        self.assertEquals(['param1', 'param2', 'param3', 'param4'], sample_function.object.parameters)

class PyCoreInProjectsTest(unittest.TestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.project_root = 'sample_project'
        os.mkdir(self.project_root)
        self.project = Project(self.project_root)
        samplemod = self.project.create_module(self.project.get_root_folder(), 'samplemod')
        samplemod.write("class SampleClass(object):\n    def sample_method():\n        pass" + \
                        "\n\ndef sample_func():\n    pass\nsample_var = 10\n" + \
                        "\ndef _underlined_func():\n    pass\n\n" )
        package = self.project.create_package(self.project.get_root_folder(), 'package')
        nestedmod = self.project.create_module(package, 'nestedmod')
        self.pycore = self.project.get_pycore()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(self.__class__, self).tearDown()

    def test_simple_import(self):
        mod = self.pycore.get_string_module('import samplemod\n')
        samplemod = mod.get_attributes()['samplemod']
        self.assertEquals(PyObject.get_base_type('Module'), samplemod.get_type())

    def test_from_import_class(self):
        mod = self.pycore.get_string_module('from samplemod import SampleClass\n')
        result = mod.get_attributes()['SampleClass']
        self.assertEquals(PyObject.get_base_type('Type'), result.get_type())
        self.assertTrue('sample_func' not in mod.get_attributes())

    def test_from_import_star(self):
        mod = self.pycore.get_string_module('from samplemod import *\n')
        self.assertEquals(PyObject.get_base_type('Type'), mod.get_attributes()['SampleClass'].get_type())
        self.assertEquals(PyObject.get_base_type('Function'), mod.get_attributes()['sample_func'].get_type())
        self.assertTrue(mod.get_attributes()['sample_var'] is not None)

    def test_from_import_star_not_imporing_underlined(self):
        mod = self.pycore.get_string_module('from samplemod import *')
        self.assertTrue('_underlined_func' not in mod.get_attributes())

    def test_from_package_import_mod(self):
        mod = self.pycore.get_string_module('from package import nestedmod\n')
        self.assertEquals(PyObject.get_base_type('Module'), mod.get_attributes()['nestedmod'].get_type())

    def test_from_package_import_star(self):
        mod = self.pycore.get_string_module('from package import *\nnest')
        self.assertTrue('nestedmod' not in mod.get_attributes())

    def test_unknown_when_module_cannot_be_found(self):
        mod = self.pycore.get_string_module('from doesnotexist import nestedmod\n')
        self.assertTrue('nestedmod' in mod.get_attributes())

    def test_from_import_function(self):
        scope = self.pycore.get_string_scope('def f():\n    from samplemod import SampleClass\n')
        self.assertEquals(PyObject.get_base_type('Type'), 
                          scope.get_scopes()[0].get_names()['SampleClass'].get_type())

    def test_circular_imports(self):
        mod1 = self.project.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.project.create_module(self.project.get_root_folder(), 'mod2')
        mod1.write('import mod2\n')
        mod2.write('import mod1\n')
        module1 = self.pycore.get_module('mod1')

    def test_multi_dot_imports(self):
        pkg = self.project.create_package(self.project.get_root_folder(), 'pkg')
        pkg_mod = self.project.create_module(pkg, 'mod')
        pkg_mod.write('def sample_func():\n    pass\n')
        mod = self.pycore.get_string_module('import pkg.mod\n')
        self.assertTrue('pkg' in mod.get_attributes())
        self.assertTrue('sample_func' in 
                        mod.get_attributes()['pkg'].get_attributes()['mod'].get_attributes())
        
    def test_multi_dot_imports2(self):
        pkg = self.project.create_package(self.project.get_root_folder(), 'pkg')
        mod1 = self.project.create_module(pkg, 'mod1')
        mod2 = self.project.create_module(pkg, 'mod2')
        mod = self.pycore.get_string_module('import pkg.mod1\nimport pkg.mod2\n')
        package = mod.get_attributes()['pkg']
        self.assertEquals(2, len(package.get_attributes()))
        self.assertTrue('mod1' in package.get_attributes() and
                        'mod2' in package.get_attributes())
        
    def test_multi_dot_imports3(self):
        pkg1 = self.project.create_package(self.project.get_root_folder(), 'pkg1')
        pkg2 = self.project.create_package(pkg1, 'pkg2')
        mod1 = self.project.create_module(pkg2, 'mod1')
        mod2 = self.project.create_module(pkg2, 'mod2')
        mod = self.pycore.get_string_module('import pkg1.pkg2.mod1\nimport pkg1.pkg2.mod2\n')
        package1 = mod.get_attributes()['pkg1']
        package2 = package1.get_attributes()['pkg2']
        self.assertEquals(2, len(package2.get_attributes()))
        self.assertTrue('mod1' in package2.get_attributes() and
                        'mod2' in package2.get_attributes())
        
    def test_invalidating_cache_after_resource_change(self):
        module = self.project.create_module(self.project.get_root_folder(), 'mod')
        module.write('import sys\n')
        mod1 = self.pycore.get_module('mod')
        self.assertTrue('var' not in mod1.get_attributes())
        module.write('var = 10\n')
        mod2 = self.pycore.get_module('mod')
        self.assertTrue('var' in mod2.get_attributes())

    def test_from_import_nonexistant_module(self):
        mod = self.pycore.get_string_module('from doesnotexistmod import DoesNotExistClass\n')
        self.assertTrue('DoesNotExistClass' in mod.get_attributes())
        self.assertEquals(PyObject.get_base_type('Unknown'),
                          mod.get_attributes()['DoesNotExistClass'].get_type())

    def test_from_import_nonexistant_name(self):
        mod = self.pycore.get_string_module('from samplemod import DoesNotExistClass\n')
        self.assertTrue('DoesNotExistClass' in mod.get_attributes())
        self.assertEquals(PyObject.get_base_type('Unknown'),
                          mod.get_attributes()['DoesNotExistClass'].get_type())


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
        sample_func = scope.get_names()['sample_func']
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
                          scope.get_scopes()[0].get_names()['SampleClass'].get_type())

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
        self.assertEquals(1, scope.get_lineno())
        self.assertEquals(2, sample_func_scope.get_lineno())

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
        self.assertEquals(PyObject.get_base_type('Function'), scope.lookup('sample_func').get_type())
        sample_func_scope = scope.get_scopes()[0]
        self.assertTrue(sample_func_scope.lookup('var1') is not None)


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(PyElementHierarchyTest))
    result.addTests(unittest.makeSuite(PyCoreInProjectsTest))
    result.addTests(unittest.makeSuite(PyCoreScopesTest))
    return result

if __name__ == '__main__':
    unittest.main()
