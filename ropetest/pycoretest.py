import os
import unittest

from ropetest import testutils
from rope.pycore import PyCore, PyType, ModuleNotFoundException
from rope.project import Project

class PyElementHierarchyTest(unittest.TestCase):

    def setUp(self):
        super(PyElementHierarchyTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = PyCore(self.project)

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(PyElementHierarchyTest, self).tearDown()

    def test_simple_module(self):
        self.project.create_module(self.project.get_root_folder(), 'mod')
        result = self.pycore.get_module('mod')
        self.assertEquals(PyType.get_type('Module'), result.type)
        self.assertEquals(0, len(result.attributes))
    
    def test_nested_modules(self):
        pkg = self.project.create_package(self.project.get_root_folder(), 'pkg')
        mod = self.project.create_module(pkg, 'mod')
        package = self.pycore.get_module('pkg')
        self.assertEquals(PyType.get_type('Module'), package.type)
        self.assertEquals(1, len(package.attributes))
        module = package.attributes['mod']
        self.assertEquals(PyType.get_type('Module'), module.get_type())

    def test_package(self):
        pkg = self.project.create_package(self.project.get_root_folder(), 'pkg')
        mod = self.project.create_module(pkg, 'mod')
        result = self.pycore.get_module('pkg')
        self.assertEquals(PyType.get_type('Module'), result.type)
        
    def test_simple_class(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    pass\n')
        mod_element = self.pycore.get_module('mod')
        result = mod_element.attributes['SampleClass']
        self.assertEquals(PyType.get_type('Type'), result.get_type())

    def test_simple_function(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('def sample_function():\n    pass\n')
        mod_element = self.pycore.get_module('mod')
        result = mod_element.attributes['sample_function']
        self.assertEquals(PyType.get_type('Function'), result.get_type())

    def test_class_methods(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    def sample_method(self):\n        pass\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.attributes['SampleClass']
        self.assertEquals(1, len(sample_class.get_attributes()))
        method = sample_class.get_attributes()['sample_method']
        self.assertEquals(PyType.get_type('Function'), method.get_type())

    def test_global_variables(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('var = 10')
        mod_element = self.pycore.get_module('mod')
        result = mod_element.attributes['var']
        
    def test_class_variables(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    var = 10\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.attributes['SampleClass']
        var = sample_class.get_attributes()['var']
        
    def test_class_attributes_set_in_init(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    def __init__(self):\n        self.var = 20\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.attributes['SampleClass']
        var = sample_class.get_attributes()['var']
        
    def test_classes_inside_other_classes(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    class InnerClass(object):\n        pass\n\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.attributes['SampleClass']
        var = sample_class.get_attributes()['InnerClass']
        self.assertEquals(PyType.get_type('Type'), var.get_type())

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
        imported_sys = module.attributes['mod1']
        self.assertEquals(PyType.get_type('Module'), imported_sys.get_type())

    def test_importing_out_of_project_names(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('import sys\n')
        module = self.pycore.get_module('mod')
        imported_sys = module.attributes['sys']
        self.assertEquals(PyType.get_type('Module'), imported_sys.get_type())

    def test_imported_as_names(self):
        self.project.create_module(self.project.get_root_folder(), 'mod1')
        mod = self.project.create_module(self.project.get_root_folder(), 'mod2')
        mod.write('import mod1 as my_import\n')
        module = self.pycore.get_module('mod2')
        imported_mod = module.attributes['my_import']
        self.assertEquals(PyType.get_type('Module'), imported_mod.get_type())

    def test_get_string_module(self):
        mod = self.pycore.get_string_module('class Sample(object):\n    pass\n')
        sample_class = mod.attributes['Sample']
        self.assertEquals(PyType.get_type('Type'), sample_class.get_type())


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
        self.pycore = PyCore(self.project)

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(self.__class__, self).tearDown()

    def test_simple_import(self):
        mod = self.pycore.get_string_module('import samplemod\n')
        samplemod = mod.attributes['samplemod']
        self.assertEquals(PyType.get_type('Module'), samplemod.get_type())

    def test_from_import_class(self):
        mod = self.pycore.get_string_module('from samplemod import SampleClass\n')
        result = mod.attributes['SampleClass']
        self.assertEquals(PyType.get_type('Type'), result.get_type())
        self.assertTrue('sample_func' not in mod.attributes)

    def test_from_import_star(self):
        mod = self.pycore.get_string_module('from samplemod import *\n')
        self.assertEquals(PyType.get_type('Type'), mod.attributes['SampleClass'].get_type())
        self.assertEquals(PyType.get_type('Function'), mod.attributes['sample_func'].get_type())
        self.assertTrue(mod.attributes['sample_var'] is not None)

    def test_from_import_star_not_imporing_underlined(self):
        mod = self.pycore.get_string_module('from samplemod import *')
        self.assertTrue('_underlined_func' not in mod.attributes)

    def test_from_package_import_mod(self):
        mod = self.pycore.get_string_module('from package import nestedmod\n')
        self.assertEquals(PyType.get_type('Module'), mod.attributes['nestedmod'].get_type())

    def test_from_package_import_star(self):
        mod = self.pycore.get_string_module('from package import *\nnest')
        self.assertTrue('nestedmod' not in mod.attributes)

    def test_unknown_when_module_cannot_be_found(self):
        mod = self.pycore.get_string_module('from doesnotexist import nestedmod\n')
        self.assertTrue('nestedmod' in mod.attributes)


class PyCoreScopesTest(unittest.TestCase):

    def setUp(self):
        super(PyCoreScopesTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = PyCore(self.project)

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(PyCoreScopesTest, self).tearDown()

    def test_simple_scope(self):
        scope = self.pycore.get_string_scope('def sample_func():\n    pass\n')
        self.assertTrue('sample_func' in scope.get_names())

    # TODO: These are related to scopes
    def xxx_test_from_import_function(self):
        code = 'from samplemod import sample_func\nsample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('sample_func', 'function', result)

    # TODO: These are related to scopes
    def xxx_test_from_imports_inside_functions(self):
        code = 'def f():\n    from samplemod import SampleClass\n    Sample'
        result = self.assist.assist(code, len(code))
        self.assert_completion_in_result('SampleClass', 'class', result)


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(PyElementHierarchyTest))
    result.addTests(unittest.makeSuite(PyCoreInProjectsTest))
    result.addTests(unittest.makeSuite(PyCoreScopesTest))
    return result

if __name__ == '__main__':
    unittest.main()
