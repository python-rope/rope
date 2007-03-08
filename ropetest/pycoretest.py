import os
import sys
import unittest

from rope.base.project import Project
from rope.base.pycore import ModuleNotFoundError
from rope.base.pyobjects import get_base_type
from ropetest import testutils


class PyCoreTest(unittest.TestCase):

    def setUp(self):
        super(PyCoreTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(PyCoreTest, self).tearDown()

    def test_simple_module(self):
        self.pycore.create_module(self.project.root, 'mod')
        result = self.pycore.get_module('mod')
        self.assertEquals(get_base_type('Module'), result.type)
        self.assertEquals(0, len(result.get_attributes()))

    def test_nested_modules(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod = self.pycore.create_module(pkg, 'mod')
        package = self.pycore.get_module('pkg')
        self.assertEquals(get_base_type('Module'), package.get_type())
        self.assertEquals(1, len(package.get_attributes()))
        module = package.get_attribute('mod').get_object()
        self.assertEquals(get_base_type('Module'), module.get_type())

    def test_package(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod = self.pycore.create_module(pkg, 'mod')
        result = self.pycore.get_module('pkg')
        self.assertEquals(get_base_type('Module'), result.type)

    def test_simple_class(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('class SampleClass(object):\n    pass\n')
        mod_element = self.pycore.get_module('mod')
        result = mod_element.get_attribute('SampleClass').get_object()
        self.assertEquals(get_base_type('Type'), result.get_type())

    def test_simple_function(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('def sample_function():\n    pass\n')
        mod_element = self.pycore.get_module('mod')
        result = mod_element.get_attribute('sample_function').get_object()
        self.assertEquals(get_base_type('Function'), result.get_type())

    def test_class_methods(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('class SampleClass(object):\n    def sample_method(self):\n        pass\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.get_attribute('SampleClass').get_object()
        self.assertEquals(1, len(sample_class.get_attributes()))
        method = sample_class.get_attribute('sample_method').get_object()
        self.assertEquals(get_base_type('Function'), method.get_type())

    def test_global_variables(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('var = 10')
        mod_element = self.pycore.get_module('mod')
        result = mod_element.get_attribute('var')

    def test_class_variables(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('class SampleClass(object):\n    var = 10\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.get_attribute('SampleClass').get_object()
        var = sample_class.get_attribute('var')

    def test_class_attributes_set_in_init(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('class SampleClass(object):\n    def __init__(self):\n        self.var = 20\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.get_attribute('SampleClass').get_object()
        var = sample_class.get_attribute('var')

    def test_classes_inside_other_classes(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('class SampleClass(object):\n    class InnerClass(object):\n        pass\n\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.get_attribute('SampleClass').get_object()
        var = sample_class.get_attribute('InnerClass').get_object()
        self.assertEquals(get_base_type('Type'), var.get_type())

    @testutils.assert_raises(ModuleNotFoundError)
    def test_non_existant_module(self):
        self.pycore.get_module('doesnotexistmodule')

    def test_imported_names(self):
        self.pycore.create_module(self.project.root, 'mod1')
        mod = self.pycore.create_module(self.project.root, 'mod2')
        mod.write('import mod1\n')
        module = self.pycore.get_module('mod2')
        imported_sys = module.get_attribute('mod1').get_object()
        self.assertEquals(get_base_type('Module'), imported_sys.get_type())

    def test_imported_as_names(self):
        self.pycore.create_module(self.project.root, 'mod1')
        mod = self.pycore.create_module(self.project.root, 'mod2')
        mod.write('import mod1 as my_import\n')
        module = self.pycore.get_module('mod2')
        imported_mod = module.get_attribute('my_import').get_object()
        self.assertEquals(get_base_type('Module'), imported_mod.get_type())

    def test_get_string_module(self):
        mod = self.pycore.get_string_module('class Sample(object):\n    pass\n')
        sample_class = mod.get_attribute('Sample').get_object()
        self.assertEquals(get_base_type('Type'), sample_class.get_type())

    def test_get_string_module_with_extra_spaces(self):
        mod = self.pycore.get_string_module('a = 10\n    ')

    def test_parameter_info_for_functions(self):
        mod = self.pycore.get_string_module('def sample_function(param1, param2=10,' +
                                            ' *param3, **param4):\n    pass')
        sample_function = mod.get_attribute('sample_function')
        self.assertEquals(['param1', 'param2', 'param3', 'param4'],
                          sample_function.get_object().get_param_names())

    # FIXME: Not found modules
    def xxx_test_not_found_module_is_module(self):
        mod = self.pycore.get_string_module('import doesnotexist\n')
        self.assertEquals(get_base_type('Module'),
                          mod.get_attribute('doesnotexist').
                          get_object().get_type())

    def test_mixing_scopes_and_objects_hierarchy(self):
        mod = self.pycore.get_string_module('var = 200\n')
        scope = mod.get_scope()
        self.assertTrue('var' in scope.get_names())

    def test_inheriting_base_class_attributes(self):
        mod = self.pycore.get_string_module('class Base(object):\n    def method(self):\n        pass\n' +
                                             'class Derived(Base):\n    pass\n')
        derived = mod.get_attribute('Derived').get_object()
        self.assertTrue('method' in derived.get_attributes())
        self.assertEquals(get_base_type('Function'),
                          derived.get_attribute('method').get_object().get_type())

    def test_inheriting_multiple_base_class_attributes(self):
        code = 'class Base1(object):\n    def method1(self):\n        pass\n' \
               'class Base2(object):\n    def method2(self):\n        pass\n' \
               'class Derived(Base1, Base2):\n    pass\n'
        mod = self.pycore.get_string_module(code)
        derived = mod.get_attribute('Derived').get_object()
        self.assertTrue('method1' in derived.get_attributes())
        self.assertTrue('method2' in derived.get_attributes())

    def test_inheriting_multiple_base_class_attributes_with_the_same_name(self):
        code = 'class Base1(object):\n    def method(self):\n        pass\n' \
               'class Base2(object):\n    def method(self):\n        pass\n' \
               'class Derived(Base1, Base2):\n    pass\n'
        mod = self.pycore.get_string_module(code)
        base1 = mod.get_attribute('Base1').get_object()
        derived = mod.get_attribute('Derived').get_object()
        self.assertEquals(base1.get_attribute('method').get_object(),
                          derived.get_attribute('method').get_object())

    def test_inheriting_unknown_base_class(self):
        mod = self.pycore.get_string_module('class Derived(NotFound):\n' \
                                            '    def f(self):\n        pass\n')
        derived = mod.get_attribute('Derived').get_object()
        self.assertTrue('f' in derived.get_attributes())

    def test_module_creation(self):
        new_module = self.pycore.create_module(self.project.root, 'module')
        self.assertFalse(new_module.is_folder())
        self.assertEquals(self.project.get_resource('module.py'), new_module)

    def test_packaged_module_creation(self):
        package = self.project.root.create_folder('package')
        new_module = self.pycore.create_module(self.project.root, 'package.module')
        self.assertEquals(self.project.get_resource('package/module.py'), new_module)

    def test_packaged_module_creation_with_nested_src(self):
        src = self.project.root.create_folder('src')
        package = src.create_folder('pkg')
        new_module = self.pycore.create_module(src, 'pkg.mod')
        self.assertEquals(self.project.get_resource('src/pkg/mod.py'), new_module)

    def test_package_creation(self):
        new_package = self.pycore.create_package(self.project.root, 'pkg')
        self.assertTrue(new_package.is_folder())
        self.assertEquals(self.project.get_resource('pkg'), new_package)
        self.assertEquals(self.project.get_resource('pkg/__init__.py'),
                          new_package.get_child('__init__.py'));

    def test_nested_package_creation(self):
        package = self.pycore.create_package(self.project.root, 'pkg1')
        nested_package = self.pycore.create_package(self.project.root, 'pkg1.pkg2')
        self.assertEquals(self.project.get_resource('pkg1/pkg2'), nested_package)

    def test_packaged_package_creation_with_nested_src(self):
        src = self.project.root.create_folder('src')
        package = self.pycore.create_package(src, 'pkg1')
        nested_package = self.pycore.create_package(src, 'pkg1.pkg2')
        self.assertEquals(self.project.get_resource('src/pkg1/pkg2'), nested_package)

    def test_find_module(self):
        src = self.project.root.create_folder('src')
        samplemod = self.pycore.create_module(src, 'samplemod')
        found_module = self.pycore.find_module('samplemod')
        self.assertEquals(samplemod, found_module)

    def test_find_nested_module(self):
        src = self.project.root.create_folder('src')
        samplepkg = self.pycore.create_package(src, 'samplepkg')
        samplemod = self.pycore.create_module(samplepkg, 'samplemod')
        found_module = self.pycore.find_module('samplepkg.samplemod')
        self.assertEquals(samplemod, found_module)

    def test_find_multiple_module(self):
        src = self.project.root.create_folder('src')
        samplemod1 = self.pycore.create_module(src, 'samplemod')
        samplemod2 = self.pycore.create_module(self.project.root, 'samplemod')
        test = self.project.root.create_folder('test')
        samplemod3 = self.pycore.create_module(test, 'samplemod')
        found_module = self.pycore.find_module('samplemod')
        self.assertTrue(samplemod1 == found_module or
                        samplemod2 == found_module or
                        samplemod3 == found_module)

    def test_find_module_packages(self):
        src = self.project.root
        samplepkg = self.pycore.create_package(src, 'samplepkg')
        found_module = self.pycore.find_module('samplepkg')
        self.assertEquals(samplepkg, found_module)

    def test_find_module_when_module_and_package_with_the_same_name(self):
        src = self.project.root
        samplemod = self.pycore.create_module(src, 'sample')
        samplepkg = self.pycore.create_package(src, 'sample')
        found_module = self.pycore.find_module('sample')
        self.assertEquals(samplepkg, found_module)

    def test_getting_empty_source_folders(self):
        self.assertEquals([], self.pycore.get_source_folders())

    def test_root_source_folder(self):
        self.project.root.create_file('sample.py')
        source_folders = self.pycore.get_source_folders()
        self.assertEquals(1, len(source_folders))
        self.assertTrue(self.project.root in source_folders)

    def test_root_source_folder2(self):
        self.project.root.create_file('mod1.py')
        self.project.root.create_file('mod2.py')
        source_folders = self.pycore.get_source_folders()
        self.assertEquals(1, len(source_folders))
        self.assertTrue(self.project.root in source_folders)

    def test_src_source_folder(self):
        src = self.project.root.create_folder('src')
        src.create_file('sample.py')
        source_folders = self.pycore.get_source_folders()
        self.assertEquals(1, len(source_folders))
        self.assertTrue(self.project.get_resource('src') in source_folders)

    def test_packages(self):
        src = self.project.root.create_folder('src')
        pkg = src.create_folder('package')
        pkg.create_file('__init__.py')
        source_folders = self.pycore.get_source_folders()
        self.assertEquals(1, len(source_folders))
        self.assertTrue(src in source_folders)

    def test_multi_source_folders(self):
        src = self.project.root.create_folder('src')
        package = src.create_folder('package')
        package.create_file('__init__.py')
        test = self.project.root.create_folder('test')
        test.create_file('alltests.py')
        source_folders = self.pycore.get_source_folders()
        self.assertEquals(2, len(source_folders))
        self.assertTrue(src in source_folders)
        self.assertTrue(test in source_folders)

    def test_multi_source_folders2(self):
        mod1 = self.pycore.create_module(self.project.root, 'mod1')
        src = self.project.root.create_folder('src')
        package = self.pycore.create_package(src, 'package')
        mod2 = self.pycore.create_module(package, 'mod2')
        source_folders = self.pycore.get_source_folders()
        self.assertEquals(2, len(source_folders))
        self.assertTrue(self.project.root in source_folders and \
                        src in source_folders)

    def test_get_pyname_definition_location(self):
        mod = self.pycore.get_string_module('a_var = 20\n')
        a_var = mod.get_attribute('a_var')
        self.assertEquals((mod, 1), a_var.get_definition_location())

    def test_get_pyname_definition_location_functions(self):
        mod = self.pycore.get_string_module('def a_func():\n    pass\n')
        a_func = mod.get_attribute('a_func')
        self.assertEquals((mod, 1), a_func.get_definition_location())

    def test_get_pyname_definition_location_class(self):
        mod = self.pycore.get_string_module('class AClass(object):\n    pass\n\n')
        a_class = mod.get_attribute('AClass')
        self.assertEquals((mod, 1), a_class.get_definition_location())

    def test_get_pyname_definition_location_local_variables(self):
        mod = self.pycore.get_string_module('def a_func():\n    a_var = 10\n')
        a_func_scope = mod.get_scope().get_scopes()[0]
        a_var = a_func_scope.get_name('a_var')
        self.assertEquals((mod, 2), a_var.get_definition_location())

    def test_get_pyname_definition_location_reassigning(self):
        mod = self.pycore.get_string_module('a_var = 20\na_var=30\n')
        a_var = mod.get_attribute('a_var')
        self.assertEquals((mod, 1), a_var.get_definition_location())

    def test_get_pyname_definition_location_importes(self):
        module = self.pycore.create_module(self.project.root, 'mod')
        mod = self.pycore.get_string_module('import mod\n')
        imported_module = self.pycore.get_module('mod')
        module_pyname = mod.get_attribute('mod')
        self.assertEquals((imported_module, 1),
                          module_pyname.get_definition_location())

    def test_get_pyname_definition_location_imports(self):
        module_resource = self.pycore.create_module(self.project.root, 'mod')
        module_resource.write('\ndef a_func():\n    pass\n')
        imported_module = self.pycore.get_module('mod')
        mod = self.pycore.get_string_module('from mod import a_func\n')
        a_func = mod.get_attribute('a_func')
        self.assertEquals((imported_module, 2), a_func.get_definition_location())

    def test_get_pyname_definition_location_parameters(self):
        mod = self.pycore.get_string_module('def a_func(param1, param2):\n    a_var = param\n')
        a_func_scope = mod.get_scope().get_scopes()[0]
        param1 = a_func_scope.get_name('param1')
        self.assertEquals((mod, 1), param1.get_definition_location())
        param2 = a_func_scope.get_name('param2')
        self.assertEquals((mod, 1), param2.get_definition_location())

    def test_module_get_resource(self):
        module_resource = self.pycore.create_module(self.project.root, 'mod')
        module = self.pycore.get_module('mod')
        self.assertEquals(module_resource, module.get_resource())
        string_module = self.pycore.get_string_module('from mod import a_func\n')
        self.assertEquals(None, string_module.get_resource())

    def test_get_pyname_definition_location_class2(self):
        mod = self.pycore.get_string_module('class AClass(object):\n    def __init__(self):\n' + \
                                            '        self.an_attr = 10\n')
        a_class = mod.get_attribute('AClass').get_object()
        an_attr = a_class.get_attribute('an_attr')
        self.assertEquals((mod, 3), an_attr.get_definition_location())

    def test_import_not_found_module_get_definition_location(self):
        mod = self.pycore.get_string_module('import doesnotexist\n')
        does_not_exist = mod.get_attribute('doesnotexist')
        self.assertEquals((None, None), does_not_exist.get_definition_location())

    def test_from_not_found_module_get_definition_location(self):
        mod = self.pycore.get_string_module('from doesnotexist import Sample\n')
        sample = mod.get_attribute('Sample')
        self.assertEquals((None, None), sample.get_definition_location())

    def test_from_package_import_module_get_definition_location(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        self.pycore.create_module(pkg, 'mod')
        pkg_mod = self.pycore.get_module('pkg.mod')
        mod = self.pycore.get_string_module('from pkg import mod\n')
        imported_mod = mod.get_attribute('mod')
        self.assertEquals((pkg_mod, 1),
                          imported_mod.get_definition_location())

    def test_get_module_for_defined_pyobjects(self):
        mod = self.pycore.get_string_module('class AClass(object):\n    pass\n')
        a_class = mod.get_attribute('AClass').get_object()
        self.assertEquals(mod, a_class.get_module())

    def test_get_definition_location_for_packages(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        init_module = self.pycore.get_module('pkg.__init__')
        mod = self.pycore.get_string_module('import pkg\n')
        pkg_pyname = mod.get_attribute('pkg')
        self.assertEquals((init_module, 1), pkg_pyname.get_definition_location())

    def test_get_definition_location_for_filtered_packages(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        self.pycore.create_module(pkg, 'mod')
        init_module = self.pycore.get_module('pkg.__init__')
        mod = self.pycore.get_string_module('import pkg.mod')
        pkg_pyname = mod.get_attribute('pkg')
        self.assertEquals((init_module, 1), pkg_pyname.get_definition_location())

    def test_out_of_project_modules(self):
        scope = self.pycore.get_string_scope('import rope.base.project as project\n')
        imported_module = scope.get_name('project').get_object()
        self.assertTrue('Project' in imported_module.get_attributes())

    def test_file_encoding_reading(self):
        contents = u'# -*- coding: utf-8 -*-\n#\N{LATIN SMALL LETTER I WITH DIAERESIS}\n'
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write(contents)
        self.pycore.get_module('mod')

    def test_file_encoding_reading2(self):
        contents = 'a_var = 1\ndef a_func():\n    global a_var\n'
        mod = self.pycore.get_string_module(contents)
        global_var = mod.get_attribute('a_var')
        func_scope = mod.get_attribute('a_func').get_object().get_scope()
        local_var = func_scope.get_name('a_var')
        self.assertEquals(global_var, local_var)

    def test_not_leaking_for_vars_inside_parent_scope(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('class C(object):\n    def f(self):\n'
                  '        for my_var1, my_var2 in []:\n            pass\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        c_class = pymod.get_attribute('C').get_object()
        self.assertFalse('my_var1' in c_class.get_attributes())
        self.assertFalse('my_var2' in c_class.get_attributes())

    def test_not_leaking_for_vars_inside_parent_scope2(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('class C(object):\n    def f(self):\n'
                  '        for my_var in []:\n            pass\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        c_class = pymod.get_attribute('C').get_object()
        self.assertFalse('my_var' in c_class.get_attributes())

    def test_not_leaking_tuple_assigned_names_inside_parent_scope(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('class C(object):\n    def f(self):\n'
                  '        var1, var2 = range(2)\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        c_class = pymod.get_attribute('C').get_object()
        self.assertFalse('var1' in c_class.get_attributes())

    @testutils.run_only_for_25
    def test_with_statement_variables(self):
        code = 'import threading\nwith threading.lock() as var:    pass\n'
        if sys.version_info < (2, 6, 0):
            code = 'from __future__ import with_statement\n' + code
        pymod = self.pycore.get_string_module(code)
        self.assertTrue('var' in pymod.get_attributes())

    @testutils.run_only_for_25
    def test_with_statement_variables_and_tuple_assignment(self):
        code = 'class A(object):\n    def __enter__(self):        return (1, 2)\n'\
               '    def __exit__(self, type, value, tb):\n        pass\n'\
               'with A() as (a, b):    pass\n'
        if sys.version_info < (2, 6, 0):
            code = 'from __future__ import with_statement\n' + code
        pymod = self.pycore.get_string_module(code)
        self.assertTrue('a' in pymod.get_attributes())
        self.assertTrue('b' in pymod.get_attributes())

    @testutils.run_only_for_25
    def test_with_statement_variable_type(self):
        code = 'class A(object):\n    def __enter__(self):        return self\n'\
               '    def __exit__(self, type, value, tb):\n        pass\n'\
               'with A() as var:    pass\n'
        if sys.version_info < (2, 6, 0):
            code = 'from __future__ import with_statement\n' + code
        pymod = self.pycore.get_string_module(code)
        a_class = pymod.get_attribute('A').get_object()
        var = pymod.get_attribute('var').get_object()
        self.assertEquals(a_class, var.get_type())


class PyCoreInProjectsTest(unittest.TestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        os.mkdir(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()
        samplemod = self.pycore.create_module(self.project.root, 'samplemod')
        samplemod.write("class SampleClass(object):\n    def sample_method():\n        pass" + \
                        "\n\ndef sample_func():\n    pass\nsample_var = 10\n" + \
                        "\ndef _underlined_func():\n    pass\n\n")
        package = self.pycore.create_package(self.project.root, 'package')
        nestedmod = self.pycore.create_module(package, 'nestedmod')

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(self.__class__, self).tearDown()

    def test_simple_import(self):
        mod = self.pycore.get_string_module('import samplemod\n')
        samplemod = mod.get_attribute('samplemod').get_object()
        self.assertEquals(get_base_type('Module'), samplemod.get_type())

    def test_from_import_class(self):
        mod = self.pycore.get_string_module('from samplemod import SampleClass\n')
        result = mod.get_attribute('SampleClass').get_object()
        self.assertEquals(get_base_type('Type'), result.get_type())
        self.assertTrue('sample_func' not in mod.get_attributes())

    def test_from_import_star(self):
        mod = self.pycore.get_string_module('from samplemod import *\n')
        self.assertEquals(get_base_type('Type'),
                          mod.get_attribute('SampleClass').get_object().get_type())
        self.assertEquals(get_base_type('Function'),
                          mod.get_attribute('sample_func').get_object().get_type())
        self.assertTrue(mod.get_attribute('sample_var') is not None)

    def test_from_import_star_overwriting(self):
        code = 'from samplemod import *\n' \
               'class SampleClass(object):\n    pass\n'
        mod = self.pycore.get_string_module(code)
        samplemod = self.pycore.get_module('samplemod')
        sample_class = samplemod.get_attribute('SampleClass').get_object()
        self.assertNotEquals(sample_class,
                             mod.get_attributes()['SampleClass'].get_object())

    def test_from_import_star_not_imporing_underlined(self):
        mod = self.pycore.get_string_module('from samplemod import *')
        self.assertTrue('_underlined_func' not in mod.get_attributes())

    def test_from_package_import_mod(self):
        mod = self.pycore.get_string_module('from package import nestedmod\n')
        self.assertEquals(get_base_type('Module'),
                          mod.get_attribute('nestedmod').get_object().get_type())

    def test_from_package_import_star(self):
        mod = self.pycore.get_string_module('from package import *\nnest')
        self.assertTrue('nestedmod' not in mod.get_attributes())

    def test_unknown_when_module_cannot_be_found(self):
        mod = self.pycore.get_string_module('from doesnotexist import nestedmod\n')
        self.assertTrue('nestedmod' in mod.get_attributes())

    def test_from_import_function(self):
        scope = self.pycore.get_string_scope('def f():\n    from samplemod import SampleClass\n')
        self.assertEquals(get_base_type('Type'),
                          scope.get_scopes()[0].get_name('SampleClass').
                          get_object().get_type())

    def test_circular_imports(self):
        mod1 = self.pycore.create_module(self.project.root, 'mod1')
        mod2 = self.pycore.create_module(self.project.root, 'mod2')
        mod1.write('import mod2\n')
        mod2.write('import mod1\n')
        module1 = self.pycore.get_module('mod1')

    def test_circular_imports2(self):
        mod1 = self.pycore.create_module(self.project.root, 'mod1')
        mod2 = self.pycore.create_module(self.project.root, 'mod2')
        mod1.write('from mod2 import Sample2\nclass Sample1(object):\n    pass\n')
        mod2.write('from mod1 import Sample1\nclass Sample2(object):\n    pass\n')
        module1 = self.pycore.get_module('mod1').get_attributes()

    def test_multi_dot_imports(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        pkg_mod = self.pycore.create_module(pkg, 'mod')
        pkg_mod.write('def sample_func():\n    pass\n')
        mod = self.pycore.get_string_module('import pkg.mod\n')
        self.assertTrue('pkg' in mod.get_attributes())
        self.assertTrue('sample_func' in
                        mod.get_attribute('pkg').get_object().get_attribute('mod').
                        get_object().get_attributes())

    def test_multi_dot_imports2(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod = self.pycore.get_string_module('import pkg.mod1\nimport pkg.mod2\n')
        package = mod.get_attribute('pkg').get_object()
        self.assertEquals(2, len(package.get_attributes()))
        self.assertTrue('mod1' in package.get_attributes() and
                        'mod2' in package.get_attributes())

    def test_multi_dot_imports3(self):
        pkg1 = self.pycore.create_package(self.project.root, 'pkg1')
        pkg2 = self.pycore.create_package(pkg1, 'pkg2')
        mod1 = self.pycore.create_module(pkg2, 'mod1')
        mod2 = self.pycore.create_module(pkg2, 'mod2')
        mod = self.pycore.get_string_module('import pkg1.pkg2.mod1\nimport pkg1.pkg2.mod2\n')
        package1 = mod.get_attribute('pkg1').get_object()
        package2 = package1.get_attribute('pkg2').get_object()
        self.assertEquals(2, len(package2.get_attributes()))
        self.assertTrue('mod1' in package2.get_attributes() and
                        'mod2' in package2.get_attributes())

    def test_multi_dot_imports_as(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod1.write('def f():\n    pass\n')
        mod = self.pycore.get_string_module('import pkg.mod1 as mod1\n')
        module = mod.get_attribute('mod1').get_object()
        self.assertTrue('f' in module.get_attributes())

    # TODO: not showing unimported names as attributes of packages
    def xxx_test_from_package_import_package(self):
        pkg1 = self.pycore.create_package(self.project.root, 'pkg1')
        pkg2 = self.pycore.create_package(pkg1, 'pkg2')
        module = self.pycore.create_module(pkg2, 'mod')
        mod = self.pycore.get_string_module('from pkg1 import pkg2\n')
        package = mod.get_attribute('pkg2')
        self.assertEquals(0, len(package.get_attributes()))

    def test_invalidating_cache_after_resource_change(self):
        module = self.pycore.create_module(self.project.root, 'mod')
        module.write('import sys\n')
        mod1 = self.pycore.get_module('mod')
        self.assertTrue('var' not in mod1.get_attributes())
        module.write('var = 10\n')
        mod2 = self.pycore.get_module('mod')
        self.assertTrue('var' in mod2.get_attributes())

    def test_invalidating_cache_after_resource_change_for_init_dot_pys(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod = self.pycore.create_module(self.project.root, 'mod')
        init_dot_py = pkg.get_child('__init__.py')
        init_dot_py.write('a_var = 10\n')
        mod.write('import pkg\n')
        pymod = self.pycore.get_module('mod')
        self.assertTrue('a_var' in pymod.get_attribute('pkg').get_object().get_attributes())
        init_dot_py.write('new_var = 10\n')
        self.assertTrue('a_var' not in pymod.get_attribute('pkg').get_object().get_attributes())

    def test_invalidating_cache_after_resource_change_for_nested_init_dot_pys(self):
        pkg1 = self.pycore.create_package(self.project.root, 'pkg1')
        pkg2 = self.pycore.create_package(pkg1, 'pkg2')
        mod = self.pycore.create_module(self.project.root, 'mod')
        init_dot_py = pkg2.get_child('__init__.py')
        init_dot_py.write('a_var = 10\n')
        mod.write('import pkg1\n')
        pymod = self.pycore.get_module('mod')
        self.assertTrue('a_var' in pymod.get_attribute('pkg1').get_object().
                        get_attribute('pkg2').get_object().get_attributes())
        init_dot_py.write('new_var = 10\n')
        self.assertTrue('a_var' not in pymod.get_attribute('pkg1').get_object().
                        get_attribute('pkg2').get_object().get_attributes())

    def test_from_import_nonexistant_module(self):
        mod = self.pycore.get_string_module('from doesnotexistmod import DoesNotExistClass\n')
        self.assertTrue('DoesNotExistClass' in mod.get_attributes())
        self.assertEquals(get_base_type('Unknown'),
                          mod.get_attribute('DoesNotExistClass').
                          get_object().get_type())

    def test_from_import_nonexistant_name(self):
        mod = self.pycore.get_string_module('from samplemod import DoesNotExistClass\n')
        self.assertTrue('DoesNotExistClass' in mod.get_attributes())
        self.assertEquals(get_base_type('Unknown'),
                          mod.get_attribute('DoesNotExistClass').
                          get_object().get_type())

    def test_not_considering_imported_names_as_sub_scopes(self):
        scope = self.pycore.get_string_scope('from samplemod import SampleClass\n')
        self.assertEquals(0, len(scope.get_scopes()))

    def test_not_considering_imported_modules_as_sub_scopes(self):
        scope = self.pycore.get_string_scope('import samplemod\n')
        self.assertEquals(0, len(scope.get_scopes()))

    def test_inheriting_dotted_base_class(self):
        mod = self.pycore.get_string_module('import samplemod\n' +
                                            'class Derived(samplemod.SampleClass):\n    pass\n')
        derived = mod.get_attribute('Derived').get_object()
        self.assertTrue('sample_method' in derived.get_attributes())

    def test_self_in_methods(self):
        scope = self.pycore.get_string_scope('class Sample(object):\n' \
                                             '    def func(self):\n        pass\n')
        sample_class = scope.get_name('Sample').get_object()
        func_scope = scope.get_scopes()[0].get_scopes()[0]
        self.assertEquals(sample_class,
                          func_scope.get_name('self').get_object().get_type())
        self.assertTrue('func' in func_scope.get_name('self').
                        get_object().get_attributes())

    def test_self_in_methods_with_decorators(self):
        scope = self.pycore.get_string_scope('class Sample(object):\n    @staticmethod\n' +
                                             '    def func(self):\n        pass\n')
        sample_class = scope.get_name('Sample').get_object()
        func_scope = scope.get_scopes()[0].get_scopes()[0]
        self.assertNotEquals(sample_class,
                             func_scope.get_name('self').get_object().get_type())

    def test_location_of_imports_when_importing(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('from samplemod import SampleClass\n')
        scope = self.pycore.get_string_scope('from mod import SampleClass\n')
        sample_class = scope.get_name('SampleClass')
        samplemod = self.pycore.get_module('samplemod')
        self.assertEquals((samplemod, 1), sample_class.get_definition_location())

    def test_nested_modules(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod = self.pycore.create_module(pkg, 'mod')
        imported_module = self.pycore.get_module('pkg.mod')
        scope = self.pycore.get_string_scope('import pkg.mod\n')
        mod_pyobject = scope.get_name('pkg').get_object().get_attribute('mod')
        self.assertEquals((imported_module, 1),
                          mod_pyobject.get_definition_location())

    def test_reading_init_dot_py(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        init_dot_py = pkg.get_child('__init__.py')
        init_dot_py.write('a_var = 1\n')
        pkg_object = self.pycore.get_module('pkg')
        self.assertTrue('a_var' in pkg_object.get_attributes())

    def test_relative_imports(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod2.write('import mod1\n')
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEquals(mod1_object, mod2_object.get_attributes()['mod1'].get_object())

    def test_relative_froms(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod1.write('def a_func():\n    pass\n')
        mod2.write('from mod1 import a_func\n')
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEquals(mod1_object.get_attribute('a_func').get_object(),
                          mod2_object.get_attribute('a_func').get_object())

    def test_relative_imports_for_string_modules(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod2.write('import mod1\n')
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.get_string_module(mod2.read(), mod2)
        self.assertEquals(mod1_object, mod2_object.get_attribute('mod1').get_object())

    def test_relative_imports_for_string_scopes(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod2.write('import mod1\n')
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_scope = self.pycore.get_string_scope(mod2.read(), mod2)
        self.assertEquals(mod1_object, mod2_scope.get_name('mod1').get_object())

    @testutils.run_only_for_25
    def test_new_style_relative_imports(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod2.write('from . import mod1\n')
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEquals(mod1_object, mod2_object.get_attribute('mod1').get_object())

    @testutils.run_only_for_25
    def test_new_style_relative_imports2(self):
        pkg = self.pycore.create_package(self.project.root, 'pkg')
        mod1 = self.pycore.create_module(self.project.root, 'mod1')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod1.write('def a_func():\n    pass\n')
        mod2.write('from ..mod1 import a_func\n')
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEquals(mod1_object.get_attribute('a_func').get_object(),
                          mod2_object.get_attribute('a_func').get_object())

    def test_invalidating_cache_for_from_imports_after_resource_change(self):
        mod1 = self.pycore.create_module(self.project.root, 'mod1')
        mod2 = self.pycore.create_module(self.project.root, 'mod2')
        mod2.write('def a_func():\n    print(1)\n')
        mod1.write('from mod2 import a_func\na_func()\n')

        pymod1 = self.pycore.get_module('mod1')
        pymod2 = self.pycore.get_module('mod2')
        self.assertEquals(pymod1.get_attribute('a_func').get_object(),
                          pymod2.get_attribute('a_func').get_object())
        mod2.write(mod2.read() + '\n')
        pymod2 = self.pycore.get_module('mod2')
        self.assertEquals(pymod1.get_attribute('a_func').get_object(),
                          pymod2.get_attribute('a_func').get_object())


class ClassHierarchyTest(unittest.TestCase):

    def setUp(self):
        super(ClassHierarchyTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(ClassHierarchyTest, self).tearDown()

    def test_empty_get_superclasses(self):
        code = 'class AClass(object):\n    pass\n'
        mod = self.pycore.get_string_module(code)
        a_class = mod.get_attribute('AClass').get_object()
        self.assertTrue(len(a_class.get_superclasses()) <= 1)

    def test_simple_get_superclasses(self):
        code = 'class A(object):\n    pass\n' \
               'class B(A):\n    pass\n'
        mod = self.pycore.get_string_module(code)
        a_class = mod.get_attribute('A').get_object()
        b_class = mod.get_attribute('B').get_object()
        self.assertEquals([a_class], b_class.get_superclasses())

    def test_get_superclasses_with_two_superclasses(self):
        code = 'class A(object):\n    pass\n' \
               'class B(object):\n    pass\n' \
               'class C(A, B):\n    pass\n'
        mod = self.pycore.get_string_module(code)
        a_class = mod.get_attribute('A').get_object()
        b_class = mod.get_attribute('B').get_object()
        c_class = mod.get_attribute('C').get_object()
        self.assertEquals([a_class, b_class], c_class.get_superclasses())

    def test_empty_get_subclasses(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('class A(object):\n    pass\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        a_class = pymod.get_attribute('A')
        self.assertEquals([], self.pycore.get_subclasses(a_class))

    def test_get_subclasses(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('class A(object):\n    pass\n\n'
                  'class B(A):\n    pass\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        a_class = pymod.get_attribute('A').get_object()
        b_class = pymod.get_attribute('B').get_object()
        self.assertEquals([b_class], self.pycore.get_subclasses(a_class))

    def test_get_subclasses_in_multiple_modules(self):
        mod1 = self.pycore.create_module(self.project.root, 'mod1')
        mod2 = self.pycore.create_module(self.project.root, 'mod2')
        mod1.write('class A(object):\n    pass\n')
        mod2.write('import mod1\nclass B(mod1.A):\n    pass\n')
        pymod1 = self.pycore.resource_to_pyobject(mod1)
        pymod2 = self.pycore.resource_to_pyobject(mod2)
        a_class = pymod1.get_attribute('A').get_object()
        b_class = pymod2.get_attribute('B').get_object()
        self.assertEquals([b_class], self.pycore.get_subclasses(a_class))

    def test_get_subclasses_reversed(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('class B(A):\n    pass\n'
                  'class A(object):\n    pass\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        a_class = pymod.get_attribute('A').get_object()
        b_class = pymod.get_attribute('B').get_object()
        self.assertEquals([b_class], self.pycore.get_subclasses(a_class))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(PyCoreTest))
    result.addTests(unittest.makeSuite(PyCoreInProjectsTest))
    result.addTests(unittest.makeSuite(ClassHierarchyTest))
    return result


if __name__ == '__main__':
    unittest.main()
