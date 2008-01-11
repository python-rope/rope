import sys
import unittest

from rope.base import exceptions
from rope.base.pycore import _TextChangeDetector
from rope.base.pyobjects import get_base_type
from ropetest import testutils


class PyCoreTest(unittest.TestCase):

    def setUp(self):
        super(PyCoreTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.get_pycore()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(PyCoreTest, self).tearDown()

    def test_simple_module(self):
        testutils.create_module(self.project, 'mod')
        result = self.pycore.get_module('mod')
        self.assertEquals(get_base_type('Module'), result.type)
        self.assertEquals(0, len(result.get_attributes()))

    def test_nested_modules(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod = testutils.create_module(self.project, 'mod', pkg)
        package = self.pycore.get_module('pkg')
        self.assertEquals(get_base_type('Module'), package.get_type())
        self.assertEquals(1, len(package.get_attributes()))
        module = package['mod'].get_object()
        self.assertEquals(get_base_type('Module'), module.get_type())

    def test_package(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod = testutils.create_module(self.project, 'mod', pkg)
        result = self.pycore.get_module('pkg')
        self.assertEquals(get_base_type('Module'), result.type)

    def test_simple_class(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('class SampleClass(object):\n    pass\n')
        mod_element = self.pycore.get_module('mod')
        result = mod_element['SampleClass'].get_object()
        self.assertEquals(get_base_type('Type'), result.get_type())

    def test_simple_function(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('def sample_function():\n    pass\n')
        mod_element = self.pycore.get_module('mod')
        result = mod_element['sample_function'].get_object()
        self.assertEquals(get_base_type('Function'), result.get_type())

    def test_class_methods(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('class SampleClass(object):\n    def sample_method(self):\n        pass\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element['SampleClass'].get_object()
        self.assertEquals(1, len(sample_class.get_attributes()))
        method = sample_class['sample_method'].get_object()
        self.assertEquals(get_base_type('Function'), method.get_type())

    def test_global_variables(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('var = 10')
        mod_element = self.pycore.get_module('mod')
        result = mod_element['var']

    def test_class_variables(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('class SampleClass(object):\n    var = 10\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element['SampleClass'].get_object()
        var = sample_class['var']

    def test_class_attributes_set_in_init(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('class SampleClass(object):\n    def __init__(self):\n        self.var = 20\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element['SampleClass'].get_object()
        var = sample_class['var']

    def test_classes_inside_other_classes(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('class SampleClass(object):\n    class InnerClass(object):\n        pass\n\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element['SampleClass'].get_object()
        var = sample_class['InnerClass'].get_object()
        self.assertEquals(get_base_type('Type'), var.get_type())

    @testutils.assert_raises(exceptions.ModuleNotFoundError)
    def test_non_existent_module(self):
        self.pycore.get_module('doesnotexistmodule')

    def test_imported_names(self):
        testutils.create_module(self.project, 'mod1')
        mod = testutils.create_module(self.project, 'mod2')
        mod.write('import mod1\n')
        module = self.pycore.get_module('mod2')
        imported_sys = module['mod1'].get_object()
        self.assertEquals(get_base_type('Module'), imported_sys.get_type())

    def test_imported_as_names(self):
        testutils.create_module(self.project, 'mod1')
        mod = testutils.create_module(self.project, 'mod2')
        mod.write('import mod1 as my_import\n')
        module = self.pycore.get_module('mod2')
        imported_mod = module['my_import'].get_object()
        self.assertEquals(get_base_type('Module'), imported_mod.get_type())

    def test_get_string_module(self):
        mod = self.pycore.get_string_module('class Sample(object):\n    pass\n')
        sample_class = mod['Sample'].get_object()
        self.assertEquals(get_base_type('Type'), sample_class.get_type())

    def test_get_string_module_with_extra_spaces(self):
        mod = self.pycore.get_string_module('a = 10\n    ')

    def test_parameter_info_for_functions(self):
        mod = self.pycore.get_string_module('def sample_function(param1, param2=10,' +
                                            ' *param3, **param4):\n    pass')
        sample_function = mod['sample_function']
        self.assertEquals(['param1', 'param2', 'param3', 'param4'],
                          sample_function.get_object().get_param_names())

    # FIXME: Not found modules
    def xxx_test_not_found_module_is_module(self):
        mod = self.pycore.get_string_module('import doesnotexist\n')
        self.assertEquals(get_base_type('Module'),
                          mod['doesnotexist'].
                          get_object().get_type())

    def test_mixing_scopes_and_objects_hierarchy(self):
        mod = self.pycore.get_string_module('var = 200\n')
        scope = mod.get_scope()
        self.assertTrue('var' in scope.get_names())

    def test_inheriting_base_class_attributes(self):
        mod = self.pycore.get_string_module('class Base(object):\n    def method(self):\n        pass\n' +
                                             'class Derived(Base):\n    pass\n')
        derived = mod['Derived'].get_object()
        self.assertTrue('method' in derived.get_attributes())
        self.assertEquals(get_base_type('Function'),
                          derived['method'].get_object().get_type())

    def test_inheriting_multiple_base_class_attributes(self):
        code = 'class Base1(object):\n    def method1(self):\n        pass\n' \
               'class Base2(object):\n    def method2(self):\n        pass\n' \
               'class Derived(Base1, Base2):\n    pass\n'
        mod = self.pycore.get_string_module(code)
        derived = mod['Derived'].get_object()
        self.assertTrue('method1' in derived.get_attributes())
        self.assertTrue('method2' in derived.get_attributes())

    def test_inheriting_multiple_base_class_attributes_with_the_same_name(self):
        code = 'class Base1(object):\n    def method(self):\n        pass\n' \
               'class Base2(object):\n    def method(self):\n        pass\n' \
               'class Derived(Base1, Base2):\n    pass\n'
        mod = self.pycore.get_string_module(code)
        base1 = mod['Base1'].get_object()
        derived = mod['Derived'].get_object()
        self.assertEquals(base1['method'].get_object(),
                          derived['method'].get_object())

    def test_inheriting_unknown_base_class(self):
        mod = self.pycore.get_string_module('class Derived(NotFound):\n' \
                                            '    def f(self):\n        pass\n')
        derived = mod['Derived'].get_object()
        self.assertTrue('f' in derived.get_attributes())

    def test_module_creation(self):
        new_module = testutils.create_module(self.project, 'module')
        self.assertFalse(new_module.is_folder())
        self.assertEquals(self.project.get_resource('module.py'), new_module)

    def test_packaged_module_creation(self):
        package = self.project.root.create_folder('package')
        new_module = testutils.create_module(self.project, 'package.module')
        self.assertEquals(self.project.get_resource('package/module.py'), new_module)

    def test_packaged_module_creation_with_nested_src(self):
        src = self.project.root.create_folder('src')
        package = src.create_folder('pkg')
        new_module = testutils.create_module(self.project, 'pkg.mod', src)
        self.assertEquals(self.project.get_resource('src/pkg/mod.py'), new_module)

    def test_package_creation(self):
        new_package = testutils.create_package(self.project, 'pkg')
        self.assertTrue(new_package.is_folder())
        self.assertEquals(self.project.get_resource('pkg'), new_package)
        self.assertEquals(self.project.get_resource('pkg/__init__.py'),
                          new_package.get_child('__init__.py'));

    def test_nested_package_creation(self):
        package = testutils.create_package(self.project, 'pkg1')
        nested_package = testutils.create_package(self.project, 'pkg1.pkg2')
        self.assertEquals(self.project.get_resource('pkg1/pkg2'), nested_package)

    def test_packaged_package_creation_with_nested_src(self):
        src = self.project.root.create_folder('src')
        package = testutils.create_package(self.project, 'pkg1', src)
        nested_package = testutils.create_package(self.project, 'pkg1.pkg2', src)
        self.assertEquals(self.project.get_resource('src/pkg1/pkg2'), nested_package)

    def test_find_module(self):
        src = self.project.root.create_folder('src')
        samplemod = testutils.create_module(self.project, 'samplemod', src)
        found_module = self.pycore.find_module('samplemod')
        self.assertEquals(samplemod, found_module)

    def test_find_nested_module(self):
        src = self.project.root.create_folder('src')
        samplepkg = testutils.create_package(self.project, 'samplepkg', src)
        samplemod = testutils.create_module(self.project, 'samplemod', samplepkg)
        found_module = self.pycore.find_module('samplepkg.samplemod')
        self.assertEquals(samplemod, found_module)

    def test_find_multiple_module(self):
        src = self.project.root.create_folder('src')
        samplemod1 = testutils.create_module(self.project, 'samplemod', src)
        samplemod2 = testutils.create_module(self.project, 'samplemod')
        test = self.project.root.create_folder('test')
        samplemod3 = testutils.create_module(self.project, 'samplemod', test)
        found_module = self.pycore.find_module('samplemod')
        self.assertTrue(samplemod1 == found_module or
                        samplemod2 == found_module or
                        samplemod3 == found_module)

    def test_find_module_packages(self):
        src = self.project.root
        samplepkg = testutils.create_package(self.project, 'samplepkg', src)
        found_module = self.pycore.find_module('samplepkg')
        self.assertEquals(samplepkg, found_module)

    def test_find_module_when_module_and_package_with_the_same_name(self):
        src = self.project.root
        samplemod = testutils.create_module(self.project, 'sample', src)
        samplepkg = testutils.create_package(self.project, 'sample', src)
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
        mod1 = testutils.create_module(self.project, 'mod1')
        src = self.project.root.create_folder('src')
        package = testutils.create_package(self.project, 'package', src)
        mod2 = testutils.create_module(self.project, 'mod2', package)
        source_folders = self.pycore.get_source_folders()
        self.assertEquals(2, len(source_folders))
        self.assertTrue(self.project.root in source_folders and \
                        src in source_folders)

    def test_get_pyname_definition_location(self):
        mod = self.pycore.get_string_module('a_var = 20\n')
        a_var = mod['a_var']
        self.assertEquals((mod, 1), a_var.get_definition_location())

    def test_get_pyname_definition_location_functions(self):
        mod = self.pycore.get_string_module('def a_func():\n    pass\n')
        a_func = mod['a_func']
        self.assertEquals((mod, 1), a_func.get_definition_location())

    def test_get_pyname_definition_location_class(self):
        mod = self.pycore.get_string_module('class AClass(object):\n    pass\n\n')
        a_class = mod['AClass']
        self.assertEquals((mod, 1), a_class.get_definition_location())

    def test_get_pyname_definition_location_local_variables(self):
        mod = self.pycore.get_string_module('def a_func():\n    a_var = 10\n')
        a_func_scope = mod.get_scope().get_scopes()[0]
        a_var = a_func_scope.get_name('a_var')
        self.assertEquals((mod, 2), a_var.get_definition_location())

    def test_get_pyname_definition_location_reassigning(self):
        mod = self.pycore.get_string_module('a_var = 20\na_var=30\n')
        a_var = mod['a_var']
        self.assertEquals((mod, 1), a_var.get_definition_location())

    def test_get_pyname_definition_location_importes(self):
        module = testutils.create_module(self.project, 'mod')
        mod = self.pycore.get_string_module('import mod\n')
        imported_module = self.pycore.get_module('mod')
        module_pyname = mod['mod']
        self.assertEquals((imported_module, 1),
                          module_pyname.get_definition_location())

    def test_get_pyname_definition_location_imports(self):
        module_resource = testutils.create_module(self.project, 'mod')
        module_resource.write('\ndef a_func():\n    pass\n')
        imported_module = self.pycore.get_module('mod')
        mod = self.pycore.get_string_module('from mod import a_func\n')
        a_func = mod['a_func']
        self.assertEquals((imported_module, 2), a_func.get_definition_location())

    def test_get_pyname_definition_location_parameters(self):
        mod = self.pycore.get_string_module('def a_func(param1, param2):\n    a_var = param\n')
        a_func_scope = mod.get_scope().get_scopes()[0]
        param1 = a_func_scope.get_name('param1')
        self.assertEquals((mod, 1), param1.get_definition_location())
        param2 = a_func_scope.get_name('param2')
        self.assertEquals((mod, 1), param2.get_definition_location())

    def test_module_get_resource(self):
        module_resource = testutils.create_module(self.project, 'mod')
        module = self.pycore.get_module('mod')
        self.assertEquals(module_resource, module.get_resource())
        string_module = self.pycore.get_string_module('from mod import a_func\n')
        self.assertEquals(None, string_module.get_resource())

    def test_get_pyname_definition_location_class2(self):
        mod = self.pycore.get_string_module('class AClass(object):\n    def __init__(self):\n' + \
                                            '        self.an_attr = 10\n')
        a_class = mod['AClass'].get_object()
        an_attr = a_class['an_attr']
        self.assertEquals((mod, 3), an_attr.get_definition_location())

    def test_import_not_found_module_get_definition_location(self):
        mod = self.pycore.get_string_module('import doesnotexist\n')
        does_not_exist = mod['doesnotexist']
        self.assertEquals((None, None), does_not_exist.get_definition_location())

    def test_from_not_found_module_get_definition_location(self):
        mod = self.pycore.get_string_module('from doesnotexist import Sample\n')
        sample = mod['Sample']
        self.assertEquals((None, None), sample.get_definition_location())

    def test_from_package_import_module_get_definition_location(self):
        pkg = testutils.create_package(self.project, 'pkg')
        testutils.create_module(self.project, 'mod', pkg)
        pkg_mod = self.pycore.get_module('pkg.mod')
        mod = self.pycore.get_string_module('from pkg import mod\n')
        imported_mod = mod['mod']
        self.assertEquals((pkg_mod, 1),
                          imported_mod.get_definition_location())

    def test_get_module_for_defined_pyobjects(self):
        mod = self.pycore.get_string_module('class AClass(object):\n    pass\n')
        a_class = mod['AClass'].get_object()
        self.assertEquals(mod, a_class.get_module())

    def test_get_definition_location_for_packages(self):
        pkg = testutils.create_package(self.project, 'pkg')
        init_module = self.pycore.get_module('pkg.__init__')
        mod = self.pycore.get_string_module('import pkg\n')
        pkg_pyname = mod['pkg']
        self.assertEquals((init_module, 1), pkg_pyname.get_definition_location())

    def test_get_definition_location_for_filtered_packages(self):
        pkg = testutils.create_package(self.project, 'pkg')
        testutils.create_module(self.project, 'mod', pkg)
        init_module = self.pycore.get_module('pkg.__init__')
        mod = self.pycore.get_string_module('import pkg.mod')
        pkg_pyname = mod['pkg']
        self.assertEquals((init_module, 1), pkg_pyname.get_definition_location())

    def test_out_of_project_modules(self):
        scope = self.pycore.get_string_scope('import rope.base.project as project\n')
        imported_module = scope.get_name('project').get_object()
        self.assertTrue('Project' in imported_module.get_attributes())

    def test_file_encoding_reading(self):
        contents = u'# -*- coding: utf-8 -*-\n#\N{LATIN SMALL LETTER I WITH DIAERESIS}\n'
        mod = testutils.create_module(self.project, 'mod')
        mod.write(contents)
        self.pycore.get_module('mod')

    def test_global_keyword(self):
        contents = 'a_var = 1\ndef a_func():\n    global a_var\n'
        mod = self.pycore.get_string_module(contents)
        global_var = mod['a_var']
        func_scope = mod['a_func'].get_object().get_scope()
        local_var = func_scope.get_name('a_var')
        self.assertEquals(global_var, local_var)

    def test_not_leaking_for_vars_inside_parent_scope(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('class C(object):\n    def f(self):\n'
                  '        for my_var1, my_var2 in []:\n            pass\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        c_class = pymod['C'].get_object()
        self.assertFalse('my_var1' in c_class.get_attributes())
        self.assertFalse('my_var2' in c_class.get_attributes())

    def test_not_leaking_for_vars_inside_parent_scope2(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('class C(object):\n    def f(self):\n'
                  '        for my_var in []:\n            pass\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        c_class = pymod['C'].get_object()
        self.assertFalse('my_var' in c_class.get_attributes())

    def test_not_leaking_tuple_assigned_names_inside_parent_scope(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('class C(object):\n    def f(self):\n'
                  '        var1, var2 = range(2)\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        c_class = pymod['C'].get_object()
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
        a_class = pymod['A'].get_object()
        var = pymod['var'].get_object()
        self.assertEquals(a_class, var.get_type())

    def test_check_for_else_block(self):
        mod = self.pycore.get_string_module('for i in range(10):\n    pass\n'
                                            'else:\n    myvar = 1\n')
        a_var = mod['myvar']
        self.assertEquals((mod, 4), a_var.get_definition_location())

    def test_check_names_defined_in_whiles(self):
        mod = self.pycore.get_string_module('while False:\n    myvar = 1\n')
        a_var = mod['myvar']
        self.assertEquals((mod, 2), a_var.get_definition_location())

    @testutils.assert_raises(exceptions.ModuleSyntaxError)
    def test_syntax_errors_in_code(self):
        mod = self.pycore.get_string_module('xyx print\n')

    def test_holding_error_location_information(self):
        try:
            mod = self.pycore.get_string_module('xyx print\n')
        except exceptions.ModuleSyntaxError, e:
            self.assertEquals(1, e.lineno)


class PyCoreInProjectsTest(unittest.TestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.get_pycore()
        samplemod = testutils.create_module(self.project, 'samplemod')
        samplemod.write("class SampleClass(object):\n    def sample_method():\n        pass" + \
                        "\n\ndef sample_func():\n    pass\nsample_var = 10\n" + \
                        "\ndef _underlined_func():\n    pass\n\n")
        package = testutils.create_package(self.project, 'package')
        nestedmod = testutils.create_module(self.project, 'nestedmod', package)

    def tearDown(self):
        testutils.remove_project(self.project)
        super(self.__class__, self).tearDown()

    def test_simple_import(self):
        mod = self.pycore.get_string_module('import samplemod\n')
        samplemod = mod['samplemod'].get_object()
        self.assertEquals(get_base_type('Module'), samplemod.get_type())

    def test_from_import_class(self):
        mod = self.pycore.get_string_module('from samplemod import SampleClass\n')
        result = mod['SampleClass'].get_object()
        self.assertEquals(get_base_type('Type'), result.get_type())
        self.assertTrue('sample_func' not in mod.get_attributes())

    def test_from_import_star(self):
        mod = self.pycore.get_string_module('from samplemod import *\n')
        self.assertEquals(get_base_type('Type'),
                          mod['SampleClass'].get_object().get_type())
        self.assertEquals(get_base_type('Function'),
                          mod['sample_func'].get_object().get_type())
        self.assertTrue(mod['sample_var'] is not None)

    def test_from_import_star_overwriting(self):
        code = 'from samplemod import *\n' \
               'class SampleClass(object):\n    pass\n'
        mod = self.pycore.get_string_module(code)
        samplemod = self.pycore.get_module('samplemod')
        sample_class = samplemod['SampleClass'].get_object()
        self.assertNotEquals(sample_class,
                             mod.get_attributes()['SampleClass'].get_object())

    def test_from_import_star_not_imporing_underlined(self):
        mod = self.pycore.get_string_module('from samplemod import *')
        self.assertTrue('_underlined_func' not in mod.get_attributes())

    def test_from_package_import_mod(self):
        mod = self.pycore.get_string_module('from package import nestedmod\n')
        self.assertEquals(get_base_type('Module'),
                          mod['nestedmod'].get_object().get_type())

    # XXX: Deciding to import everything on import start from packages
    def xxx_test_from_package_import_star(self):
        mod = self.pycore.get_string_module('from package import *\n')
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
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod1.write('import mod2\n')
        mod2.write('import mod1\n')
        module1 = self.pycore.get_module('mod1')

    def test_circular_imports2(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod1.write('from mod2 import Sample2\nclass Sample1(object):\n    pass\n')
        mod2.write('from mod1 import Sample1\nclass Sample2(object):\n    pass\n')
        module1 = self.pycore.get_module('mod1').get_attributes()

    def test_multi_dot_imports(self):
        pkg = testutils.create_package(self.project, 'pkg')
        pkg_mod = testutils.create_module(self.project, 'mod', pkg)
        pkg_mod.write('def sample_func():\n    pass\n')
        mod = self.pycore.get_string_module('import pkg.mod\n')
        self.assertTrue('pkg' in mod.get_attributes())
        self.assertTrue('sample_func' in
                        mod['pkg'].get_object()['mod'].
                        get_object().get_attributes())

    def test_multi_dot_imports2(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod1 = testutils.create_module(self.project, 'mod1', pkg)
        mod2 = testutils.create_module(self.project, 'mod2', pkg)
        mod = self.pycore.get_string_module('import pkg.mod1\nimport pkg.mod2\n')
        package = mod['pkg'].get_object()
        self.assertEquals(2, len(package.get_attributes()))
        self.assertTrue('mod1' in package.get_attributes() and
                        'mod2' in package.get_attributes())

    def test_multi_dot_imports3(self):
        pkg1 = testutils.create_package(self.project, 'pkg1')
        pkg2 = testutils.create_package(self.project, 'pkg2', pkg1)
        mod1 = testutils.create_module(self.project, 'mod1', pkg2)
        mod2 = testutils.create_module(self.project, 'mod2', pkg2)
        mod = self.pycore.get_string_module('import pkg1.pkg2.mod1\nimport pkg1.pkg2.mod2\n')
        package1 = mod['pkg1'].get_object()
        package2 = package1['pkg2'].get_object()
        self.assertEquals(2, len(package2.get_attributes()))
        self.assertTrue('mod1' in package2.get_attributes() and
                        'mod2' in package2.get_attributes())

    def test_multi_dot_imports_as(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod1 = testutils.create_module(self.project, 'mod1', pkg)
        mod1.write('def f():\n    pass\n')
        mod = self.pycore.get_string_module('import pkg.mod1 as mod1\n')
        module = mod['mod1'].get_object()
        self.assertTrue('f' in module.get_attributes())

    # TODO: not showing unimported names as attributes of packages
    def xxx_test_from_package_import_package(self):
        pkg1 = testutils.create_package(self.project, 'pkg1')
        pkg2 = testutils.create_package(self.project, 'pkg2', pkg1)
        module = testutils.create_module(self.project, 'mod', pkg2)
        mod = self.pycore.get_string_module('from pkg1 import pkg2\n')
        package = mod['pkg2']
        self.assertEquals(0, len(package.get_attributes()))

    def test_invalidating_cache_after_resource_change(self):
        module = testutils.create_module(self.project, 'mod')
        module.write('import sys\n')
        mod1 = self.pycore.get_module('mod')
        self.assertTrue('var' not in mod1.get_attributes())
        module.write('var = 10\n')
        mod2 = self.pycore.get_module('mod')
        self.assertTrue('var' in mod2.get_attributes())

    def test_invalidating_cache_after_resource_change_for_init_dot_pys(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod = testutils.create_module(self.project, 'mod')
        init_dot_py = pkg.get_child('__init__.py')
        init_dot_py.write('a_var = 10\n')
        mod.write('import pkg\n')
        pymod = self.pycore.get_module('mod')
        self.assertTrue('a_var' in pymod['pkg'].get_object().get_attributes())
        init_dot_py.write('new_var = 10\n')
        self.assertTrue('a_var' not in pymod['pkg'].get_object().get_attributes())

    def test_invalidating_cache_after_resource_change_for_nested_init_dot_pys(self):
        pkg1 = testutils.create_package(self.project, 'pkg1')
        pkg2 = testutils.create_package(self.project, 'pkg2', pkg1)
        mod = testutils.create_module(self.project, 'mod')
        init_dot_py = pkg2.get_child('__init__.py')
        init_dot_py.write('a_var = 10\n')
        mod.write('import pkg1\n')
        pymod = self.pycore.get_module('mod')
        self.assertTrue('a_var' in pymod['pkg1'].get_object()['pkg2'].get_object().get_attributes())
        init_dot_py.write('new_var = 10\n')
        self.assertTrue('a_var' not in pymod['pkg1'].get_object()['pkg2'].get_object().get_attributes())

    def test_from_import_nonexistent_module(self):
        mod = self.pycore.get_string_module('from doesnotexistmod import DoesNotExistClass\n')
        self.assertTrue('DoesNotExistClass' in mod.get_attributes())
        self.assertEquals(get_base_type('Unknown'),
                          mod['DoesNotExistClass'].
                          get_object().get_type())

    def test_from_import_nonexistent_name(self):
        mod = self.pycore.get_string_module('from samplemod import DoesNotExistClass\n')
        self.assertTrue('DoesNotExistClass' in mod.get_attributes())
        self.assertEquals(get_base_type('Unknown'),
                          mod['DoesNotExistClass'].
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
        derived = mod['Derived'].get_object()
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

    def test_none_assignments_in_classes(self):
        scope = self.pycore.get_string_scope(
            'class C(object):\n    var = ""\n'
            '    def f(self):\n        self.var += "".join([])\n')
        c_class = scope.get_name('C').get_object()
        self.assertTrue('var' in c_class.get_attributes())

    def test_self_in_methods_with_decorators(self):
        scope = self.pycore.get_string_scope('class Sample(object):\n    @staticmethod\n' +
                                             '    def func(self):\n        pass\n')
        sample_class = scope.get_name('Sample').get_object()
        func_scope = scope.get_scopes()[0].get_scopes()[0]
        self.assertNotEquals(sample_class,
                             func_scope.get_name('self').get_object().get_type())

    def test_location_of_imports_when_importing(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('from samplemod import SampleClass\n')
        scope = self.pycore.get_string_scope('from mod import SampleClass\n')
        sample_class = scope.get_name('SampleClass')
        samplemod = self.pycore.get_module('samplemod')
        self.assertEquals((samplemod, 1), sample_class.get_definition_location())

    def test_nested_modules(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod = testutils.create_module(self.project, 'mod', pkg)
        imported_module = self.pycore.get_module('pkg.mod')
        scope = self.pycore.get_string_scope('import pkg.mod\n')
        mod_pyobject = scope.get_name('pkg').get_object()['mod']
        self.assertEquals((imported_module, 1),
                          mod_pyobject.get_definition_location())

    def test_reading_init_dot_py(self):
        pkg = testutils.create_package(self.project, 'pkg')
        init_dot_py = pkg.get_child('__init__.py')
        init_dot_py.write('a_var = 1\n')
        pkg_object = self.pycore.get_module('pkg')
        self.assertTrue('a_var' in pkg_object.get_attributes())

    def test_relative_imports(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod1 = testutils.create_module(self.project, 'mod1', pkg)
        mod2 = testutils.create_module(self.project, 'mod2', pkg)
        mod2.write('import mod1\n')
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEquals(mod1_object, mod2_object.get_attributes()['mod1'].get_object())

    def test_relative_froms(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod1 = testutils.create_module(self.project, 'mod1', pkg)
        mod2 = testutils.create_module(self.project, 'mod2', pkg)
        mod1.write('def a_func():\n    pass\n')
        mod2.write('from mod1 import a_func\n')
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEquals(mod1_object['a_func'].get_object(),
                          mod2_object['a_func'].get_object())

    def test_relative_imports_for_string_modules(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod1 = testutils.create_module(self.project, 'mod1', pkg)
        mod2 = testutils.create_module(self.project, 'mod2', pkg)
        mod2.write('import mod1\n')
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.get_string_module(mod2.read(), mod2)
        self.assertEquals(mod1_object, mod2_object['mod1'].get_object())

    def test_relative_imports_for_string_scopes(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod1 = testutils.create_module(self.project, 'mod1', pkg)
        mod2 = testutils.create_module(self.project, 'mod2', pkg)
        mod2.write('import mod1\n')
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_scope = self.pycore.get_string_scope(mod2.read(), mod2)
        self.assertEquals(mod1_object, mod2_scope.get_name('mod1').get_object())

    @testutils.run_only_for_25
    def test_new_style_relative_imports(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod1 = testutils.create_module(self.project, 'mod1', pkg)
        mod2 = testutils.create_module(self.project, 'mod2', pkg)
        mod2.write('from . import mod1\n')
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEquals(mod1_object, mod2_object['mod1'].get_object())

    @testutils.run_only_for_25
    def test_new_style_relative_imports2(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2', pkg)
        mod1.write('def a_func():\n    pass\n')
        mod2.write('from ..mod1 import a_func\n')
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEquals(mod1_object['a_func'].get_object(),
                          mod2_object['a_func'].get_object())

    def test_invalidating_cache_for_from_imports_after_resource_change(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod2.write('def a_func():\n    print(1)\n')
        mod1.write('from mod2 import a_func\na_func()\n')

        pymod1 = self.pycore.get_module('mod1')
        pymod2 = self.pycore.get_module('mod2')
        self.assertEquals(pymod1['a_func'].get_object(),
                          pymod2['a_func'].get_object())
        mod2.write(mod2.read() + '\n')
        pymod2 = self.pycore.get_module('mod2')
        self.assertEquals(pymod1['a_func'].get_object(),
                          pymod2['a_func'].get_object())

    def test_invalidating_superclasses_after_change(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod1.write('class A(object):\n    def func1(self):\n        pass\n')
        mod2.write('import mod1\nclass B(mod1.A):\n    pass\n')

        b_class = self.pycore.get_module('mod2')['B'].get_object()
        self.assertTrue('func1' in b_class.get_attributes())

        mod1.write('class A(object):\n    def func2(self):\n        pass\n')
        self.assertTrue('func2' in b_class.get_attributes())

    def test_simple_module(self):
        mod = testutils.create_module(self.project, 'mod')
        pymod = self.pycore.resource_to_pyobject(mod)
        self.assertTrue(pymod.is_valid())
        mod.write('a = 1\n')
        self.assertFalse(pymod.is_valid())


class ClassHierarchyTest(unittest.TestCase):

    def setUp(self):
        super(ClassHierarchyTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.get_pycore()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(ClassHierarchyTest, self).tearDown()

    def test_empty_get_superclasses(self):
        code = 'class AClass(object):\n    pass\n'
        mod = self.pycore.get_string_module(code)
        a_class = mod['AClass'].get_object()
        self.assertTrue(len(a_class.get_superclasses()) <= 1)

    def test_simple_get_superclasses(self):
        code = 'class A(object):\n    pass\n' \
               'class B(A):\n    pass\n'
        mod = self.pycore.get_string_module(code)
        a_class = mod['A'].get_object()
        b_class = mod['B'].get_object()
        self.assertEquals([a_class], b_class.get_superclasses())

    def test_get_superclasses_with_two_superclasses(self):
        code = 'class A(object):\n    pass\n' \
               'class B(object):\n    pass\n' \
               'class C(A, B):\n    pass\n'
        mod = self.pycore.get_string_module(code)
        a_class = mod['A'].get_object()
        b_class = mod['B'].get_object()
        c_class = mod['C'].get_object()
        self.assertEquals([a_class, b_class], c_class.get_superclasses())

    def test_empty_get_subclasses(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('class A(object):\n    pass\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        a_class = pymod['A']
        self.assertEquals([], self.pycore.get_subclasses(a_class))

    def test_get_subclasses(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('class A(object):\n    pass\n\n'
                  'class B(A):\n    pass\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        a_class = pymod['A'].get_object()
        b_class = pymod['B'].get_object()
        self.assertEquals([b_class], self.pycore.get_subclasses(a_class))

    def test_get_subclasses_in_multiple_modules(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod1.write('class A(object):\n    pass\n')
        mod2.write('import mod1\nclass B(mod1.A):\n    pass\n')
        pymod1 = self.pycore.resource_to_pyobject(mod1)
        pymod2 = self.pycore.resource_to_pyobject(mod2)
        a_class = pymod1['A'].get_object()
        b_class = pymod2['B'].get_object()
        self.assertEquals([b_class], self.pycore.get_subclasses(a_class))

    def test_get_subclasses_reversed(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('class B(A):\n    pass\n'
                  'class A(object):\n    pass\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        a_class = pymod['A'].get_object()
        b_class = pymod['B'].get_object()
        self.assertEquals([b_class], self.pycore.get_subclasses(a_class))

    def test_get_subclasses_for_in_string_definitions(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('"""\nclass B(A):\n    pass\n"""\n'
                  'class A(object):\n    pass\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        a_class = pymod['A'].get_object()
        self.assertEquals([], self.pycore.get_subclasses(a_class))

    def test_get_classes_for_in_string_definitions(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('class A(object):\n    pass\n')
        self.assertEquals(1, len(self.pycore.get_classes()))
        mod.write('')
        self.assertEquals(0, len(self.pycore.get_classes()))


class TextChangeDetectorTest(unittest.TestCase):

    def test_trivial_case(self):
        detector = _TextChangeDetector('\n', '\n')
        self.assertFalse(detector.is_changed(1, 1))

    def test_one_line_change(self):
        detector = _TextChangeDetector('1\n2\n', '1\n3\n')
        self.assertFalse(detector.is_changed(1, 1))
        self.assertTrue(detector.is_changed(2, 2))

    def test_line_expansion(self):
        detector = _TextChangeDetector('1\n2\n', '1\n3\n4\n2\n')
        self.assertFalse(detector.is_changed(1, 1))
        self.assertFalse(detector.is_changed(2, 2))

    def test_line_removals(self):
        detector = _TextChangeDetector('1\n3\n4\n2\n', '1\n2\n')
        self.assertFalse(detector.is_changed(1, 1))
        self.assertTrue(detector.is_changed(2, 3))
        self.assertFalse(detector.is_changed(4, 4))

    def test_multi_line_checks(self):
        detector = _TextChangeDetector('1\n2\n', '1\n3\n')
        self.assertTrue(detector.is_changed(1, 2))

    def test_consume_change(self):
        detector = _TextChangeDetector('1\n2\n', '1\n3\n')
        self.assertTrue(detector.is_changed(1, 2))
        self.assertTrue(detector.consume_changes(1, 2))
        self.assertFalse(detector.is_changed(1, 2))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(PyCoreTest))
    result.addTests(unittest.makeSuite(PyCoreInProjectsTest))
    result.addTests(unittest.makeSuite(ClassHierarchyTest))
    result.addTests(unittest.makeSuite(TextChangeDetectorTest))
    return result


if __name__ == '__main__':
    unittest.main()
