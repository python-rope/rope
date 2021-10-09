import sys
from textwrap import dedent

from rope.base.builtins import File, BuiltinClass

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rope.base import exceptions
from rope.base import libutils
from rope.base.pycore import _TextChangeDetector
from rope.base.pyobjects import get_base_type, AbstractFunction
from rope.base.pynamesdef import AssignedName
from ropetest import testutils


class PyCoreTest(unittest.TestCase):
    def setUp(self):
        super(PyCoreTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore

    def tearDown(self):
        testutils.remove_project(self.project)
        super(PyCoreTest, self).tearDown()

    def test_simple_module(self):
        testutils.create_module(self.project, "mod")
        result = self.project.get_module("mod")
        self.assertEqual(get_base_type("Module"), result.type)
        self.assertEqual(0, len(result.get_attributes()))

    def test_nested_modules(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod = testutils.create_module(self.project, "mod", pkg)  # noqa
        package = self.project.get_module("pkg")
        self.assertEqual(get_base_type("Module"), package.get_type())
        self.assertEqual(1, len(package.get_attributes()))
        module = package["mod"].get_object()
        self.assertEqual(get_base_type("Module"), module.get_type())

    def test_package(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod = testutils.create_module(self.project, "mod", pkg)  # noqa
        result = self.project.get_module("pkg")
        self.assertEqual(get_base_type("Module"), result.type)

    def test_simple_class(self):
        mod = testutils.create_module(self.project, "mod")
        mod.write(
            dedent("""\
                class SampleClass(object):
                    pass
            """)
        )
        mod_element = self.project.get_module("mod")
        result = mod_element["SampleClass"].get_object()
        self.assertEqual(get_base_type("Type"), result.get_type())

    def test_simple_function(self):
        mod = testutils.create_module(self.project, "mod")
        mod.write(
            dedent("""\
                def sample_function():
                    pass
            """)
        )
        mod_element = self.project.get_module("mod")
        result = mod_element["sample_function"].get_object()
        self.assertEqual(get_base_type("Function"), result.get_type())

    def test_class_methods(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class SampleClass(object):
                def sample_method(self):
                    pass
        """)
        mod.write(code)
        mod_element = self.project.get_module("mod")
        sample_class = mod_element["SampleClass"].get_object()
        self.assertTrue("sample_method" in sample_class)
        method = sample_class["sample_method"].get_object()
        self.assertEqual(get_base_type("Function"), method.get_type())

    def test_global_variable_without_type_annotation(self):
        mod = testutils.create_module(self.project, "mod")
        mod.write("var = 10")
        mod_element = self.project.get_module("mod")
        var = mod_element["var"]
        self.assertEqual(AssignedName, type(var))

    @testutils.only_for_versions_higher("3.6")
    def test_global_variable_with_type_annotation(self):
        mod = testutils.create_module(self.project, "mod")
        mod.write("py3_var: str = foo_bar")
        mod_element = self.project.get_module("mod")
        py3_var = mod_element["py3_var"]
        self.assertEqual(AssignedName, type(py3_var))

    def test_class_variables(self):
        mod = testutils.create_module(self.project, "mod")
        mod.write(
            dedent("""\
                class SampleClass(object):
                    var = 10
            """)
        )
        mod_element = self.project.get_module("mod")
        sample_class = mod_element["SampleClass"].get_object()
        var = sample_class["var"]  # noqa

    def test_class_attributes_set_in_init(self):
        mod = testutils.create_module(self.project, "mod")
        mod.write(
            dedent("""\
                class C(object):
                    def __init__(self):
                        self.var = 20
            """)
        )
        mod_element = self.project.get_module("mod")
        sample_class = mod_element["C"].get_object()
        var = sample_class["var"]  # noqa

    def test_class_attributes_set_in_init_overwriting_a_defined(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C(object):
                def __init__(self):
                    self.f = 20
                def f():
                    pass
        """)
        mod.write(code)
        mod_element = self.project.get_module("mod")
        sample_class = mod_element["C"].get_object()
        f = sample_class["f"].get_object()
        self.assertTrue(isinstance(f, AbstractFunction))

    def test_classes_inside_other_classes(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class SampleClass(object):
                class InnerClass(object):
                    pass

        """)
        mod.write(code)
        mod_element = self.project.get_module("mod")
        sample_class = mod_element["SampleClass"].get_object()
        var = sample_class["InnerClass"].get_object()
        self.assertEqual(get_base_type("Type"), var.get_type())

    def test_non_existent_module(self):
        with self.assertRaises(exceptions.ModuleNotFoundError):
            self.project.get_module("doesnotexistmodule")

    def test_imported_names(self):
        testutils.create_module(self.project, "mod1")
        mod = testutils.create_module(self.project, "mod2")
        mod.write("import mod1\n")
        module = self.project.get_module("mod2")
        imported_sys = module["mod1"].get_object()
        self.assertEqual(get_base_type("Module"), imported_sys.get_type())

    def test_imported_as_names(self):
        testutils.create_module(self.project, "mod1")
        mod = testutils.create_module(self.project, "mod2")
        mod.write("import mod1 as my_import\n")
        module = self.project.get_module("mod2")
        imported_mod = module["my_import"].get_object()
        self.assertEqual(get_base_type("Module"), imported_mod.get_type())

    def test_get_string_module(self):
        code = dedent("""\
            class Sample(object):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        sample_class = mod["Sample"].get_object()
        self.assertEqual(get_base_type("Type"), sample_class.get_type())

    def test_get_string_module_with_extra_spaces(self):
        code = "a = 10\n    "
        mod = libutils.get_string_module(self.project, code) # noqa

    def test_parameter_info_for_functions(self):
        code = dedent("""\
            def func(param1, param2=10, *param3, **param4):
                pass""")
        mod = libutils.get_string_module(self.project, code)
        sample_function = mod["func"]
        self.assertEqual(
            ["param1", "param2", "param3", "param4"],
            sample_function.get_object().get_param_names(),
        )

    # FIXME: Not found modules
    def xxx_test_not_found_module_is_module(self):
        code = "import doesnotexist\n"
        mod = libutils.get_string_module(self.project, code)
        self.assertEqual(
            get_base_type("Module"), mod["doesnotexist"].get_object().get_type()
        )

    def test_mixing_scopes_and_objects_hierarchy(self):
        code = "var = 200\n"
        mod = libutils.get_string_module(self.project, code)
        scope = mod.get_scope()
        self.assertTrue("var" in scope.get_names())

    def test_inheriting_base_class_attributes(self):
        code = dedent("""\
            class Base(object):
                def method(self):
                    pass
            class Derived(Base):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        derived = mod["Derived"].get_object()
        self.assertTrue("method" in derived)
        self.assertEqual(
            get_base_type("Function"), derived["method"].get_object().get_type()
        )

    def test_inheriting_multiple_base_class_attributes(self):
        code = dedent("""\
            class Base1(object):
                def method1(self):
                    pass
            class Base2(object):
                def method2(self):
                    pass
            class Derived(Base1, Base2):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        derived = mod["Derived"].get_object()
        self.assertTrue("method1" in derived)
        self.assertTrue("method2" in derived)

    def test_inherit_multiple_base_class_attrs_with_the_same_name(self):
        code = dedent("""\
            class Base1(object):
                def method(self):
                    pass
            class Base2(object):
                def method(self):
                    pass
            class Derived(Base1, Base2):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        base1 = mod["Base1"].get_object()
        derived = mod["Derived"].get_object()
        self.assertEqual(base1["method"].get_object(), derived["method"].get_object())

    def test_inheriting_unknown_base_class(self):
        code = dedent("""\
            class Derived(NotFound):
                def f(self):
                    pass
        """)
        mod = libutils.get_string_module(self.project, code)
        derived = mod["Derived"].get_object()
        self.assertTrue("f" in derived)

    def test_module_creation(self):
        new_module = testutils.create_module(self.project, "module")
        self.assertFalse(new_module.is_folder())
        self.assertEqual(self.project.get_resource("module.py"), new_module)

    def test_packaged_module_creation(self):
        package = self.project.root.create_folder("package")  # noqa
        new_module = testutils.create_module(self.project, "package.module")
        self.assertEqual(self.project.get_resource("package/module.py"), new_module)

    def test_packaged_module_creation_with_nested_src(self):
        src = self.project.root.create_folder("src")
        src.create_folder("pkg")
        new_module = testutils.create_module(self.project, "pkg.mod", src)
        self.assertEqual(self.project.get_resource("src/pkg/mod.py"), new_module)

    def test_package_creation(self):
        new_package = testutils.create_package(self.project, "pkg")
        self.assertTrue(new_package.is_folder())
        self.assertEqual(self.project.get_resource("pkg"), new_package)
        self.assertEqual(
            self.project.get_resource("pkg/__init__.py"),
            new_package.get_child("__init__.py"),
        )

    def test_nested_package_creation(self):
        testutils.create_package(self.project, "pkg1")
        nested_package = testutils.create_package(self.project, "pkg1.pkg2")
        self.assertEqual(self.project.get_resource("pkg1/pkg2"), nested_package)

    def test_packaged_package_creation_with_nested_src(self):
        src = self.project.root.create_folder("src")
        testutils.create_package(self.project, "pkg1", src)
        nested_package = testutils.create_package(self.project, "pkg1.pkg2", src)
        self.assertEqual(self.project.get_resource("src/pkg1/pkg2"), nested_package)

    def test_find_module(self):
        src = self.project.root.create_folder("src")
        samplemod = testutils.create_module(self.project, "samplemod", src)
        found_module = self.project.find_module("samplemod")
        self.assertEqual(samplemod, found_module)

    def test_find_nested_module(self):
        src = self.project.root.create_folder("src")
        samplepkg = testutils.create_package(self.project, "samplepkg", src)
        samplemod = testutils.create_module(self.project, "samplemod", samplepkg)
        found_module = self.project.find_module("samplepkg.samplemod")
        self.assertEqual(samplemod, found_module)

    def test_find_multiple_module(self):
        src = self.project.root.create_folder("src")
        samplemod1 = testutils.create_module(self.project, "samplemod", src)
        samplemod2 = testutils.create_module(self.project, "samplemod")
        test = self.project.root.create_folder("test")
        samplemod3 = testutils.create_module(self.project, "samplemod", test)
        found_module = self.project.find_module("samplemod")
        self.assertTrue(
            samplemod1 == found_module
            or samplemod2 == found_module
            or samplemod3 == found_module
        )

    def test_find_module_packages(self):
        src = self.project.root
        samplepkg = testutils.create_package(self.project, "samplepkg", src)
        found_module = self.project.find_module("samplepkg")
        self.assertEqual(samplepkg, found_module)

    def test_find_module_when_module_and_package_with_the_same_name(self):
        src = self.project.root
        testutils.create_module(self.project, "sample", src)
        samplepkg = testutils.create_package(self.project, "sample", src)
        found_module = self.project.find_module("sample")
        self.assertEqual(samplepkg, found_module)

    def test_source_folders_preference(self):
        testutils.create_package(self.project, "pkg1")
        testutils.create_package(self.project, "pkg1.src2")
        lost = testutils.create_module(self.project, "pkg1.src2.lost")
        self.assertEqual(self.project.find_module("lost"), None)
        self.project.close()
        from rope.base.project import Project

        self.project = Project(self.project.address, source_folders=["pkg1/src2"])
        self.assertEqual(self.project.find_module("lost"), lost)

    def test_get_pyname_definition_location(self):
        code = "a_var = 20\n"
        mod = libutils.get_string_module(self.project, code)
        a_var = mod["a_var"]
        self.assertEqual((mod, 1), a_var.get_definition_location())

    def test_get_pyname_definition_location_functions(self):
        code = dedent("""\
            def a_func():
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        a_func = mod["a_func"]
        self.assertEqual((mod, 1), a_func.get_definition_location())

    def test_get_pyname_definition_location_class(self):
        code = dedent("""\
            class AClass(object):
                pass

        """)
        mod = libutils.get_string_module(self.project, code)
        a_class = mod["AClass"]
        self.assertEqual((mod, 1), a_class.get_definition_location())

    def test_get_pyname_definition_location_local_variables(self):
        code = dedent("""\
            def a_func():
                a_var = 10
        """)
        mod = libutils.get_string_module(self.project, code)
        a_func_scope = mod.get_scope().get_scopes()[0]
        a_var = a_func_scope["a_var"]
        self.assertEqual((mod, 2), a_var.get_definition_location())

    def test_get_pyname_definition_location_reassigning(self):
        code = dedent("""\
            a_var = 20
            a_var=30
        """)
        mod = libutils.get_string_module(self.project, code)
        a_var = mod["a_var"]
        self.assertEqual((mod, 1), a_var.get_definition_location())

    def test_get_pyname_definition_location_importes(self):
        testutils.create_module(self.project, "mod")
        code = "import mod\n"
        mod = libutils.get_string_module(self.project, code)
        imported_module = self.project.get_module("mod")
        module_pyname = mod["mod"]
        self.assertEqual((imported_module, 1), module_pyname.get_definition_location())

    def test_get_pyname_definition_location_imports(self):
        module_resource = testutils.create_module(self.project, "mod")
        module_resource.write(
            dedent("""\

                def a_func():
                    pass
            """)
        )
        imported_module = self.project.get_module("mod")
        code = dedent("""\
            from mod import a_func
        """)
        mod = libutils.get_string_module(self.project, code)
        a_func = mod["a_func"]
        self.assertEqual((imported_module, 2), a_func.get_definition_location())

    def test_get_pyname_definition_location_parameters(self):
        code = dedent("""\
            def a_func(param1, param2):
                a_var = param
        """)
        mod = libutils.get_string_module(self.project, code)
        a_func_scope = mod.get_scope().get_scopes()[0]
        param1 = a_func_scope["param1"]
        self.assertEqual((mod, 1), param1.get_definition_location())
        param2 = a_func_scope["param2"]
        self.assertEqual((mod, 1), param2.get_definition_location())

    def test_module_get_resource(self):
        module_resource = testutils.create_module(self.project, "mod")
        module = self.project.get_module("mod")
        self.assertEqual(module_resource, module.get_resource())
        code = dedent("""\
            from mod import a_func
        """)
        string_module = libutils.get_string_module(self.project, code)
        self.assertEqual(None, string_module.get_resource())

    def test_get_pyname_definition_location_class2(self):
        code = dedent("""\
            class AClass(object):
                def __init__(self):
                    self.an_attr = 10
        """)
        mod = libutils.get_string_module(self.project, code)
        a_class = mod["AClass"].get_object()
        an_attr = a_class["an_attr"]
        self.assertEqual((mod, 3), an_attr.get_definition_location())

    def test_import_not_found_module_get_definition_location(self):
        code = "import doesnotexist\n"
        mod = libutils.get_string_module(self.project, code)
        does_not_exist = mod["doesnotexist"]
        self.assertEqual((None, None), does_not_exist.get_definition_location())

    def test_from_not_found_module_get_definition_location(self):
        code = "from doesnotexist import Sample\n"
        mod = libutils.get_string_module(self.project, code)
        sample = mod["Sample"]
        self.assertEqual((None, None), sample.get_definition_location())

    def test_from_package_import_module_get_definition_location(self):
        pkg = testutils.create_package(self.project, "pkg")
        testutils.create_module(self.project, "mod", pkg)
        pkg_mod = self.project.get_module("pkg.mod")
        code = "from pkg import mod\n"
        mod = libutils.get_string_module(self.project, code)
        imported_mod = mod["mod"]
        self.assertEqual((pkg_mod, 1), imported_mod.get_definition_location())

    def test_get_module_for_defined_pyobjects(self):
        code = dedent("""\
            class AClass(object):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        a_class = mod["AClass"].get_object()
        self.assertEqual(mod, a_class.get_module())

    def test_get_definition_location_for_packages(self):
        testutils.create_package(self.project, "pkg")
        init_module = self.project.get_module("pkg.__init__")
        code = "import pkg\n"
        mod = libutils.get_string_module(self.project, code)
        pkg_pyname = mod["pkg"]
        self.assertEqual((init_module, 1), pkg_pyname.get_definition_location())

    def test_get_definition_location_for_filtered_packages(self):
        pkg = testutils.create_package(self.project, "pkg")
        testutils.create_module(self.project, "mod", pkg)
        init_module = self.project.get_module("pkg.__init__")
        code = "import pkg.mod"
        mod = libutils.get_string_module(self.project, code)
        pkg_pyname = mod["pkg"]
        self.assertEqual((init_module, 1), pkg_pyname.get_definition_location())

    def test_out_of_project_modules(self):
        code = "import rope.base.project as project\n"
        scope = libutils.get_string_scope(self.project, code)
        imported_module = scope["project"].get_object()
        self.assertTrue("Project" in imported_module)

    def test_file_encoding_reading(self):
        contents = (
            u"# -*- coding: utf-8 -*-\n" + u"#\N{LATIN SMALL LETTER I WITH DIAERESIS}\n"
        )
        mod = testutils.create_module(self.project, "mod")
        mod.write(contents)
        self.project.get_module("mod")

    def test_global_keyword(self):
        code = dedent("""\
            a_var = 1
            def a_func():
                global a_var
        """)
        mod = libutils.get_string_module(self.project, code)
        global_var = mod["a_var"]
        func_scope = mod["a_func"].get_object().get_scope()
        local_var = func_scope["a_var"]
        self.assertEqual(global_var, local_var)

    def test_not_leaking_for_vars_inside_parent_scope(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C(object):
                def f(self):
                    for my_var1, my_var2 in []:
                        pass
        """)
        mod.write(code)
        pymod = self.pycore.resource_to_pyobject(mod)
        c_class = pymod["C"].get_object()
        self.assertFalse("my_var1" in c_class)
        self.assertFalse("my_var2" in c_class)

    def test_not_leaking_for_vars_inside_parent_scope2(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C(object):
                def f(self):
                    for my_var in []:
                        pass
        """)
        mod.write(code)
        pymod = self.pycore.resource_to_pyobject(mod)
        c_class = pymod["C"].get_object()
        self.assertFalse("my_var" in c_class)

    def test_variables_defined_in_excepts(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            try:
                myvar1 = 1
            except:
                myvar2 = 1
            finally:
                myvar3 = 1
        """)
        mod.write(code)
        pymod = self.pycore.resource_to_pyobject(mod)
        self.assertTrue("myvar1" in pymod)
        self.assertTrue("myvar2" in pymod)
        self.assertTrue("myvar3" in pymod)

    def test_not_leaking_tuple_assigned_names_inside_parent_scope(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C(object):
                def f(self):
                    var1, var2 = range(2)
        """)
        mod.write(code)
        pymod = self.pycore.resource_to_pyobject(mod)
        c_class = pymod["C"].get_object()
        self.assertFalse("var1" in c_class)

    @testutils.only_for("2.5")
    def test_with_statement_variables(self):
        code = dedent("""\
            import threading
            with threading.lock() as var:    pass
        """)
        if sys.version_info < (2, 6, 0):
            code = "from __future__ import with_statement\n" + code
        pymod = libutils.get_string_module(self.project, code)
        self.assertTrue("var" in pymod)

    @testutils.only_for("2.5")
    def test_with_statement_variables_and_tuple_assignment(self):
        code = dedent("""\
            class A(object):
                def __enter__(self):        return (1, 2)
                def __exit__(self, type, value, tb):
                    pass
            with A() as (a, b):
                pass
        """)
        if sys.version_info < (2, 6, 0):
            code = "from __future__ import with_statement\n" + code
        pymod = libutils.get_string_module(self.project, code)
        self.assertTrue("a" in pymod)
        self.assertTrue("b" in pymod)

    @testutils.only_for("2.5")
    def test_with_statement_variable_type(self):
        code = dedent("""\
            class A(object):
                def __enter__(self):
                    return self
                def __exit__(self, type, value, tb):
                    pass
            with A() as var:
                pass
        """)
        if sys.version_info < (2, 6, 0):
            code = "from __future__ import with_statement\n" + code
        pymod = libutils.get_string_module(self.project, code)
        a_class = pymod["A"].get_object()
        var = pymod["var"].get_object()
        self.assertEqual(a_class, var.get_type())

    @testutils.only_for("2.7")
    def test_nested_with_statement_variable_type(self):
        code = dedent("""\
            class A(object):
                def __enter__(self):
                    return self
                def __exit__(self, type, value, tb):
                    pass
            class B(object):
                def __enter__(self):
                    return self
                def __exit__(self, type, value, tb):
                    pass
            with A() as var_a, B() as var_b:
                pass
        """)
        if sys.version_info < (2, 6, 0):
            code = "from __future__ import with_statement\n" + code
        pymod = libutils.get_string_module(self.project, code)
        a_class = pymod["A"].get_object()
        var_a = pymod["var_a"].get_object()
        self.assertEqual(a_class, var_a.get_type())

        b_class = pymod["B"].get_object()
        var_b = pymod["var_b"].get_object()
        self.assertEqual(b_class, var_b.get_type())

    @testutils.only_for("2.5")
    def test_with_statement_with_no_vars(self):
        code = dedent("""\
            with open("file"):    pass
        """)
        if sys.version_info < (2, 6, 0):
            code = "from __future__ import with_statement\n" + code
        pymod = libutils.get_string_module(self.project, code)
        pymod.get_attributes()

    def test_with_statement(self):
        code = dedent("""\
            a = 10
            with open("file") as f:    pass
        """)
        pymod = libutils.get_string_module(self.project, code)
        assigned = pymod.get_attribute("a")
        self.assertEqual(BuiltinClass, type(assigned.get_object().get_type()))

        assigned = pymod.get_attribute("f")
        self.assertEqual(File, type(assigned.get_object().get_type()))

    def test_check_for_else_block(self):
        code = dedent("""\
            for i in range(10):
                pass
            else:
                myvar = 1
        """)
        mod = libutils.get_string_module(self.project, code)
        a_var = mod["myvar"]
        self.assertEqual((mod, 4), a_var.get_definition_location())

    def test_check_names_defined_in_whiles(self):
        code = dedent("""\
            while False:
                myvar = 1
        """)
        mod = libutils.get_string_module(self.project, code)
        a_var = mod["myvar"]
        self.assertEqual((mod, 2), a_var.get_definition_location())

    def test_get_definition_location_in_tuple_assnames(self):
        code = dedent("""\
            def f(x):
                x.z, a = range(2)
        """)
        mod = libutils.get_string_module(self.project, code)
        x = mod["f"].get_object().get_scope()["x"]
        a = mod["f"].get_object().get_scope()["a"]
        self.assertEqual((mod, 1), x.get_definition_location())
        self.assertEqual((mod, 2), a.get_definition_location())

    def test_syntax_errors_in_code(self):
        with self.assertRaises(exceptions.ModuleSyntaxError):
            libutils.get_string_module(self.project, "xyx print\n")

    def test_holding_error_location_information(self):
        try:
            libutils.get_string_module(self.project, "xyx print\n")
        except exceptions.ModuleSyntaxError as e:
            self.assertEqual(1, e.lineno)

    def test_no_exceptions_on_module_encoding_problems(self):
        mod = testutils.create_module(self.project, "mod")
        contents = b"\nsdsdsd\n\xa9\n"
        file = open(mod.real_path, "wb")
        file.write(contents)
        file.close()
        mod.read()

    def test_syntax_errors_when_cannot_decode_file2(self):
        mod = testutils.create_module(self.project, "mod")
        contents = b"\n\xa9\n"
        file = open(mod.real_path, "wb")
        file.write(contents)
        file.close()
        with self.assertRaises(exceptions.ModuleSyntaxError):
            self.pycore.resource_to_pyobject(mod)

    def test_syntax_errors_when_null_bytes(self):
        mod = testutils.create_module(self.project, "mod")
        contents = b"\n\x00\n"
        file = open(mod.real_path, "wb")
        file.write(contents)
        file.close()
        with self.assertRaises(exceptions.ModuleSyntaxError):
            self.pycore.resource_to_pyobject(mod)

    def test_syntax_errors_when_bad_strs(self):
        mod = testutils.create_module(self.project, "mod")
        contents = b'\n"\\x0"\n'
        file = open(mod.real_path, "wb")
        file.write(contents)
        file.close()
        with self.assertRaises(exceptions.ModuleSyntaxError):
            self.pycore.resource_to_pyobject(mod)

    def test_not_reaching_maximum_recursions_with_from_star_imports(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write("from mod2 import *\n")
        mod2.write("from mod1 import *\n")
        pymod1 = self.pycore.resource_to_pyobject(mod1)
        pymod1.get_attributes()

    def test_not_reaching_maximum_recursions_when_importing_variables(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write("from mod2 import myvar\n")
        mod2.write("from mod1 import myvar\n")
        pymod1 = self.pycore.resource_to_pyobject(mod1)
        pymod1["myvar"].get_object()

    def test_not_reaching_maximum_recursions_when_importing_variables2(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write("from mod1 import myvar\n")
        pymod1 = self.pycore.resource_to_pyobject(mod1)
        pymod1["myvar"].get_object()

    def test_pyobject_equality_should_compare_types(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(
            dedent("""\
                var1 = ""
                var2 = ""
            """)
        )
        pymod1 = self.pycore.resource_to_pyobject(mod1)
        self.assertEqual(pymod1["var1"].get_object(), pymod1["var2"].get_object())


class PyCoreInProjectsTest(unittest.TestCase):
    def setUp(self):
        super(self.__class__, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        samplemod = testutils.create_module(self.project, "samplemod")
        code = dedent("""\
            class SampleClass(object):
                def sample_method():
                    pass

            def sample_func():
                pass
            sample_var = 10

            def _underlined_func():
                pass

        """)
        samplemod.write(code)
        package = testutils.create_package(self.project, "package")
        testutils.create_module(self.project, "nestedmod", package)

    def tearDown(self):
        testutils.remove_project(self.project)
        super(self.__class__, self).tearDown()

    def test_simple_import(self):
        code = "import samplemod\n"
        mod = libutils.get_string_module(self.project, code)
        samplemod = mod["samplemod"].get_object()
        self.assertEqual(get_base_type("Module"), samplemod.get_type())

    def test_from_import_class(self):
        code = "from samplemod import SampleClass\n"
        mod = libutils.get_string_module(self.project, code)
        result = mod["SampleClass"].get_object()
        self.assertEqual(get_base_type("Type"), result.get_type())
        self.assertTrue("sample_func" not in mod.get_attributes())

    def test_from_import_star(self):
        code = "from samplemod import *\n"
        mod = libutils.get_string_module(self.project, code)
        self.assertEqual(
            get_base_type("Type"), mod["SampleClass"].get_object().get_type()
        )
        self.assertEqual(
            get_base_type("Function"), mod["sample_func"].get_object().get_type()
        )
        self.assertTrue(mod["sample_var"] is not None)

    def test_from_import_star_overwriting(self):
        code = dedent("""\
            from samplemod import *
            class SampleClass(object):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        samplemod = self.project.get_module("samplemod")
        sample_class = samplemod["SampleClass"].get_object()
        self.assertNotEqual(
            sample_class, mod.get_attributes()["SampleClass"].get_object()
        )

    def test_from_import_star_not_imporing_underlined(self):
        code = "from samplemod import *"
        mod = libutils.get_string_module(self.project, code)
        self.assertTrue("_underlined_func" not in mod.get_attributes())

    def test_from_import_star_imports_in_functions(self):
        code = dedent("""\
            def f():
                from os import *
        """)
        mod = libutils.get_string_module(self.project, code)
        mod["f"].get_object().get_scope().get_names()

    def test_from_package_import_mod(self):
        code = "from package import nestedmod\n"
        mod = libutils.get_string_module(self.project, code)
        self.assertEqual(
            get_base_type("Module"), mod["nestedmod"].get_object().get_type()
        )

    # XXX: Deciding to import everything on import start from packages
    def xxx_test_from_package_import_star(self):
        code = "from package import *\n"
        mod = libutils.get_string_module(self.project, code)
        self.assertTrue("nestedmod" not in mod.get_attributes())

    def test_unknown_when_module_cannot_be_found(self):
        code = "from doesnotexist import nestedmod\n"
        mod = libutils.get_string_module(self.project, code)
        self.assertTrue("nestedmod" in mod)

    def test_from_import_function(self):
        code = dedent("""\
            def f():
                from samplemod import SampleClass
        """)
        scope = libutils.get_string_scope(self.project, code)
        self.assertEqual(
            get_base_type("Type"),
            scope.get_scopes()[0]["SampleClass"].get_object().get_type(),
        )

    def test_circular_imports(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write("import mod2\n")
        mod2.write("import mod1\n")
        self.project.get_module("mod1")

    def test_circular_imports2(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write(
            dedent("""\
                from mod2 import Sample2
                class Sample1(object):
                    pass
            """)
        )
        mod2.write(
            dedent("""\
                from mod1 import Sample1
                class Sample2(object):
                    pass
            """)
        )
        self.project.get_module("mod1").get_attributes()

    def test_multi_dot_imports(self):
        pkg = testutils.create_package(self.project, "pkg")
        pkg_mod = testutils.create_module(self.project, "mod", pkg)
        pkg_mod.write(
            dedent("""\
                def sample_func():
                    pass
            """)
        )
        code = "import pkg.mod\n"
        mod = libutils.get_string_module(self.project, code)
        self.assertTrue("pkg" in mod)
        self.assertTrue("sample_func" in mod["pkg"].get_object()["mod"].get_object())

    def test_multi_dot_imports2(self):
        pkg = testutils.create_package(self.project, "pkg")
        testutils.create_module(self.project, "mod1", pkg)
        testutils.create_module(self.project, "mod2", pkg)
        code = dedent("""\
            import pkg.mod1
            import pkg.mod2
        """)
        mod = libutils.get_string_module(self.project, code)
        package = mod["pkg"].get_object()
        self.assertEqual(2, len(package.get_attributes()))
        self.assertTrue("mod1" in package and "mod2" in package)

    def test_multi_dot_imports3(self):
        pkg1 = testutils.create_package(self.project, "pkg1")
        pkg2 = testutils.create_package(self.project, "pkg2", pkg1)
        testutils.create_module(self.project, "mod1", pkg2)
        testutils.create_module(self.project, "mod2", pkg2)
        code = dedent("""\
            import pkg1.pkg2.mod1
            import pkg1.pkg2.mod2
        """)
        mod = libutils.get_string_module(self.project, code)
        package1 = mod["pkg1"].get_object()
        package2 = package1["pkg2"].get_object()
        self.assertEqual(2, len(package2.get_attributes()))
        self.assertTrue("mod1" in package2 and "mod2" in package2)

    def test_multi_dot_imports_as(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod1 = testutils.create_module(self.project, "mod1", pkg)
        mod1.write(
            dedent("""\
                def f():
                    pass
            """)
        )
        code = "import pkg.mod1 as mod1\n"
        mod = libutils.get_string_module(self.project, code)
        module = mod["mod1"].get_object()
        self.assertTrue("f" in module)

    # TODO: not showing unimported names as attributes of packages
    def xxx_test_from_package_import_package(self):
        pkg1 = testutils.create_package(self.project, "pkg1")
        pkg2 = testutils.create_package(self.project, "pkg2", pkg1)
        testutils.create_module(self.project, "mod", pkg2)
        code = "from pkg1 import pkg2\n"
        mod = libutils.get_string_module(self.project, code)
        package = mod["pkg2"]
        self.assertEqual(0, len(package.get_attributes()))

    def test_invalidating_cache_after_resource_change(self):
        module = testutils.create_module(self.project, "mod")
        module.write("import sys\n")
        mod1 = self.project.get_module("mod")
        self.assertTrue("var" not in mod1.get_attributes())
        module.write("var = 10\n")
        mod2 = self.project.get_module("mod")
        self.assertTrue("var" in mod2)

    def test_invalidating_cache_after_resource_change_for_init_dot_pys(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod = testutils.create_module(self.project, "mod")
        init_dot_py = pkg.get_child("__init__.py")
        init_dot_py.write("a_var = 10\n")
        mod.write("import pkg\n")
        pymod = self.project.get_module("mod")
        self.assertTrue("a_var" in pymod["pkg"].get_object())
        init_dot_py.write("new_var = 10\n")
        self.assertTrue("a_var" not in pymod["pkg"].get_object().get_attributes())

    def test_invalidating_cache_after_rsrc_chng_for_nested_init_dot_pys(self):
        pkg1 = testutils.create_package(self.project, "pkg1")
        pkg2 = testutils.create_package(self.project, "pkg2", pkg1)
        mod = testutils.create_module(self.project, "mod")
        init_dot_py = pkg2.get_child("__init__.py")
        init_dot_py.write("a_var = 10\n")
        mod.write("import pkg1\n")
        pymod = self.project.get_module("mod")
        self.assertTrue("a_var" in pymod["pkg1"].get_object()["pkg2"].get_object())
        init_dot_py.write("new_var = 10\n")
        self.assertTrue("a_var" not in pymod["pkg1"].get_object()["pkg2"].get_object())

    def test_from_import_nonexistent_module(self):
        code = "from doesnotexistmod import DoesNotExistClass\n"
        mod = libutils.get_string_module(self.project, code)
        self.assertTrue("DoesNotExistClass" in mod)
        self.assertEqual(
            get_base_type("Unknown"), mod["DoesNotExistClass"].get_object().get_type()
        )

    def test_from_import_nonexistent_name(self):
        code = "from samplemod import DoesNotExistClass\n"
        mod = libutils.get_string_module(self.project, code)
        self.assertTrue("DoesNotExistClass" in mod)
        self.assertEqual(
            get_base_type("Unknown"), mod["DoesNotExistClass"].get_object().get_type()
        )

    def test_not_considering_imported_names_as_sub_scopes(self):
        code = "from samplemod import SampleClass\n"
        scope = libutils.get_string_scope(self.project, code)
        self.assertEqual(0, len(scope.get_scopes()))

    def test_not_considering_imported_modules_as_sub_scopes(self):
        code = "import samplemod\n"
        scope = libutils.get_string_scope(self.project, code)
        self.assertEqual(0, len(scope.get_scopes()))

    def test_inheriting_dotted_base_class(self):
        code = dedent("""\
            import samplemod
            class Derived(samplemod.SampleClass):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        derived = mod["Derived"].get_object()
        self.assertTrue("sample_method" in derived)

    def test_self_in_methods(self):
        code = dedent("""\
            class Sample(object):
                def func(self):
                    pass
        """)
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope["Sample"].get_object()
        func_scope = scope.get_scopes()[0].get_scopes()[0]
        self.assertEqual(sample_class, func_scope["self"].get_object().get_type())
        self.assertTrue("func" in func_scope["self"].get_object())

    def test_none_assignments_in_classes(self):
        code = dedent("""\
            class C(object):
                var = ""
                def f(self):
                    self.var += "".join([])
        """)
        scope = libutils.get_string_scope(self.project, code)
        c_class = scope["C"].get_object()
        self.assertTrue("var" in c_class)

    def test_self_in_methods_with_decorators(self):
        code = dedent("""\
            class Sample(object):
                @staticmethod
                def func(self):
                    pass
        """)
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope["Sample"].get_object()
        func_scope = scope.get_scopes()[0].get_scopes()[0]
        self.assertNotEqual(sample_class, func_scope["self"].get_object().get_type())

    def test_location_of_imports_when_importing(self):
        mod = testutils.create_module(self.project, "mod")
        mod.write("from samplemod import SampleClass\n")
        code = "from mod import SampleClass\n"
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope["SampleClass"]
        samplemod = self.project.get_module("samplemod")
        self.assertEqual((samplemod, 1), sample_class.get_definition_location())

    def test_nested_modules(self):
        pkg = testutils.create_package(self.project, "pkg")
        testutils.create_module(self.project, "mod", pkg)
        imported_module = self.project.get_module("pkg.mod")
        code = "import pkg.mod\n"
        scope = libutils.get_string_scope(self.project, code)
        mod_pyobject = scope["pkg"].get_object()["mod"]
        self.assertEqual((imported_module, 1), mod_pyobject.get_definition_location())

    def test_reading_init_dot_py(self):
        pkg = testutils.create_package(self.project, "pkg")
        init_dot_py = pkg.get_child("__init__.py")
        init_dot_py.write("a_var = 1\n")
        pkg_object = self.project.get_module("pkg")
        self.assertTrue("a_var" in pkg_object)

    def test_relative_imports(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod1 = testutils.create_module(self.project, "mod1", pkg)
        mod2 = testutils.create_module(self.project, "mod2", pkg)
        mod2.write("import mod1\n")
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEqual(mod1_object, mod2_object.get_attributes()["mod1"].get_object())

    def test_relative_froms(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod1 = testutils.create_module(self.project, "mod1", pkg)
        mod2 = testutils.create_module(self.project, "mod2", pkg)
        mod1.write(
            dedent("""\
                def a_func():
                    pass
            """)
        )
        mod2.write("from mod1 import a_func\n")
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEqual(
            mod1_object["a_func"].get_object(), mod2_object["a_func"].get_object()
        )

    def test_relative_imports_for_string_modules(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod1 = testutils.create_module(self.project, "mod1", pkg)
        mod2 = testutils.create_module(self.project, "mod2", pkg)
        mod2.write("import mod1\n")
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = libutils.get_string_module(self.project, mod2.read(), mod2)
        self.assertEqual(mod1_object, mod2_object["mod1"].get_object())

    def test_relative_imports_for_string_scopes(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod1 = testutils.create_module(self.project, "mod1", pkg)
        mod2 = testutils.create_module(self.project, "mod2", pkg)
        mod2.write("import mod1\n")
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_scope = libutils.get_string_scope(self.project, mod2.read(), mod2)
        self.assertEqual(mod1_object, mod2_scope["mod1"].get_object())

    @testutils.only_for("2.5")
    def test_new_style_relative_imports(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod1 = testutils.create_module(self.project, "mod1", pkg)
        mod2 = testutils.create_module(self.project, "mod2", pkg)
        mod2.write("from . import mod1\n")
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEqual(mod1_object, mod2_object["mod1"].get_object())

    @testutils.only_for("2.5")
    def test_new_style_relative_imports2(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2", pkg)
        mod1.write(
            dedent("""\
                def a_func():
                    pass
            """)
        )
        mod2.write("from ..mod1 import a_func\n")
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEqual(
            mod1_object["a_func"].get_object(), mod2_object["a_func"].get_object()
        )

    def test_invalidating_cache_for_from_imports_after_resource_change(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write(
            dedent("""\
                def a_func():
                    print(1)
            """)
        )
        mod1.write(
            dedent("""\
                from mod2 import a_func
                a_func()
            """)
        )

        pymod1 = self.project.get_module("mod1")
        pymod2 = self.project.get_module("mod2")
        self.assertEqual(pymod1["a_func"].get_object(), pymod2["a_func"].get_object())
        mod2.write(mod2.read() + "\n")
        pymod2 = self.project.get_module("mod2")
        self.assertEqual(pymod1["a_func"].get_object(), pymod2["a_func"].get_object())

    def test_invalidating_superclasses_after_change(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write(
            dedent("""\
                class A(object):
                    def func1(self):
                        pass
            """)
        )
        mod2.write(
            dedent("""\
                import mod1
                class B(mod1.A):
                    pass
            """)
        )

        b_class = self.project.get_module("mod2")["B"].get_object()
        self.assertTrue("func1" in b_class)

        mod1.write(
            dedent("""\
                class A(object):
                    def func2(self):
                        pass
            """)
        )
        self.assertTrue("func2" in b_class)

    def test_caching_pymodule_with_syntax_errors(self):
        self.project.prefs["ignore_syntax_errors"] = True
        self.project.prefs["automatic_soa"] = True
        self.project.pycore._init_automatic_soa()
        source = dedent("""\
            import sys
            ab cd""")
        mod = testutils.create_module(self.project, "mod")
        mod.write(source)
        from rope.contrib import fixsyntax

        fixer = fixsyntax.FixSyntax(self.project, source, mod, 10)
        pymodule = fixer.get_pymodule()
        self.assertTrue(pymodule.source_code.startswith("import sys\npass\n"))


class TextChangeDetectorTest(unittest.TestCase):
    def test_trivial_case(self):
        detector = _TextChangeDetector("\n", "\n")
        self.assertFalse(detector.is_changed(1, 1))

    def test_one_line_change(self):
        detector = _TextChangeDetector("1\n2\n", "1\n3\n")
        self.assertFalse(detector.is_changed(1, 1))
        self.assertTrue(detector.is_changed(2, 2))

    def test_line_expansion(self):
        detector = _TextChangeDetector("1\n2\n", "1\n3\n4\n2\n")
        self.assertFalse(detector.is_changed(1, 1))
        self.assertFalse(detector.is_changed(2, 2))

    def test_line_removals(self):
        detector = _TextChangeDetector("1\n3\n4\n2\n", "1\n2\n")
        self.assertFalse(detector.is_changed(1, 1))
        self.assertTrue(detector.is_changed(2, 3))
        self.assertFalse(detector.is_changed(4, 4))

    def test_multi_line_checks(self):
        detector = _TextChangeDetector("1\n2\n", "1\n3\n")
        self.assertTrue(detector.is_changed(1, 2))

    def test_consume_change(self):
        detector = _TextChangeDetector("1\n2\n", "1\n3\n")
        self.assertTrue(detector.is_changed(1, 2))
        self.assertTrue(detector.consume_changes(1, 2))
        self.assertFalse(detector.is_changed(1, 2))


class PyCoreProjectConfigsTest(unittest.TestCase):
    def setUp(self):
        super(PyCoreProjectConfigsTest, self).setUp()
        self.project = None

    def tearDown(self):
        if self.project:
            testutils.remove_project(self.project)
        super(PyCoreProjectConfigsTest, self).tearDown()

    def test_python_files_config(self):
        self.project = testutils.sample_project(python_files=["myscript"])
        myscript = self.project.root.create_file("myscript")
        self.assertTrue(self.project.pycore.is_python_file(myscript))

    def test_ignore_bad_imports(self):
        self.project = testutils.sample_project(ignore_bad_imports=True)
        code = "import some_nonexistent_module\n"
        pymod = libutils.get_string_module(self.project, code)
        self.assertFalse("some_nonexistent_module" in pymod)

    def test_ignore_bad_imports_for_froms(self):
        self.project = testutils.sample_project(ignore_bad_imports=True)
        code = "from some_nonexistent_module import var\n"
        pymod = libutils.get_string_module(self.project, code)
        self.assertFalse("var" in pymod)

    def test_reporting_syntax_errors_with_force_errors(self):
        self.project = testutils.sample_project(ignore_syntax_errors=True)
        mod = testutils.create_module(self.project, "mod")
        mod.write("syntax error ...\n")
        with self.assertRaises(exceptions.ModuleSyntaxError):
            self.project.pycore.resource_to_pyobject(mod, force_errors=True)

    def test_reporting_syntax_errors_in_strings_with_force_errors(self):
        self.project = testutils.sample_project(ignore_syntax_errors=True)
        with self.assertRaises(exceptions.ModuleSyntaxError):
            libutils.get_string_module(
                self.project, "syntax error ...", force_errors=True
            )

    def test_not_raising_errors_for_strings_with_ignore_errors(self):
        self.project = testutils.sample_project(ignore_syntax_errors=True)
        libutils.get_string_module(self.project, "syntax error ...")

    def test_reporting_syntax_errors_with_force_errors_for_packages(self):
        self.project = testutils.sample_project(ignore_syntax_errors=True)
        pkg = testutils.create_package(self.project, "pkg")
        pkg.get_child("__init__.py").write("syntax error ...\n")
        with self.assertRaises(exceptions.ModuleSyntaxError):
            self.project.pycore.resource_to_pyobject(pkg, force_errors=True)
