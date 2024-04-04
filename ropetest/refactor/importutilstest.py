import unittest
from textwrap import dedent

from rope.base.prefs import get_preferred_import_style, ImportStyle, Prefs, ImportPrefs
from rope.base.prefs import DEFAULT_IMPORT_STYLE
from rope.refactor.importutils import ImportTools, add_import, importinfo
from ropetest import testutils


class TestImportPrefs:
    def test_preferred_import_style_is_normal_import(self, project):
        pref = Prefs(imports=ImportPrefs(preferred_import_style="normal-import"))
        assert pref.imports.preferred_import_style == "normal-import"
        assert get_preferred_import_style(pref) == ImportStyle.normal_import

    def test_preferred_import_style_is_from_module(self, project):
        pref = Prefs(imports=ImportPrefs(preferred_import_style="from-module"))
        assert pref.imports.preferred_import_style == "from-module"
        assert get_preferred_import_style(pref) == ImportStyle.from_module

    def test_preferred_import_style_is_from_global(self, project):
        pref = Prefs(imports=ImportPrefs(preferred_import_style="from-global"))
        assert pref.imports.preferred_import_style == "from-global"
        assert get_preferred_import_style(pref) == ImportStyle.from_global

    def test_invalid_preferred_import_style_is_default(self, project):
        pref = Prefs(imports=ImportPrefs(preferred_import_style="invalid-value"))
        assert pref.imports.preferred_import_style == "invalid-value"
        assert get_preferred_import_style(pref) == DEFAULT_IMPORT_STYLE
        assert get_preferred_import_style(pref) == ImportStyle.normal_import

    def test_default_preferred_import_style_default_is_normal_imports(self, project):
        pref = Prefs()
        assert pref.imports.preferred_import_style == "default"
        assert get_preferred_import_style(pref) == ImportStyle.normal_import

    def test_default_preferred_import_style_default_and_prefer_module_from_imports(self, project):
        pref = Prefs(
            prefer_module_from_imports=True,
            imports=ImportPrefs(preferred_import_style="default"),
        )
        assert get_preferred_import_style(pref) == ImportStyle.from_module

    def test_preferred_import_style_is_normal_import_takes_precedence_over_prefer_module_from_imports(self, project):
        pref = Prefs(
            prefer_module_from_imports=True,
            imports=ImportPrefs(preferred_import_style="normal_import"),
        )
        assert get_preferred_import_style(pref) == ImportStyle.normal_import

    def test_preferred_import_style_is_from_module_takes_precedence_over_prefer_module_from_imports(self, project):
        pref = Prefs(
            prefer_module_from_imports=True,
            imports=ImportPrefs(preferred_import_style="from-module"),
        )
        assert get_preferred_import_style(pref) == ImportStyle.from_module

    def test_preferred_import_style_is_from_global_takes_precedence_over_prefer_module_from_imports(self, project):
        pref = Prefs(
            prefer_module_from_imports=True,
            imports=ImportPrefs(preferred_import_style="from-global"),
        )
        assert get_preferred_import_style(pref) == ImportStyle.from_global


class ImportUtilsTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()
        self.import_tools = ImportTools(self.project)

        self.mod = testutils.create_module(self.project, "mod")
        self.pkg1 = testutils.create_package(self.project, "pkg1")
        self.mod1 = testutils.create_module(self.project, "mod1", self.pkg1)
        self.pkg2 = testutils.create_package(self.project, "pkg2")
        self.mod2 = testutils.create_module(self.project, "mod2", self.pkg2)
        self.mod3 = testutils.create_module(self.project, "mod3", self.pkg2)
        p1 = testutils.create_package(self.project, "p1")
        p2 = testutils.create_package(self.project, "p2", p1)
        p3 = testutils.create_package(self.project, "p3", p2)
        m1 = testutils.create_module(self.project, "m1", p3)  # noqa
        l = testutils.create_module(self.project, "l", p3)  # noqa

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def test_get_import_for_module(self):
        mod = self.project.find_module("mod")
        import_statement = self.import_tools.get_import(mod)
        self.assertEqual("import mod", import_statement.get_import_statement())

    def test_get_import_for_module_in_nested_modules(self):
        mod = self.project.find_module("pkg1.mod1")
        import_statement = self.import_tools.get_import(mod)
        self.assertEqual("import pkg1.mod1", import_statement.get_import_statement())

    def test_get_import_for_module_in_init_dot_py(self):
        init_dot_py = self.pkg1.get_child("__init__.py")
        import_statement = self.import_tools.get_import(init_dot_py)
        self.assertEqual("import pkg1", import_statement.get_import_statement())

    def test_get_from_import_for_module(self):
        mod = self.project.find_module("mod")
        import_statement = self.import_tools.get_from_import(mod, "a_func")
        self.assertEqual(
            "from mod import a_func", import_statement.get_import_statement()
        )

    def test_get_from_import_for_module_in_nested_modules(self):
        mod = self.project.find_module("pkg1.mod1")
        import_statement = self.import_tools.get_from_import(mod, "a_func")
        self.assertEqual(
            "from pkg1.mod1 import a_func", import_statement.get_import_statement()
        )

    def test_get_from_import_for_module_in_init_dot_py(self):
        init_dot_py = self.pkg1.get_child("__init__.py")
        import_statement = self.import_tools.get_from_import(init_dot_py, "a_func")
        self.assertEqual(
            "from pkg1 import a_func", import_statement.get_import_statement()
        )

    def test_get_import_statements(self):
        self.mod.write("import pkg1\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEqual("import pkg1", imports[0].import_info.get_import_statement())

    def test_get_import_statements_with_alias(self):
        self.mod.write("import pkg1.mod1 as mod1\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEqual(
            "import pkg1.mod1 as mod1", imports[0].import_info.get_import_statement()
        )

    def test_get_import_statements_for_froms(self):
        self.mod.write("from pkg1 import mod1\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEqual(
            "from pkg1 import mod1", imports[0].import_info.get_import_statement()
        )

    def test_get_multi_line_import_statements_for_froms(self):
        self.mod.write("from pkg1 \\\n    import mod1\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEqual(
            "from pkg1 import mod1", imports[0].import_info.get_import_statement()
        )

    def test_get_import_statements_for_from_star(self):
        self.mod.write("from pkg1 import *\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEqual(
            "from pkg1 import *", imports[0].import_info.get_import_statement()
        )

    def test_get_import_statements_for_new_relatives(self):
        self.mod2.write("from .mod3 import x\n")
        pymod = self.project.get_module("pkg2.mod2")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEqual(
            "from .mod3 import x", imports[0].import_info.get_import_statement()
        )

    def test_ignoring_indented_imports(self):
        self.mod.write(dedent("""\
            if True:
                import pkg1
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        self.assertEqual(0, len(imports))

    def test_import_get_names(self):
        self.mod.write("import pkg1 as pkg\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        context = importinfo.ImportContext(self.project, self.project.root)
        self.assertEqual(["pkg"], imports[0].import_info.get_imported_names(context))

    def test_import_get_names_with_alias(self):
        self.mod.write("import pkg1.mod1\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        context = importinfo.ImportContext(self.project, self.project.root)
        self.assertEqual(["pkg1"], imports[0].import_info.get_imported_names(context))

    def test_import_get_names_with_alias2(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
        """))
        self.mod.write("from pkg1.mod1 import *\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.imports
        context = importinfo.ImportContext(self.project, self.project.root)
        self.assertEqual(["a_func"], imports[0].import_info.get_imported_names(context))

    def test_empty_getting_used_imports(self):
        self.mod.write("")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEqual(0, len(imports))

    def test_empty_getting_used_imports2(self):
        self.mod.write("import pkg\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEqual(0, len(imports))

    def test_simple_getting_used_imports(self):
        self.mod.write("import pkg\nprint(pkg)\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEqual(1, len(imports))
        self.assertEqual("import pkg", imports[0].get_import_statement())

    def test_simple_getting_used_imports2(self):
        self.mod.write(dedent("""\
            import pkg
            def a_func():
                print(pkg)
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEqual(1, len(imports))
        self.assertEqual("import pkg", imports[0].get_import_statement())

    def test_getting_used_imports_for_nested_scopes(self):
        self.mod.write(dedent("""\
            import pkg1
            print(pkg1)
            def a_func():
                pass
            print(pkg1)
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod["a_func"].get_object())
        self.assertEqual(0, len(imports))

    def test_getting_used_imports_for_nested_scopes2(self):
        self.mod.write(dedent("""\
            from pkg1 import mod1
            def a_func():
                print(mod1)
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod["a_func"].get_object())
        self.assertEqual(1, len(imports))
        self.assertEqual("from pkg1 import mod1", imports[0].get_import_statement())

    def test_empty_removing_unused_imports(self):
        self.mod.write("import pkg1\nprint(pkg1)\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            "import pkg1\nprint(pkg1)\n", module_with_imports.get_changed_source()
        )

    def test_simple_removing_unused_imports(self):
        self.mod.write("import pkg1\n\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual("", module_with_imports.get_changed_source())

    def test_simple_removing_unused_imports_for_froms(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
            def another_func():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import a_func, another_func

            a_func()
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                from pkg1.mod1 import a_func

                a_func()
            """),
            module_with_imports.get_changed_source(),
        )

    def test_simple_removing_unused_imports_for_from_stars(self):
        self.mod.write(dedent("""\
            from pkg1.mod1 import *

        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual("", module_with_imports.get_changed_source())

    def test_simple_removing_unused_imports_for_nested_modules(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
        """))
        self.mod.write(dedent("""\
            import pkg1.mod1
            pkg1.mod1.a_func()"""))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            "import pkg1.mod1\npkg1.mod1.a_func()",
            module_with_imports.get_changed_source(),
        )

    def test_removing_unused_imports_and_functions_of_the_same_name(self):
        self.mod.write(dedent("""\
            def a_func():
                pass
            def a_func():
                pass
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                def a_func():
                    pass
                def a_func():
                    pass
            """),
            module_with_imports.get_changed_source(),
        )

    def test_removing_unused_imports_for_from_import_with_as(self):
        self.mod.write("a_var = 1\n")
        self.mod1.write(dedent("""\
            from mod import a_var as myvar
            a_var = myvar
        """))
        pymod = self.project.get_pymodule(self.mod1)
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                from mod import a_var as myvar
                a_var = myvar
            """),
            module_with_imports.get_changed_source(),
        )

    def test_not_removing_imports_that_conflict_with_class_names(self):
        code = dedent("""\
            import pkg1
            class A(object):
                pkg1 = 0
                def f(self):
                    a_var = pkg1
        """)
        self.mod.write(code)
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(code, module_with_imports.get_changed_source())

    def test_adding_imports(self):
        self.mod.write("\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        new_import = self.import_tools.get_import(self.mod1)
        module_with_imports.add_import(new_import)
        self.assertEqual("import pkg1.mod1\n", module_with_imports.get_changed_source())

    def test_adding_imports_no_pull_to_top(self):
        self.mod.write(dedent("""\
            import pkg2.mod3
            class A(object):
                pass

            import pkg2.mod2
        """))
        pymod = self.project.get_module("mod")
        self.project.prefs["pull_imports_to_top"] = False
        module_with_imports = self.import_tools.module_imports(pymod)
        new_import = self.import_tools.get_import(self.mod1)
        module_with_imports.add_import(new_import)
        self.assertEqual(
            dedent("""\
                import pkg2.mod3
                class A(object):
                    pass

                import pkg2.mod2
                import pkg1.mod1
            """),
            module_with_imports.get_changed_source(),
        )

    def test_adding_from_imports(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
            def another_func():
                pass
        """))
        self.mod.write("from pkg1.mod1 import a_func\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        new_import = self.import_tools.get_from_import(self.mod1, "another_func")
        module_with_imports.add_import(new_import)
        self.assertEqual(
            "from pkg1.mod1 import a_func, another_func\n",
            module_with_imports.get_changed_source(),
        )

    def test_adding_to_star_imports(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
            def another_func():
                pass
        """))
        self.mod.write("from pkg1.mod1 import *\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        new_import = self.import_tools.get_from_import(self.mod1, "another_func")
        module_with_imports.add_import(new_import)
        self.assertEqual(
            "from pkg1.mod1 import *\n", module_with_imports.get_changed_source()
        )

    def test_adding_star_imports(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
            def another_func():
                pass
        """))
        self.mod.write("from pkg1.mod1 import a_func\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        new_import = self.import_tools.get_from_import(self.mod1, "*")
        module_with_imports.add_import(new_import)
        self.assertEqual(
            "from pkg1.mod1 import *\n", module_with_imports.get_changed_source()
        )

    def test_adding_imports_and_preserving_spaces_after_imports(self):
        self.mod.write(dedent("""\
            import pkg1


            print(pkg1)
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        new_import = self.import_tools.get_import(self.pkg2)
        module_with_imports.add_import(new_import)
        self.assertEqual(
            dedent("""\
                import pkg1
                import pkg2


                print(pkg1)
            """),
            module_with_imports.get_changed_source(),
        )

    def test_not_changing_the_format_of_unchanged_imports(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
            def another_func():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import (a_func,
                another_func)
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        self.assertEqual(
            dedent("""\
                from pkg1.mod1 import (a_func,
                    another_func)
            """),
            module_with_imports.get_changed_source(),
        )

    def test_not_changing_the_format_of_unchanged_imports2(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
            def another_func():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import (a_func)
            a_func()
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                from pkg1.mod1 import (a_func)
                a_func()
            """),
            module_with_imports.get_changed_source(),
        )

    def test_removing_unused_imports_and_reoccuring_names(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
            def another_func():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import *
            from pkg1.mod1 import a_func
            a_func()
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                from pkg1.mod1 import *
                a_func()
            """),
            module_with_imports.get_changed_source(),
        )

    def test_removing_unused_imports_and_reoccuring_names2(self):
        self.mod.write(dedent("""\
            import pkg2.mod2
            import pkg2.mod3
            print(pkg2.mod2, pkg2.mod3)"""))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                import pkg2.mod2
                import pkg2.mod3
                print(pkg2.mod2, pkg2.mod3)"""),
            module_with_imports.get_changed_source(),
        )

    def test_removing_unused_imports_and_common_packages(self):
        self.mod.write(dedent("""\
            import pkg1.mod1
            import pkg1
            print(pkg1, pkg1.mod1)
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                import pkg1.mod1
                print(pkg1, pkg1.mod1)
            """),
            module_with_imports.get_changed_source(),
        )

    def test_removing_unused_imports_and_common_packages_reversed(self):
        self.mod.write(dedent("""\
            import pkg1
            import pkg1.mod1
            print(pkg1, pkg1.mod1)
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_duplicates()
        self.assertEqual(
            dedent("""\
                import pkg1.mod1
                print(pkg1, pkg1.mod1)
            """),
            module_with_imports.get_changed_source(),
        )

    def test_removing_unused_imports_and_common_packages2(self):
        self.mod.write(dedent("""\
            import pkg1.mod1
            import pkg1.mod2
            print(pkg1)
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                import pkg1.mod1
                print(pkg1)
            """),
            module_with_imports.get_changed_source(),
        )

    def test_removing_unused_imports_and_froms(self):
        self.mod1.write(dedent("""\
            def func1():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import func1
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual("", module_with_imports.get_changed_source())

    def test_removing_unused_imports_and_froms2(self):
        self.mod1.write(dedent("""\
            def func1():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import func1
            func1()"""))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                from pkg1.mod1 import func1
                func1()"""),
            module_with_imports.get_changed_source(),
        )

    def test_removing_unused_imports_and_froms3(self):
        self.mod1.write(dedent("""\
            def func1():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import func1
            def a_func():
                func1()
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                from pkg1.mod1 import func1
                def a_func():
                    func1()
            """),
            module_with_imports.get_changed_source(),
        )

    def test_removing_unused_imports_and_froms4(self):
        self.mod1.write(dedent("""\
            def func1():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import func1
            class A(object):
                def a_func(self):
                    func1()
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                from pkg1.mod1 import func1
                class A(object):
                    def a_func(self):
                        func1()
            """),
            module_with_imports.get_changed_source(),
        )

    def test_removing_unused_imports_and_getting_attributes(self):
        self.mod1.write(dedent("""\
            class A(object):
                def f(self):
                    pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import A
            var = A().f()"""))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                from pkg1.mod1 import A
                var = A().f()"""),
            module_with_imports.get_changed_source(),
        )

    def test_removing_unused_imports_function_parameters(self):
        self.mod1.write(dedent("""\
            def func1():
                pass
        """))
        self.mod.write(dedent("""\
            import pkg1
            def a_func(pkg1):
                my_var = pkg1
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                def a_func(pkg1):
                    my_var = pkg1
            """),
            module_with_imports.get_changed_source(),
        )

    def test_trivial_expanding_star_imports(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
            def another_func():
                pass
        """))
        self.mod.write("from pkg1.mod1 import *\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.expand_stars()
        self.assertEqual("", module_with_imports.get_changed_source())

    def test_expanding_star_imports(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
            def another_func():
                pass
        """))
        self.mod.write("from pkg1.mod1 import *\na_func()\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.expand_stars()
        self.assertEqual(
            "from pkg1.mod1 import a_func\na_func()\n",
            module_with_imports.get_changed_source(),
        )

    def test_removing_duplicate_imports(self):
        self.mod.write("import pkg1\nimport pkg1\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_duplicates()
        self.assertEqual("import pkg1\n", module_with_imports.get_changed_source())

    def test_removing_duplicates_and_reoccuring_names(self):
        self.mod.write("import pkg2.mod2\nimport pkg2.mod3\n")
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_duplicates()
        self.assertEqual(
            "import pkg2.mod2\nimport pkg2.mod3\n",
            module_with_imports.get_changed_source(),
        )

    def test_removing_duplicate_imports_for_froms(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
            def another_func():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1 import a_func
            from pkg1 import a_func, another_func
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_duplicates()
        self.assertEqual(
            "from pkg1 import a_func, another_func\n",
            module_with_imports.get_changed_source(),
        )

    def test_transforming_froms_to_normal_changing_imports(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import a_func
            print(a_func)
        """))
        pymod = self.project.get_module("mod")
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEqual(
            dedent("""\
                import pkg1.mod1
                print(pkg1.mod1.a_func)
            """),
            changed_module,
        )

    def test_transforming_froms_to_normal_changing_occurrences(self):
        self.mod1.write("def a_func():\n    pass\n")
        self.mod.write("from pkg1.mod1 import a_func\na_func()")
        pymod = self.project.get_module("mod")
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEqual("import pkg1.mod1\npkg1.mod1.a_func()", changed_module)

    def test_transforming_froms_to_normal_for_multi_imports(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
            def another_func():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import *
            a_func()
            another_func()
        """))
        pymod = self.project.get_module("mod")
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEqual(
            dedent("""\
                import pkg1.mod1
                pkg1.mod1.a_func()
                pkg1.mod1.another_func()
            """),
            changed_module,
        )

    def test_transform_froms_to_norm_for_multi_imports_inside_parens(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
            def another_func():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import (a_func,
                another_func)
            a_func()
            another_func()
        """))
        pymod = self.project.get_module("mod")
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEqual(
            dedent("""\
                import pkg1.mod1
                pkg1.mod1.a_func()
                pkg1.mod1.another_func()
            """),
            changed_module,
        )

    def test_transforming_froms_to_normal_from_stars(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import *
            a_func()
        """))
        pymod = self.project.get_module("mod")
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEqual(
            dedent("""\
                import pkg1.mod1
                pkg1.mod1.a_func()
            """),
            changed_module,
        )

    def test_transforming_froms_to_normal_from_stars2(self):
        self.mod1.write("a_var = 10")
        self.mod.write(dedent("""\
            import pkg1.mod1
            from pkg1.mod1 import a_var
            def a_func():
                print(pkg1.mod1, a_var)
        """))
        pymod = self.project.get_module("mod")
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEqual(
            dedent("""\
                import pkg1.mod1
                def a_func():
                    print(pkg1.mod1, pkg1.mod1.a_var)
            """),
            changed_module,
        )

    def test_transforming_froms_to_normal_from_with_alias(self):
        self.mod1.write(dedent("""\
            def a_func():
                pass
        """))
        self.mod.write(dedent("""\
            from pkg1.mod1 import a_func as another_func
            another_func()
        """))
        pymod = self.project.get_module("mod")
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEqual(
            dedent("""\
                import pkg1.mod1
                pkg1.mod1.a_func()
            """),
            changed_module,
        )

    def test_transforming_froms_to_normal_for_relatives(self):
        self.mod2.write(dedent("""\
            def a_func():
                pass
        """))
        self.mod3.write(dedent("""\
            from mod2 import *
            a_func()
        """))
        pymod = self.project.get_pymodule(self.mod3)
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEqual(
            dedent("""\
                import pkg2.mod2
                pkg2.mod2.a_func()
            """),
            changed_module,
        )

    def test_transforming_froms_to_normal_for_os_path(self):
        self.mod.write("from os import path\npath.exists('.')\n")
        pymod = self.project.get_pymodule(self.mod)
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEqual("import os\nos.path.exists('.')\n", changed_module)


    def test_transforming_froms_to_normal_kwarg_with_same_name(self):
        self.mod.write("from os import path\nfoo(path=path.join('a', 'b'))\n")
        pymod = self.project.get_pymodule(self.mod)
        changed_module = self.import_tools.froms_to_imports(pymod)
        self.assertEqual("import os\nfoo(path=os.path.join('a', 'b'))\n", changed_module)

    def test_transform_relatives_imports_to_abs_imports_doing_nothing(self):
        self.mod2.write("from pkg1 import mod1\nimport mod1\n")
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEqual(
            "from pkg1 import mod1\nimport mod1\n",
            self.import_tools.relatives_to_absolutes(pymod),
        )

    def test_transform_relatives_to_absolute_imports_for_normal_imports(self):
        self.mod2.write("import mod3\n")
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEqual(
            "import pkg2.mod3\n", self.import_tools.relatives_to_absolutes(pymod)
        )

    def test_transform_relatives_imports_to_absolute_imports_for_froms(self):
        self.mod3.write(dedent("""\
            def a_func():
                pass
        """))
        self.mod2.write("from mod3 import a_func\n")
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEqual(
            "from pkg2.mod3 import a_func\n",
            self.import_tools.relatives_to_absolutes(pymod),
        )

    def test_transform_rel_imports_to_abs_imports_for_new_relatives(self):
        self.mod3.write(dedent("""\
            def a_func():
                pass
        """))
        self.mod2.write("from .mod3 import a_func\n")
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEqual(
            "from pkg2.mod3 import a_func\n",
            self.import_tools.relatives_to_absolutes(pymod),
        )

    def test_transform_relatives_to_absolute_imports_for_normal_imports2(self):
        self.mod2.write("import mod3\nprint(mod3)")
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEqual(
            "import pkg2.mod3\nprint(pkg2.mod3)",
            self.import_tools.relatives_to_absolutes(pymod),
        )

    def test_transform_relatives_to_absolute_imports_for_aliases(self):
        self.mod2.write("import mod3 as mod3\nprint(mod3)")
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEqual(
            "import pkg2.mod3 as mod3\nprint(mod3)",
            self.import_tools.relatives_to_absolutes(pymod),
        )

    def test_organizing_imports(self):
        self.mod1.write("import mod1\n")
        pymod = self.project.get_pymodule(self.mod1)
        self.assertEqual("", self.import_tools.organize_imports(pymod))

    def test_organizing_imports_without_deduplication(self):
        contents = dedent("""\
            from pkg2 import mod2
            from pkg2 import mod3
        """)
        self.mod.write(contents)
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs["split_imports"] = True
        self.assertEqual(
            contents, self.import_tools.organize_imports(pymod, unused=False)
        )

    def test_splitting_imports(self):
        self.mod.write(dedent("""\
            from pkg1 import mod1
            from pkg2 import mod2, mod3
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs["split_imports"] = True
        self.assertEqual(
            dedent("""\
                from pkg1 import mod1
                from pkg2 import mod2
                from pkg2 import mod3
            """),
            self.import_tools.organize_imports(pymod, unused=False),
        )

    def test_splitting_imports_no_pull_to_top(self):
        self.mod.write(dedent("""\
            from pkg2 import mod3, mod4
            from pkg1 import mod2
            from pkg1 import mod1
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs["split_imports"] = True
        self.project.prefs["pull_imports_to_top"] = False
        self.assertEqual(
            dedent("""\
                from pkg1 import mod2
                from pkg1 import mod1
                from pkg2 import mod3
                from pkg2 import mod4
            """),
            self.import_tools.organize_imports(pymod, sort=False, unused=False),
        )

    def test_splitting_imports_with_filter(self):
        self.mod.write(dedent("""\
            from pkg1 import mod1, mod2
            from pkg2 import mod3, mod4
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs["split_imports"] = True

        def import_filter(stmt):
            return stmt.import_info.module_name == "pkg1"

        self.assertEqual(
            dedent("""\
                from pkg1 import mod1
                from pkg1 import mod2
                from pkg2 import mod3, mod4
            """),
            self.import_tools.organize_imports(
                pymod, unused=False, import_filter=import_filter
            ),
        )

    def test_splitting_duplicate_imports(self):
        self.mod.write(dedent("""\
            from pkg2 import mod1
            from pkg2 import mod1, mod2
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs["split_imports"] = True
        self.assertEqual(
            dedent("""\
                from pkg2 import mod1
                from pkg2 import mod2
            """),
            self.import_tools.organize_imports(pymod, unused=False),
        )

    def test_splitting_duplicate_imports2(self):
        self.mod.write(dedent("""\
            from pkg2 import mod1, mod3
            from pkg2 import mod1, mod2
            from pkg2 import mod2, mod3
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs["split_imports"] = True
        self.assertEqual(
            dedent("""\
                from pkg2 import mod1
                from pkg2 import mod2
                from pkg2 import mod3
            """),
            self.import_tools.organize_imports(pymod, unused=False),
        )

    def test_removing_self_imports(self):
        self.mod.write(dedent("""\
            import mod
            mod.a_var = 1
            print(mod.a_var)
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                a_var = 1
                print(a_var)
            """),
            self.import_tools.organize_imports(pymod),
        )

    def test_removing_self_imports2(self):
        self.mod1.write(dedent("""\
            import pkg1.mod1
            pkg1.mod1.a_var = 1
            print(pkg1.mod1.a_var)
        """))
        pymod = self.project.get_pymodule(self.mod1)
        self.assertEqual(
            dedent("""\
                a_var = 1
                print(a_var)
            """),
            self.import_tools.organize_imports(pymod),
        )

    def test_removing_self_imports_with_as(self):
        self.mod.write(dedent("""\
            import mod as mymod
            mymod.a_var = 1
            print(mymod.a_var)
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                a_var = 1
                print(a_var)
            """),
            self.import_tools.organize_imports(pymod),
        )

    def test_removing_self_imports_for_froms(self):
        self.mod1.write(dedent("""\
            from pkg1 import mod1
            mod1.a_var = 1
            print(mod1.a_var)
        """))
        pymod = self.project.get_pymodule(self.mod1)
        self.assertEqual(
            dedent("""\
                a_var = 1
                print(a_var)
            """),
            self.import_tools.organize_imports(pymod),
        )

    def test_removing_self_imports_for_froms_with_as(self):
        self.mod1.write(dedent("""\
            from pkg1 import mod1 as mymod
            mymod.a_var = 1
            print(mymod.a_var)
        """))
        pymod = self.project.get_pymodule(self.mod1)
        self.assertEqual(
            dedent("""\
                a_var = 1
                print(a_var)
            """),
            self.import_tools.organize_imports(pymod),
        )

    def test_removing_self_imports_for_froms2(self):
        self.mod.write(dedent("""\
            from mod import a_var
            a_var = 1
            print(a_var)
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                a_var = 1
                print(a_var)
            """),
            self.import_tools.organize_imports(pymod),
        )

    def test_removing_self_imports_for_froms3(self):
        self.mod.write(dedent("""\
            from mod import a_var
            a_var = 1
            print(a_var)
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                a_var = 1
                print(a_var)
            """),
            self.import_tools.organize_imports(pymod),
        )

    def test_removing_self_imports_for_froms4(self):
        self.mod.write(dedent("""\
            from mod import a_var as myvar
            a_var = 1
            print(myvar)
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                a_var = 1
                print(a_var)
            """),
            self.import_tools.organize_imports(pymod),
        )

    def test_removing_self_imports_with_no_dot_after_mod(self):
        self.mod.write(dedent("""\
            import mod
            print(mod)
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                import mod


                print(mod)
            """),
            self.import_tools.organize_imports(pymod),
        )

    def test_removing_self_imports_with_no_dot_after_mod2(self):
        self.mod.write(dedent("""\
            import mod
            a_var = 1
            print(mod\\
                    \\
                    .var)

        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                a_var = 1
                print(var)

            """),
            self.import_tools.organize_imports(pymod),
        )

    def test_removing_self_imports_for_from_import_star(self):
        self.mod.write(dedent("""\
            from mod import *
            a_var = 1
            print(myvar)
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                a_var = 1
                print(myvar)
            """),
            self.import_tools.organize_imports(pymod),
        )

    def test_not_removing_future_imports(self):
        self.mod.write("from __future__ import division\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            "from __future__ import division\n",
            self.import_tools.organize_imports(pymod),
        )

    def test_sorting_empty_imports(self):
        self.mod.write("")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual("", self.import_tools.sort_imports(pymod))

    def test_sorting_one_import(self):
        self.mod.write("import pkg1.mod1\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual("import pkg1.mod1\n", self.import_tools.sort_imports(pymod))

    def test_sorting_imports_alphabetically(self):
        self.mod.write("import pkg2.mod2\nimport pkg1.mod1\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            "import pkg1.mod1\nimport pkg2.mod2\n",
            self.import_tools.sort_imports(pymod),
        )

    def test_sorting_imports_purely_alphabetically(self):
        self.mod.write(dedent("""\
            from pkg2 import mod3 as mod0
            import pkg2.mod2
            import pkg1.mod1
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.project.prefs["sort_imports_alphabetically"] = True
        self.assertEqual(
            dedent("""\
                import pkg1.mod1
                import pkg2.mod2
                from pkg2 import mod3 as mod0
            """),
            self.import_tools.sort_imports(pymod),
        )

    def test_sorting_imports_and_froms(self):
        self.mod.write("import pkg2.mod2\nfrom pkg1 import mod1\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            "import pkg2.mod2\nfrom pkg1 import mod1\n",
            self.import_tools.sort_imports(pymod),
        )

    def test_sorting_imports_and_standard_modules(self):
        self.mod.write(dedent("""\
            import pkg1
            import sys
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                import sys

                import pkg1
            """),
            self.import_tools.sort_imports(pymod),
        )

    def test_sorting_imports_and_standard_modules2(self):
        self.mod.write(dedent("""\
            import sys

            import time
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                import sys
                import time
            """),
            self.import_tools.sort_imports(pymod),
        )

    def test_sorting_only_standard_modules(self):
        self.mod.write("import sys\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual("import sys\n", self.import_tools.sort_imports(pymod))

    def test_sorting_third_party(self):
        self.mod.write(dedent("""\
            import pkg1
            import a_third_party
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                import a_third_party

                import pkg1
            """),
            self.import_tools.sort_imports(pymod),
        )

    def test_sorting_only_third_parties(self):
        self.mod.write(dedent("""\
            import a_third_party
            a_var = 1
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                import a_third_party


                a_var = 1
            """),
            self.import_tools.sort_imports(pymod),
        )

    def test_simple_handling_long_imports(self):
        self.mod.write(dedent("""\
            import pkg1.mod1


            m = pkg1.mod1
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                import pkg1.mod1


                m = pkg1.mod1
            """),
            self.import_tools.handle_long_imports(pymod, maxdots=2),
        )

    def test_handling_long_imports_for_many_dots(self):
        self.mod.write(dedent("""\
            import p1.p2.p3.m1


            m = p1.p2.p3.m1
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                from p1.p2.p3 import m1


                m = m1
            """),
            self.import_tools.handle_long_imports(pymod, maxdots=2),
        )

    def test_handling_long_imports_for_their_length(self):
        self.mod.write(dedent("""\
            import p1.p2.p3.m1


            m = p1.p2.p3.m1
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                import p1.p2.p3.m1


                m = p1.p2.p3.m1
            """),
            self.import_tools.handle_long_imports(pymod, maxdots=3, maxlength=20),
        )

    def test_handling_long_imports_for_many_dots2(self):
        self.mod.write(dedent("""\
            import p1.p2.p3.m1


            m = p1.p2.p3.m1
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                from p1.p2.p3 import m1


                m = m1
            """),
            self.import_tools.handle_long_imports(pymod, maxdots=3, maxlength=10),
        )

    def test_handling_long_imports_with_one_letter_last(self):
        self.mod.write(dedent("""\
            import p1.p2.p3.l


            m = p1.p2.p3.l
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                from p1.p2.p3 import l


                m = l
            """),
            self.import_tools.handle_long_imports(pymod, maxdots=2),
        )

    def test_empty_removing_unused_imports_and_eating_blank_lines(self):
        self.mod.write(dedent("""\
            import pkg1
            import pkg2


            print(pkg1)
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        module_with_imports.remove_unused_imports()
        self.assertEqual(
            dedent("""\
                import pkg1


                print(pkg1)
            """),
            module_with_imports.get_changed_source(),
        )

    def test_sorting_imports_moving_to_top(self):
        self.mod.write(dedent("""\
            import mod
            def f():
                print(mod, pkg1, pkg2)
            import pkg1
            import pkg2
        """))
        pymod = self.project.get_module("mod")
        self.assertEqual(
            dedent("""\
                import mod
                import pkg1
                import pkg2


                def f():
                    print(mod, pkg1, pkg2)
            """),
            self.import_tools.sort_imports(pymod),
        )

    def test_sorting_imports_moving_to_top2(self):
        self.mod.write(dedent("""\
            def f():
                print(mod)
            import mod
        """))
        pymod = self.project.get_module("mod")
        self.assertEqual(
            dedent("""\
                import mod


                def f():
                    print(mod)
            """),
            self.import_tools.sort_imports(pymod),
        )

    # Sort pulls imports to the top anyway
    def test_sorting_imports_no_pull_to_top(self):
        code = dedent("""\
            import pkg2
            def f():
                print(mod, pkg1, pkg2)
            import pkg1
            import mod
        """)
        self.mod.write(code)
        pymod = self.project.get_module("mod")
        self.project.prefs["pull_imports_to_top"] = False
        self.assertEqual(
            dedent("""\
                import mod
                import pkg1
                import pkg2


                def f():
                    print(mod, pkg1, pkg2)
            """),
            self.import_tools.sort_imports(pymod),
        )

    def test_sorting_imports_moving_to_top_and_module_docs(self):
        self.mod.write(dedent('''\
            """
            docs
            """
            def f():
                print(mod)
            import mod
        '''))
        pymod = self.project.get_module("mod")
        self.assertEqual(
            dedent('''\
                """
                docs
                """
                import mod


                def f():
                    print(mod)
            '''),
            self.import_tools.sort_imports(pymod),
        )

    def test_sorting_imports_moving_to_top_and_module_docs2(self):
        self.mod.write(dedent('''\
            """
            docs
            """


            import bbb
            import aaa
            def f():
                print(mod)
            import mod
        '''))
        pymod = self.project.get_module("mod")
        self.assertEqual(
            dedent('''\
                """
                docs
                """


                import aaa
                import bbb

                import mod


                def f():
                    print(mod)
            '''),
            self.import_tools.sort_imports(pymod),
        )

    def test_get_changed_source_preserves_blank_lines(self):
        self.mod.write(dedent("""\
            __author__ = "author"

            import aaa

            import bbb

            def f():
                print(mod)
        """))
        pymod = self.project.get_module("mod")
        module_with_imports = self.import_tools.module_imports(pymod)
        self.assertEqual(
            dedent("""\
                import aaa

                import bbb

                __author__ = "author"

                def f():
                    print(mod)
            """),
            module_with_imports.get_changed_source(),
        )

    def test_sorting_future_imports(self):
        self.mod.write(dedent("""\
            import os
            from __future__ import division
        """))
        pymod = self.project.get_module("mod")
        self.assertEqual(
            dedent("""\
                from __future__ import division

                import os
            """),
            self.import_tools.sort_imports(pymod),
        )

    def test_organizing_imports_all_star(self):
        code = expected = dedent("""\
            from package import some_name


            __all__ = ["some_name"]
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    def test_organizing_imports_all_star_with_variables(self):
        code = expected = dedent("""\
            from package import name_one, name_two


            if something():
                foo = 'name_one'
            else:
                foo = 'name_two'
            __all__ = [foo]
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    def test_organizing_imports_all_star_with_inline_if(self):
        code = expected = dedent("""\
            from package import name_one, name_two


            __all__ = ['name_one' if something() else 'name_two']
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    @testutils.only_for_versions_higher("3")
    def test_organizing_imports_all_star_tolerates_non_list_of_str_1(self):
        code = expected = dedent("""\
            from package import name_one, name_two


            foo = 'name_two'
            __all__ = [bar, *abc] + mylist
            __all__ = [foo, 'name_one', *abc]
            __all__ = [it for it in mylist]
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    def test_organizing_imports_all_star_assigned_name_alias(self):
        code = expected = dedent("""\
            from package import name_one, name_two


            foo = ['name_one', 'name_two']
            __all__ = foo
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    def test_organizing_imports_all_star_imported_name_alias(self):
        self.mod1.write("foo = ['name_one', 'name_two']")
        self.mod2.write("from pkg1.mod1 import foo")
        code = expected = dedent("""\
            from package import name_one, name_two

            from pkg2.mod2 import foo


            __all__ = foo
        """)
        self.mod3.write(code)
        pymod = self.project.get_pymodule(self.mod3)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    def test_organizing_imports_all_star_tolerates_non_list_of_str_2(self):
        code = expected = dedent("""\
            from package import name_one, name_two


            foo = 'name_two'
            __all__ = [foo, 3, 'name_one']
            __all__ = [it for it in mylist]
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    def test_organizing_imports_all_star_plusjoin(self):
        code = expected = dedent("""\
            from package import name_one, name_two


            foo = ['name_two']
            __all__ = ['name_one'] + foo
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    def test_organizing_imports_all_star_starjoin(self):
        code = expected = dedent("""\
            from package import name_one, name_two


            foo = ['name_two']
            __all__ = ['name_one', *foo]
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    @testutils.time_limit(60)
    def test_organizing_imports_all_star_no_infinite_loop(self):
        code = expected = dedent("""\
            from package import name_one, name_two


            foo = bar
            bar = foo
            __all__ = [foo, 'name_one', 'name_two']
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    def test_organizing_imports_all_star_resolve_imported_name(self):
        self.mod1.write("foo = 'name_one'")

        code = expected = dedent("""\
            from package import name_one, name_two

            from pkg1.mod1 import foo


            __all__ = [foo, 'name_two']
        """)
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    def test_organizing_imports_undefined_variable(self):
        code = expected = dedent("""\
            from foo import some_name


            __all__ = ['some_name', undefined_variable]
        """)
        self.mod1.write(code)

        pymod = self.project.get_pymodule(self.mod1)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    def test_organizing_imports_undefined_variable_with_imported_name(self):
        self.mod1.write("")
        self.mod2.write("from pkg1.mod1 import undefined_variable")

        code = expected = dedent("""\
            from pkg2.mod2 import undefined_variable


            __all__ = undefined_variable
        """)
        self.mod3.write(code)

        pymod = self.project.get_pymodule(self.mod3)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    def test_organizing_indirect_all_star_import(self):
        self.mod1.write("some_name = 1")
        self.mod2.write(dedent("""\
            __all__ = ['some_name', *imported_all]
        """))

        code = expected = dedent("""\
            from mod1 import some_name

            from mod2 import __all__
        """)
        self.mod3.write(code)

        pymod = self.project.get_pymodule(self.mod3)
        self.assertEqual(expected, self.import_tools.organize_imports(pymod))

    def test_customized_import_organization(self):
        self.mod.write(dedent("""\
            import sys
            import sys
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            "import sys\n", self.import_tools.organize_imports(pymod, unused=False)
        )

    def test_customized_import_organization2(self):
        self.mod.write("import sys\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            "import sys\n", self.import_tools.organize_imports(pymod, unused=False)
        )

    def test_customized_import_organization3(self):
        self.mod.write(dedent("""\
            import sys
            import mod


            var = 1
            print(mod.var)
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                import sys


                var = 1
                print(var)
            """),
            self.import_tools.organize_imports(pymod, unused=False),
        )

    def test_trivial_filtered_expand_stars(self):
        self.pkg1.get_child("__init__.py").write("var1 = 1\n")
        self.pkg2.get_child("__init__.py").write("var2 = 1\n")
        self.mod.write(dedent("""\
            from pkg1 import *
            from pkg2 import *

            print(var1, var2)
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                from pkg1 import *
                from pkg2 import *

                print(var1, var2)
            """),
            self.import_tools.expand_stars(pymod, lambda stmt: False),
        )

    def _line_filter(self, lineno):
        def import_filter(import_stmt):
            return import_stmt.start_line <= lineno < import_stmt.end_line

        return import_filter

    def test_filtered_expand_stars(self):
        self.pkg1.get_child("__init__.py").write("var1 = 1\n")
        self.pkg2.get_child("__init__.py").write("var2 = 1\n")
        self.mod.write(dedent("""\
            from pkg1 import *
            from pkg2 import *

            print(var1, var2)
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                from pkg1 import *
                from pkg2 import var2

                print(var1, var2)
            """),
            self.import_tools.expand_stars(pymod, self._line_filter(2)),
        )

    def test_filtered_relative_to_absolute(self):
        self.mod3.write("var = 1")
        self.mod2.write("import mod3\n\nprint(mod3.var)\n")
        pymod = self.project.get_pymodule(self.mod2)
        self.assertEqual(
            dedent("""\
                import mod3

                print(mod3.var)
            """),
            self.import_tools.relatives_to_absolutes(pymod, lambda stmt: False),
        )
        self.assertEqual(
            dedent("""\
                import pkg2.mod3

                print(pkg2.mod3.var)
            """),
            self.import_tools.relatives_to_absolutes(pymod, self._line_filter(1)),
        )

    def test_filtered_froms_to_normals(self):
        self.pkg1.get_child("__init__.py").write("var1 = 1\n")
        self.pkg2.get_child("__init__.py").write("var2 = 1\n")
        self.mod.write(dedent("""\
            from pkg1 import var1
            from pkg2 import var2

            print(var1, var2)
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                from pkg1 import var1
                from pkg2 import var2

                print(var1, var2)
            """),
            self.import_tools.expand_stars(pymod, lambda stmt: False),
        )
        self.assertEqual(
            dedent("""\
                from pkg1 import var1
                import pkg2

                print(var1, pkg2.var2)
            """),
            self.import_tools.froms_to_imports(pymod, self._line_filter(2)),
        )

    def test_filtered_froms_to_normals2(self):
        self.pkg1.get_child("__init__.py").write("var1 = 1\n")
        self.pkg2.get_child("__init__.py").write("var2 = 1\n")
        self.mod.write(dedent("""\
            from pkg1 import *
            from pkg2 import *

            print(var1, var2)
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                from pkg1 import *
                import pkg2

                print(var1, pkg2.var2)
            """),
            self.import_tools.froms_to_imports(pymod, self._line_filter(2)),
        )

    def test_filtered_handle_long_imports(self):
        self.mod.write(dedent("""\
            import p1.p2.p3.m1
            import pkg1.mod1


            m = p1.p2.p3.m1, pkg1.mod1
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                import p1.p2.p3.m1
                from pkg1 import mod1


                m = p1.p2.p3.m1, mod1
            """),
            self.import_tools.handle_long_imports(
                pymod, maxlength=5, import_filter=self._line_filter(2)
            ),
        )

    def test_filtering_and_import_actions_with_more_than_one_phase(self):
        self.pkg1.get_child("__init__.py").write("var1 = 1\n")
        self.pkg2.get_child("__init__.py").write("var2 = 1\n")
        self.mod.write(dedent("""\
            from pkg1 import *
            from pkg2 import *

            print(var2)
        """))
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            dedent("""\
                from pkg2 import *

                print(var2)
            """),
            self.import_tools.expand_stars(pymod, self._line_filter(1)),
        )

    def test_non_existent_module_and_used_imports(self):
        self.mod.write(dedent("""\
            from does_not_exist import func

            func()
        """))
        pymod = self.project.get_module("mod")

        module_with_imports = self.import_tools.module_imports(pymod)
        imports = module_with_imports.get_used_imports(pymod)
        self.assertEqual(1, len(imports))


class AddImportTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()

        self.mod1 = testutils.create_module(self.project, "mod1")
        self.mod2 = testutils.create_module(self.project, "mod2")
        self.pkg = testutils.create_package(self.project, "pkg")
        self.mod3 = testutils.create_module(self.project, "mod3", self.pkg)

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def test_normal_imports(self):
        self.mod2.write("myvar = None\n")
        self.mod1.write("\n")
        pymod = self.project.get_module("mod1")
        result, name = add_import(self.project, pymod, "mod2", "myvar")
        self.assertEqual("import mod2\n", result)
        self.assertEqual("mod2.myvar", name)

    def test_not_reimporting_a_name(self):
        self.mod2.write("myvar = None\n")
        self.mod1.write("from mod2 import myvar\n")
        pymod = self.project.get_module("mod1")
        result, name = add_import(self.project, pymod, "mod2", "myvar")
        self.assertEqual("from mod2 import myvar\n", result)
        self.assertEqual("myvar", name)

    def test_adding_import_when_siblings_are_imported(self):
        self.mod2.write("var1 = None\nvar2 = None\n")
        self.mod1.write("from mod2 import var1\n")
        pymod = self.project.get_module("mod1")
        result, name = add_import(self.project, pymod, "mod2", "var2")
        self.assertEqual("from mod2 import var1, var2\n", result)
        self.assertEqual("var2", name)

    def test_adding_import_when_the_package_is_imported(self):
        self.pkg.get_child("__init__.py").write("var1 = None\n")
        self.mod3.write("var2 = None\n")
        self.mod1.write("from pkg import var1\n")
        pymod = self.project.get_module("mod1")
        result, name = add_import(self.project, pymod, "pkg.mod3", "var2")
        self.assertEqual("from pkg import var1, mod3\n", result)
        self.assertEqual("mod3.var2", name)

    def test_adding_import_for_modules_instead_of_names(self):
        self.pkg.get_child("__init__.py").write("var1 = None\n")
        self.mod3.write("\n")
        self.mod1.write("from pkg import var1\n")
        pymod = self.project.get_module("mod1")
        result, name = add_import(self.project, pymod, "pkg.mod3", None)
        self.assertEqual("from pkg import var1, mod3\n", result)
        self.assertEqual("mod3", name)

    def test_adding_import_for_modules_with_normal_duplicate_imports(self):
        self.pkg.get_child("__init__.py").write("var1 = None\n")
        self.mod3.write("\n")
        self.mod1.write("import pkg.mod3\n")
        pymod = self.project.get_module("mod1")
        result, name = add_import(self.project, pymod, "pkg.mod3", None)
        self.assertEqual("import pkg.mod3\n", result)
        self.assertEqual("pkg.mod3", name)
