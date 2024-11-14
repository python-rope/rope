from __future__ import annotations

import unittest
from textwrap import dedent
from typing import TYPE_CHECKING, Union

from rope.base import exceptions
from rope.refactor import move
from ropetest import testutils


if TYPE_CHECKING:
    from rope.base import resources, project

class MoveRefactoringTest(unittest.TestCase):
    project: project.Project
    mod1: resources.File
    mod2: resources.File
    mod3: resources.File
    pkg: resources.Folder
    mod4: resources.File
    mod5: resources.File
    origin_module: resources.File
    destination_module: resources.File
    origin_module_in_pkg: resources.File
    destination_module_in_pkg: resources.File
    destination_pkg_root: resources.Folder

    def setUp(self) -> None:
        super().setUp()
        self.project = testutils.sample_project()
        self.mod1 = testutils.create_module(self.project, "mod1")
        self.mod2 = testutils.create_module(self.project, "mod2")
        self.mod3 = testutils.create_module(self.project, "mod3")
        self.pkg = testutils.create_package(self.project, "pkg")
        self.mod4 = testutils.create_module(self.project, "mod4", self.pkg)
        self.mod5 = testutils.create_module(self.project, "mod5", self.pkg)
        self.origin_module = testutils.create_module(self.project, "origin_module")
        self.destination_module = testutils.create_module(self.project, "destination_module")
        self.origin_module_in_pkg = testutils.create_module(self.project, "origin_module_in_pkg", self.pkg)
        self.destination_module_in_pkg = testutils.create_module(self.project, "destination_module_in_pkg", self.pkg)
        self.destination_pkg_root = testutils.create_package(self.project, "destination_pkg_root")

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def _move(
        self,
        resource: Union[resources.File, resources.Folder],
        offset: Union[int, None],
        dest_resource: Union[str, resources.File, resources.Folder],
    ):
        mover = move.create_move(self.project, resource, offset)
        changes = mover.get_changes(dest_resource)
        self.project.do(changes)

    def _move_to_attr(
        self,
        resource: Union[resources.File, resources.Folder],
        offset: Union[int, None],
        dest_attr: str,
        *,
        new_name: str,
    ):
        mover = move.create_move(self.project, resource, offset)
        assert isinstance(mover, move.MoveMethod)
        changes = mover.get_changes(dest_attr, new_name=new_name)
        self.project.do(changes)

    def test_move_constant(self) -> None:
        self.origin_module.write("foo = 123\n")
        self._move(self.origin_module, self.origin_module.read().index("foo") + 1, self.destination_module)
        self.assertEqual("", self.origin_module.read())
        self.assertEqual("foo = 123\n", self.destination_module.read())

    def test_move_constant_2(self) -> None:
        self.origin_module.write("bar = 321\nfoo = 123\n")
        self._move(self.origin_module, self.origin_module.read().index("foo") + 1, self.destination_module)
        self.assertEqual("bar = 321\n", self.origin_module.read())
        self.assertEqual("foo = 123\n", self.destination_module.read())

    def test_move_target_is_module_name(self) -> None:
        self.origin_module.write("foo = 123\n")
        self._move(self.origin_module, self.origin_module.read().index("foo") + 1, "destination_module")
        self.assertEqual("", self.origin_module.read())
        self.assertEqual("foo = 123\n", self.destination_module.read())

    def test_move_target_is_package_name(self) -> None:
        self.origin_module.write("foo = 123\n")
        self._move(self.origin_module, self.origin_module.read().index("foo") + 1, "pkg.destination_module_in_pkg")
        self.assertEqual("", self.origin_module.read())
        self.assertEqual("foo = 123\n", self.destination_module_in_pkg.read())

    def test_move_constant_multiline(self) -> None:
        self.origin_module.write(dedent("""\
            foo = (
                123
            )
        """))
        self._move(self.origin_module, self.origin_module.read().index("foo") + 1, self.destination_module)
        self.assertEqual("", self.origin_module.read())
        self.assertEqual(
            dedent("""\
                foo = (
                    123
                )
            """),
            self.destination_module.read(),
        )

    def test_move_constant_multiple_statements(self) -> None:
        self.origin_module.write(dedent("""\
            foo = 123
            foo += 3
            foo = 4
        """))
        self._move(self.origin_module, self.origin_module.read().index("foo") + 1, self.destination_module)
        self.assertEqual(
            dedent("""\
                import destination_module
                destination_module.foo += 3
                destination_module.foo = 4
            """),
            self.origin_module.read(),
        )
        self.assertEqual("foo = 123\n", self.destination_module.read())

    def test_simple_moving(self) -> None:
        """Move a global class definition"""
        self.origin_module.write(dedent("""\
            class AClass(object):
                pass
        """))
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module)
        self.assertEqual("", self.origin_module.read())
        self.assertEqual(
            dedent("""\
                class AClass(object):
                    pass
            """),
            self.destination_module.read(),
        )

    def test_moving_with_comment_prefix(self) -> None:
        """Comments above the moved class are moved to the destination module"""
        self.origin_module.write(dedent("""\
            a = 1
            # 1
            # 2
            class AClass(object):
                pass
        """))
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module)
        self.assertEqual("a = 1\n", self.origin_module.read())
        self.assertEqual(
            dedent("""\
                # 1
                # 2
                class AClass(object):
                    pass
            """),
            self.destination_module.read(),
        )

    def test_moving_with_comment_prefix_imports(self) -> None:
        self.origin_module.write(dedent("""\
            import foo
            a = 1
            # 1
            # 2
            class AClass(foo.FooClass):
                pass
        """))
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module)
        self.assertEqual("a = 1\n", self.origin_module.read())
        self.assertEqual(
            dedent("""\
                import foo


                # 1
                # 2
                class AClass(foo.FooClass):
                    pass
            """),
            self.destination_module.read(),
        )

    def test_changing_other_modules_replacing_normal_imports(self) -> None:
        """
        When moving a class from origin_module to destination_module,
        references to the class in mod3 is updated to point to
        destination_module
        """
        self.origin_module.write(dedent("""\
            class AClass(object):
                pass
        """))
        self.mod3.write(dedent("""\
            import origin_module
            a_var = origin_module.AClass()
        """))
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module)
        self.assertEqual(
            dedent("""\
                import destination_module
                a_var = destination_module.AClass()
            """),
            self.mod3.read(),
        )

    def test_changing_other_modules_adding_normal_imports(self) -> None:
        self.origin_module.write(dedent("""\
            class AClass(object):
                pass
            def a_function():
                pass
        """))
        self.mod3.write(dedent("""\
            import origin_module
            a_var = origin_module.AClass()
            origin_module.a_function()"""))
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module)
        self.assertEqual(
            dedent("""\
                import origin_module
                import destination_module
                a_var = destination_module.AClass()
                origin_module.a_function()"""),
            self.mod3.read(),
        )

    def test_adding_imports_prefer_from_module(self) -> None:
        self.project.prefs["prefer_module_from_imports"] = True
        self.origin_module.write(dedent("""\
            class AClass(object):
                pass
            def a_function():
                pass
        """))
        self.mod3.write(dedent("""\
            import origin_module
            a_var = origin_module.AClass()
            origin_module.a_function()"""))
        # Move to destination_module_in_pkg which is in a different package
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module_in_pkg)
        self.assertEqual(
            dedent("""\
                import origin_module
                from pkg import destination_module_in_pkg
                a_var = destination_module_in_pkg.AClass()
                origin_module.a_function()"""),
            self.mod3.read(),
        )

    def test_adding_imports_preferred_import_style_is_normal_import(self) -> None:
        self.project.prefs.imports.preferred_import_style = "normal-import"
        self.origin_module.write(dedent("""\
            class AClass(object):
                pass
            def a_function():
                pass
        """))
        self.mod3.write(dedent("""\
            import origin_module
            a_var = origin_module.AClass()
            origin_module.a_function()"""))
        # Move to destination_module_in_pkg which is in a different package
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module_in_pkg)
        self.assertEqual(
            dedent("""\
                import origin_module
                import pkg.destination_module_in_pkg
                a_var = pkg.destination_module_in_pkg.AClass()
                origin_module.a_function()"""),
            self.mod3.read(),
        )

    def test_adding_imports_preferred_import_style_is_from_module(self) -> None:
        self.project.prefs.imports.preferred_import_style = "from-module"
        self.origin_module.write(dedent("""\
            class AClass(object):
                pass
            def a_function():
                pass
        """))
        self.mod3.write(dedent("""\
            import origin_module
            a_var = origin_module.AClass()
            origin_module.a_function()"""))
        # Move to destination_module_in_pkg which is in a different package
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module_in_pkg)
        self.assertEqual(
            dedent("""\
                import origin_module
                from pkg import destination_module_in_pkg
                a_var = destination_module_in_pkg.AClass()
                origin_module.a_function()"""),
            self.mod3.read(),
        )

    def test_adding_imports_preferred_import_style_is_from_global(self) -> None:
        self.project.prefs.imports.preferred_import_style = "from-global"
        self.origin_module.write(dedent("""\
            class AClass(object):
                pass
            def a_function():
                pass
        """))
        self.mod3.write(dedent("""\
            import origin_module
            a_var = origin_module.AClass()
            origin_module.a_function()"""))
        # Move to destination_module_in_pkg which is in a different package
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module_in_pkg)
        self.assertEqual(
            dedent("""\
                import origin_module
                from pkg.destination_module_in_pkg import AClass
                a_var = AClass()
                origin_module.a_function()"""),
            self.mod3.read(),
        )

    def test_adding_imports_noprefer_from_module(self) -> None:
        self.project.prefs["prefer_module_from_imports"] = False
        self.origin_module.write(dedent("""\
            class AClass(object):
                pass
            def a_function():
                pass
        """))
        self.mod3.write(dedent("""\
            import origin_module
            a_var = origin_module.AClass()
            origin_module.a_function()"""))
        # Move to destination_module_in_pkg which is in a different package
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module_in_pkg)
        self.assertEqual(
            dedent("""\
                import origin_module
                import pkg.destination_module_in_pkg
                a_var = pkg.destination_module_in_pkg.AClass()
                origin_module.a_function()"""),
            self.mod3.read(),
        )

    def test_adding_imports_prefer_from_module_top_level_module(self) -> None:
        self.project.prefs["prefer_module_from_imports"] = True
        self.origin_module.write(dedent("""\
            class AClass(object):
                pass
            def a_function():
                pass
        """))
        self.mod3.write(dedent("""\
            import origin_module
            a_var = origin_module.AClass()
            origin_module.a_function()"""))
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module)
        self.assertEqual(
            dedent("""\
                import origin_module
                import destination_module
                a_var = destination_module.AClass()
                origin_module.a_function()"""),
            self.mod3.read(),
        )

    def test_changing_other_modules_removing_from_imports(self) -> None:
        self.origin_module.write(dedent("""\
            class AClass(object):
                pass
        """))
        self.mod3.write(dedent("""\
            from origin_module import AClass
            a_var = AClass()
        """))
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module)
        self.assertEqual(
            dedent("""\
                import destination_module
                a_var = destination_module.AClass()
            """),
            self.mod3.read(),
        )

    def test_changing_source_module(self) -> None:
        """
        Add import statements to the source module as the moved class now lives
        in destination_module.
        """
        self.origin_module.write(dedent("""\
            class AClass(object):
                pass
            a_var = AClass()
        """))
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module)
        self.assertEqual(
            dedent("""\
                import destination_module
                a_var = destination_module.AClass()
            """),
            self.origin_module.read(),
        )

    def test_changing_destination_module(self) -> None:
        """
        Remove import statements in the destination module as the moved class
        can now be referenced from destination_module without import.
        """
        self.origin_module.write(dedent("""\
            class AClass(object):
                pass
        """))
        self.destination_module.write(dedent("""\
            from origin_module import AClass
            a_var = AClass()
        """))
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module)
        self.assertEqual(
            dedent("""\
                class AClass(object):
                    pass
                a_var = AClass()
            """),
            self.destination_module.read(),
        )

    def test_folder_destination(self) -> None:
        folder = self.project.root.create_folder("folder")
        self.origin_module.write(dedent("""\
            class AClass(object):
                pass
        """))
        with self.assertRaisesRegex(
            exceptions.RefactoringError,
            r"Move destination for non-modules should not be folders\.",
        ) as e:
            self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, folder)

    def test_raising_exception_for_moving_non_global_elements(self) -> None:
        self.origin_module.write(dedent("""\
            def a_func():
                class AClass(object):
                    pass
        """))
        with self.assertRaisesRegex(
            exceptions.RefactoringError,
            r"Move only works on global classes/functions/variables, modules and methods\.",
        ):
            self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module)

    def test_raising_an_exception_for_moving_non_global_variable(self) -> None:
        code = dedent("""\
            class TestClass:
                CONSTANT = 5
        """)
        self.origin_module.write(code)
        with self.assertRaisesRegex(
            exceptions.RefactoringError,
            "Move refactoring should be performed on a global class, function or variable\.",
        ):
            mover = move.create_move(
                self.project, self.origin_module, code.index("CONSTANT") + 1
            )

    def test_raising_exception_for_moving_glob_elements_to_the_same_module(self) -> None:
        self.origin_module.write(dedent("""\
            def a_func():
                pass
        """))
        with self.assertRaisesRegex(
            exceptions.RefactoringError,
            "Moving global elements to the same module\.",
        ):
            self._move(self.origin_module, self.origin_module.read().index("a_func"), self.origin_module)

    def test_moving_used_imports_to_destination_module(self) -> None:
        """
        Add import statements for imported references used by the moved
        function to the destination module.
        """
        self.mod3.write("a_var = 10")
        code = dedent("""\
            import mod3
            from mod3 import a_var
            def a_func():
                print(mod3, a_var)
        """)
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("a_func") + 1, self.destination_module)
        expected = dedent("""\
            import mod3
            from mod3 import a_var


            def a_func():
                print(mod3, a_var)
        """)
        self.assertEqual(expected, self.destination_module.read())

    def test_moving_used_names_to_destination_module2(self) -> None:
        """
        Add import statements for references to globals in the source module
        used by the moved function to the destination module.
        """
        code = dedent("""\
            a_var = 10
            def a_func():
                print(a_var)
        """)
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("a_func") + 1, self.destination_module)
        self.assertEqual(
            dedent("""\
                a_var = 10
            """),
            self.origin_module.read(),
        )
        expected = dedent("""\
            from origin_module import a_var


            def a_func():
                print(a_var)
        """)
        self.assertEqual(expected, self.destination_module.read())

    def test_moving_used_underlined_names_to_destination_module(self) -> None:
        code = dedent("""\
            _var = 10
            def a_func():
                print(_var)
        """)
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("a_func") + 1, self.destination_module)
        expected = dedent("""\
            from origin_module import _var


            def a_func():
                print(_var)
        """)
        self.assertEqual(expected, self.destination_module.read())

    def test_moving_and_used_relative_imports(self) -> None:
        """Move global function where the source module is in a package"""
        code = dedent("""\
            import mod5
            def a_func():
                print(mod5)
        """)
        self.origin_module_in_pkg.write(code)
        self._move(self.origin_module_in_pkg, code.index("a_func") + 1, self.destination_module)
        expected = dedent("""\
            import pkg.mod5


            def a_func():
                print(pkg.mod5)
        """)
        self.assertEqual(expected, self.destination_module.read())
        self.assertEqual("", self.origin_module_in_pkg.read())

    def test_moving_modules_into_package(self) -> None:
        """Move global function where the destination module is in a package"""
        code = dedent("""\
            import mod1
            print(mod1)"""
        )
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("mod1") + 1, self.destination_pkg_root)
        expected = dedent("""\
            import destination_pkg_root.mod1
            print(destination_pkg_root.mod1)"""
        )
        self.assertEqual(expected, self.origin_module.read())
        self.assertTrue(
            not self.mod1.exists() and self.project.find_module("destination_pkg_root.mod1") is not None
        )

    def test_moving_modules_and_removing_out_of_date_imports(self) -> None:
        code = dedent("""\
            import pkg.mod4
            print(pkg.mod4)""")
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("mod4") + 1, self.project.root)
        expected = dedent("""\
            import mod4
            print(mod4)""")
        self.assertEqual(expected, self.origin_module.read())
        self.assertTrue(self.project.find_module("mod4") is not None)

    def test_moving_modules_and_removing_out_of_date_froms(self) -> None:
        code = dedent("""\
            from pkg import mod4
            print(mod4)""")
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("mod4") + 1, self.project.root)
        self.assertEqual(
            dedent("""\
                import mod4
                print(mod4)"""
            ), 
            self.origin_module.read(),
        )

    def test_moving_modules_and_removing_out_of_date_froms2(self) -> None:
        self.mod4.write("a_var = 10")
        code = dedent("""\
            from pkg.mod4 import a_var
            print(a_var)
        """)
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("mod4") + 1, self.project.root)
        expected = dedent("""\
            from mod4 import a_var
            print(a_var)
        """)
        self.assertEqual(expected, self.origin_module.read())

    def test_moving_modules_and_relative_import(self) -> None:
        self.mod4.write(dedent("""\
            import mod5
            print(mod5)
        """))
        code = dedent("""\
            import pkg.mod4
            print(pkg.mod4)""")
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("mod4") + 1, self.project.root)
        moved = self.project.find_module("mod4")
        assert moved
        expected = dedent("""\
            import pkg.mod5
            print(pkg.mod5)
        """)
        self.assertEqual(expected, moved.read())

    def test_moving_module_kwarg_same_name_as_old(self) -> None:
        self.origin_module.write(dedent("""\
            def foo(origin_module=0):
                pass"""))
        code = dedent("""\
            import origin_module
            origin_module.foo(origin_module=1)""")
        self.mod2.write(code)
        self._move(self.origin_module, None, self.destination_pkg_root)
        moved = self.project.find_module("mod2")
        assert moved
        expected = dedent("""\
            import destination_pkg_root.origin_module
            destination_pkg_root.origin_module.foo(origin_module=1)""")
        self.assertEqual(expected, moved.read())

    def test_moving_packages(self) -> None:
        code = dedent("""\
            import pkg.mod4
            print(pkg.mod4)""")
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("pkg") + 1, self.destination_pkg_root)
        self.assertFalse(self.pkg.exists())
        self.assertTrue(self.project.find_module("destination_pkg_root.pkg.mod4") is not None)
        self.assertTrue(self.project.find_module("destination_pkg_root.pkg.mod4") is not None)
        self.assertTrue(self.project.find_module("destination_pkg_root.pkg.mod5") is not None)
        expected = dedent("""\
            import destination_pkg_root.pkg.mod4
            print(destination_pkg_root.pkg.mod4)""")
        self.assertEqual(expected, self.origin_module.read())

    def test_moving_modules_with_self_imports(self) -> None:
        self.mod1.write(dedent("""\
            import mod1
            print(mod1)
        """))
        self.origin_module.write(dedent("""\
            import mod1
        """))
        self._move(self.origin_module, self.origin_module.read().index("mod1") + 1, self.destination_pkg_root)
        moved = self.project.find_module("destination_pkg_root.mod1")
        assert moved
        self.assertEqual(
            dedent("""\
                import destination_pkg_root.mod1
                print(destination_pkg_root.mod1)
            """),
            moved.read(),
        )

    def test_moving_modules_with_from_imports(self) -> None:
        code = dedent("""\
            from pkg import mod4
            print(mod4)""")
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("pkg") + 1, self.destination_pkg_root)
        self.assertFalse(self.pkg.exists())
        self.assertTrue(self.project.find_module("destination_pkg_root.pkg.mod4") is not None)
        self.assertTrue(self.project.find_module("destination_pkg_root.pkg.mod5") is not None)
        expected = dedent("""\
            from destination_pkg_root.pkg import mod4
            print(mod4)""")
        self.assertEqual(expected, self.origin_module.read())

    def test_moving_modules_with_from_import(self) -> None:
        pkg2 = testutils.create_package(self.project, "pkg2")
        pkg3 = testutils.create_package(self.project, "pkg3", pkg2)
        pkg4 = testutils.create_package(self.project, "pkg4", pkg3)
        code = dedent("""\
            from pkg import origin_module_in_pkg
            print(origin_module_in_pkg)""")
        self.mod1.write(code)
        self._move(self.origin_module_in_pkg, None, pkg4)
        self.assertTrue(self.project.find_module("pkg2.pkg3.pkg4.origin_module_in_pkg") is not None)
        expected = dedent("""\
            from pkg2.pkg3.pkg4 import origin_module_in_pkg
            print(origin_module_in_pkg)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_modules_with_multi_from_imports(self) -> None:
        pkg2 = testutils.create_package(self.project, "pkg2")
        pkg3 = testutils.create_package(self.project, "pkg3", pkg2)
        pkg4 = testutils.create_package(self.project, "pkg4", pkg3)
        code = dedent("""\
            from pkg import origin_module_in_pkg, mod5
            print(origin_module_in_pkg)""")
        self.mod1.write(code)
        self._move(self.origin_module_in_pkg, None, pkg4)
        self.assertTrue(self.project.find_module("pkg2.pkg3.pkg4.origin_module_in_pkg") is not None)
        expected = dedent("""\
            from pkg import mod5
            from pkg2.pkg3.pkg4 import origin_module_in_pkg
            print(origin_module_in_pkg)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_modules_with_from_and_normal_imports(self) -> None:
        pkg2 = testutils.create_package(self.project, "pkg2")
        pkg3 = testutils.create_package(self.project, "pkg3", pkg2)
        pkg4 = testutils.create_package(self.project, "pkg4", pkg3)
        code = dedent("""\
            from pkg import origin_module_in_pkg
            import pkg.origin_module_in_pkg
            print(origin_module_in_pkg)
            print(pkg.origin_module_in_pkg)""")
        self.mod1.write(code)
        self._move(self.origin_module_in_pkg, None, pkg4)
        self.assertTrue(self.project.find_module("pkg2.pkg3.pkg4.origin_module_in_pkg") is not None)
        expected = dedent("""\
            import pkg2.pkg3.pkg4.origin_module_in_pkg
            from pkg2.pkg3.pkg4 import origin_module_in_pkg
            print(origin_module_in_pkg)
            print(pkg2.pkg3.pkg4.origin_module_in_pkg)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_modules_with_normal_and_from_imports(self) -> None:
        pkg2 = testutils.create_package(self.project, "pkg2")
        pkg3 = testutils.create_package(self.project, "pkg3", pkg2)
        pkg4 = testutils.create_package(self.project, "pkg4", pkg3)
        code = dedent("""\
            import pkg.origin_module_in_pkg
            from pkg import origin_module_in_pkg
            print(origin_module_in_pkg)
            print(pkg.origin_module_in_pkg)""")
        self.mod1.write(code)
        self._move(self.origin_module_in_pkg, None, pkg4)
        self.assertTrue(self.project.find_module("pkg2.pkg3.pkg4.origin_module_in_pkg") is not None)
        expected = dedent("""\
            import pkg2.pkg3.pkg4.origin_module_in_pkg
            from pkg2.pkg3.pkg4 import origin_module_in_pkg
            print(origin_module_in_pkg)
            print(pkg2.pkg3.pkg4.origin_module_in_pkg)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_modules_from_import_variable(self) -> None:
        pkg2 = testutils.create_package(self.project, "pkg2")
        pkg3 = testutils.create_package(self.project, "pkg3", pkg2)
        pkg4 = testutils.create_package(self.project, "pkg4", pkg3)
        code = dedent("""\
            from pkg.origin_module_in_pkg import foo
            print(foo)""")
        self.mod1.write(code)
        self._move(self.origin_module_in_pkg, None, pkg4)
        self.assertTrue(self.project.find_module("pkg2.pkg3.pkg4.origin_module_in_pkg") is not None)
        expected = dedent("""\
            from pkg2.pkg3.pkg4.origin_module_in_pkg import foo
            print(foo)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_modules_normal_import(self) -> None:
        pkg2 = testutils.create_package(self.project, "pkg2")
        pkg3 = testutils.create_package(self.project, "pkg3", pkg2)
        pkg4 = testutils.create_package(self.project, "pkg4", pkg3)
        code = dedent("""\
            import pkg.origin_module_in_pkg
            print(pkg.origin_module_in_pkg)""")
        self.mod1.write(code)
        self._move(self.origin_module_in_pkg, None, pkg4)
        self.assertTrue(self.project.find_module("pkg2.pkg3.pkg4.origin_module_in_pkg") is not None)
        expected = dedent("""\
            import pkg2.pkg3.pkg4.origin_module_in_pkg
            print(pkg2.pkg3.pkg4.origin_module_in_pkg)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_package_with_from_and_normal_imports(self) -> None:
        code = dedent("""\
            from pkg import mod4
            import pkg.mod4
            print(pkg.mod4)
            print(mod4)""")
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("pkg") + 1, self.destination_pkg_root)
        self.assertFalse(self.pkg.exists())
        self.assertTrue(self.project.find_module("destination_pkg_root.pkg.mod4") is not None)
        self.assertTrue(self.project.find_module("destination_pkg_root.pkg.mod5") is not None)
        expected = dedent("""\
            from destination_pkg_root.pkg import mod4
            import destination_pkg_root.pkg.mod4
            print(destination_pkg_root.pkg.mod4)
            print(mod4)""")
        self.assertEqual(expected, self.origin_module.read())

    def test_moving_package_with_from_and_normal_imports2(self) -> None:
        code = dedent("""\
            import pkg.mod4
            from pkg import mod4
            print(pkg.mod4)
            print(mod4)""")
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("pkg") + 1, self.destination_pkg_root)
        self.assertFalse(self.pkg.exists())
        self.assertTrue(self.project.find_module("destination_pkg_root.pkg.mod4") is not None)
        self.assertTrue(self.project.find_module("destination_pkg_root.pkg.mod5") is not None)
        expected = dedent("""\
            import destination_pkg_root.pkg.mod4
            from destination_pkg_root.pkg import mod4
            print(destination_pkg_root.pkg.mod4)
            print(mod4)""")
        self.assertEqual(expected, self.origin_module.read())

    def test_moving_package_and_retaining_blank_lines(self) -> None:
        pkg2 = testutils.create_package(self.project, "pkg2", self.pkg)
        code = dedent('''\
            """Docstring followed by blank lines."""

            import pkg.origin_module_in_pkg

            from pkg import origin_module_in_pkg
            from x import y
            from y import z
            from a import b
            from b import c
            print(pkg.origin_module_in_pkg)
            print(origin_module_in_pkg)''')
        self.mod1.write(code)
        self._move(self.origin_module_in_pkg, None, pkg2)
        expected = dedent('''\
            """Docstring followed by blank lines."""

            import pkg.pkg2.origin_module_in_pkg

            from x import y
            from y import z
            from a import b
            from b import c
            from pkg.pkg2 import origin_module_in_pkg
            print(pkg.pkg2.origin_module_in_pkg)
            print(origin_module_in_pkg)''')
        self.assertEqual(expected, self.mod1.read())

    def test_moving_functions_to_imported_module(self) -> None:
        code = dedent("""\
            import destination_module
            def a_func():
                var = destination_module.a_var
        """)
        self.destination_module.write("a_var = 1\n")
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("a_func") + 1, self.destination_module)
        expected = dedent("""\
            def a_func():
                var = a_var
            a_var = 1
        """)
        self.assertEqual(expected, self.destination_module.read())

    def test_moving_resources_using_move_module_refactoring(self) -> None:
        self.origin_module.write("a_var = 1")
        self.mod2.write(dedent("""\
            import origin_module
            my_var = origin_module.a_var
        """))
        resource = self.origin_module
        dest_resource = self.destination_pkg_root
        self._move(resource, None, dest_resource)
        expected = dedent("""\
            import destination_pkg_root.origin_module
            my_var = destination_pkg_root.origin_module.a_var
        """)
        self.assertEqual(expected, self.mod2.read())
        self.assertTrue(self.destination_pkg_root.get_child("origin_module.py") is not None)

    def test_moving_resources_using_move_module_for_packages(self) -> None:
        self.mod1.write(dedent("""\
            import pkg
            my_pkg = pkg"""))
        self._move(self.pkg, None, self.destination_pkg_root)
        expected = dedent("""\
            import destination_pkg_root.pkg
            my_pkg = destination_pkg_root.pkg""")
        self.assertEqual(expected, self.mod1.read())
        self.assertTrue(self.destination_pkg_root.get_child("pkg") is not None)

    def test_moving_resources_using_move_module_for_init_dot_py(self) -> None:
        self.mod1.write(dedent("""\
            import pkg
            my_pkg = pkg"""))
        init = self.pkg.get_child("__init__.py")
        self._move(init, None, self.destination_pkg_root)
        self.assertEqual(
            dedent("""\
                import destination_pkg_root.pkg
                my_pkg = destination_pkg_root.pkg"""),
            self.mod1.read(),
        )
        self.assertTrue(self.destination_pkg_root.get_child("pkg") is not None)

    def test_moving_module_and_star_imports(self) -> None:
        self.origin_module.write("a_var = 1")
        self.mod2.write(dedent("""\
            from origin_module import *
            a = a_var
        """))
        self._move(self.origin_module, None, self.destination_pkg_root)
        self.assertEqual(
            dedent("""\
                from destination_pkg_root.origin_module import *
                a = a_var
            """),
            self.mod2.read(),
        )

    def test_moving_module_and_not_removing_blanks_after_imports(self) -> None:
        self.origin_module_in_pkg.write("a_var = 1")
        self.mod2.write(dedent("""\
            from pkg import origin_module_in_pkg
            import os


            print(origin_module_in_pkg.a_var)
        """))
        self._move(self.origin_module_in_pkg, None, self.project.root)
        self.assertEqual(
            dedent("""\
                import os
                import origin_module_in_pkg


                print(origin_module_in_pkg.a_var)
            """),
            self.mod2.read(),
        )

    def test_moving_module_refactoring_and_nonexistent_destinations(self) -> None:
        self.origin_module_in_pkg.write("a_var = 1")
        self.mod2.write(dedent("""\
            from pkg import origin_module_in_pkg
            import os


            print(origin_module_in_pkg.a_var)
        """))
        with self.assertRaisesRegex(
            exceptions.RefactoringError,
            r"Move destination for modules should be packages.",
        ):
            self._move(self.origin_module_in_pkg, None, None)  # type: ignore[arg-type]

    def test_moving_methods_choosing_the_correct_class(self) -> None:
        code = dedent("""\
            class A(object):
                def a_method(self):
                    pass
        """)
        self.origin_module.write(code)
        mover = move.create_move(self.project, self.origin_module, code.index("a_method"))
        self.assertTrue(isinstance(mover, move.MoveMethod))

    def test_moving_methods_getting_new_method_for_empty_methods(self) -> None:
        code = dedent("""\
            class A(object):
                def a_method(self):
                    pass
        """)
        self.origin_module.write(code)
        mover = move.create_move(self.project, self.origin_module, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self):
                    pass
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_getting_new_method_for_constant_methods(self) -> None:
        code = dedent("""\
            class A(object):
                def a_method(self):
                    return 1
        """)
        self.origin_module.write(code)
        mover = move.create_move(self.project, self.origin_module, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self):
                    return 1
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_getting_new_method_passing_simple_parameters(self) -> None:
        code = dedent("""\
            class A(object):
                def a_method(self, p):
                    return p
        """)
        self.origin_module.write(code)
        mover = move.create_move(self.project, self.origin_module, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self, p):
                    return p
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_getting_new_method_using_main_object(self) -> None:
        code = dedent("""\
            class A(object):
                attr = 1
                def a_method(host):
                    return host.attr
        """)
        self.origin_module.write(code)
        mover = move.create_move(self.project, self.origin_module, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self, host):
                    return host.attr
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_getting_new_method_renaming_main_object(self) -> None:
        code = dedent("""\
            class A(object):
                attr = 1
                def a_method(self):
                    return self.attr
        """)
        self.origin_module.write(code)
        mover = move.create_move(self.project, self.origin_module, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self, host):
                    return host.attr
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_gettin_new_method_with_keyword_arguments(self) -> None:
        code = dedent("""\
            class A(object):
                attr = 1
                def a_method(self, p=None):
                    return p
        """)
        self.origin_module.write(code)
        mover = move.create_move(self.project, self.origin_module, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self, p=None):
                    return p
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_gettin_new_method_with_many_kinds_arguments(self) -> None:
        code = dedent("""\
            class A(object):
                attr = 1
                def a_method(self, p1, *args, **kwds):
                    return self.attr
        """)
        self.origin_module.write(code)
        mover = move.create_move(self.project, self.origin_module, code.index("a_method"))
        expected = dedent("""\
            def new_method(self, host, p1, *args, **kwds):
                return host.attr
        """)
        self.assertEqual(expected, mover.get_new_method("new_method"))

    def test_moving_methods_getting_new_method_for_multi_line_methods(self) -> None:
        code = dedent("""\
            class A(object):
                def a_method(self):
                    a = 2
                    return a
        """)
        self.origin_module.write(code)
        mover = move.create_move(self.project, self.origin_module, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self):
                    a = 2
                    return a
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_getting_old_method_for_constant_methods(self) -> None:
        self.mod2.write(dedent("""\
            class B(object):
                pass
        """))
        code = dedent("""\
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self):
                    return 1
        """)
        self.origin_module.write(code)
        self._move_to_attr(self.origin_module, code.index("a_method"), "attr", new_name="new_method")
        expected = dedent("""\
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self):
                    return self.attr.new_method()
        """)
        self.assertEqual(expected, self.origin_module.read())

    def test_moving_methods_getting_getting_changes_for_goal_class(self) -> None:
        self.mod2.write(dedent("""\
            class B(object):
                var = 1
        """))
        code = dedent("""\
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self):
                    return 1
        """)
        self.origin_module.write(code)
        self._move_to_attr(self.origin_module, code.index("a_method"), "attr", new_name="new_method")
        expected = dedent("""\
            class B(object):
                var = 1


                def new_method(self):
                    return 1
        """)
        self.assertEqual(expected, self.mod2.read())

    def test_moving_methods_getting_getting_changes_for_goal_class2(self) -> None:
        code = dedent("""\
            class B(object):
                var = 1

            class A(object):
                attr = B()
                def a_method(self):
                    return 1
        """)
        self.origin_module.write(code)
        self._move_to_attr(self.origin_module, code.index("a_method"), "attr", new_name="new_method")
        self.assertEqual(
            dedent("""\
                class B(object):
                    var = 1


                    def new_method(self):
                        return 1

                class A(object):
                    attr = B()
                    def a_method(self):
                        return self.attr.new_method()
            """),
            self.origin_module.read(),
        )

    def test_moving_methods_and_nonexistent_attributes(self) -> None:
        code = dedent("""\
            class A(object):
                def a_method(self):
                    return 1
        """)
        self.origin_module.write(code)
        with self.assertRaisesRegex(
            exceptions.RefactoringError,
            r"Destination attribute <x> not found",
        ):
            self._move_to_attr(self.origin_module, code.index("a_method"), "x", new_name="new_method")

    def test_unknown_attribute_type(self) -> None:
        code = dedent("""\
            class A(object):
                attr = 1
                def a_method(self):
                    return 1
        """)
        self.origin_module.write(code)
        with self.assertRaisesRegex(
            exceptions.RefactoringError,
            r"Unknown class type for attribute <attr>",
        ):
            self._move_to_attr(self.origin_module, code.index("a_method"), "attr", new_name="new_method")

    def test_moving_methods_and_moving_used_imports(self) -> None:
        self.mod2.write(dedent("""\
            class B(object):
                var = 1
        """))
        code = dedent("""\
            import sys
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self):
                    return sys.version
        """)
        self.origin_module.write(code)
        self._move_to_attr(self.origin_module, code.index("a_method"), "attr", new_name="new_method")
        code = dedent("""\
            import sys
            class B(object):
                var = 1


                def new_method(self):
                    return sys.version
        """)
        self.assertEqual(code, self.mod2.read())

    def test_moving_methods_getting_getting_changes_for_goal_class3(self) -> None:
        self.mod2.write(dedent("""\
            class B(object):
                pass
        """))
        code = dedent("""\
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self):
                    return 1
        """)
        self.origin_module.write(code)
        self._move_to_attr(self.origin_module, code.index("a_method"), "attr", new_name="new_method")
        expected = dedent("""\
            class B(object):

                def new_method(self):
                    return 1
        """)
        self.assertEqual(expected, self.mod2.read())

    def test_moving_methods_and_source_class_with_parameters(self) -> None:
        self.mod2.write(dedent("""\
            class B(object):
                pass
        """))
        code = dedent("""\
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self, p):
                    return p
        """)
        self.origin_module.write(code)
        self._move_to_attr(self.origin_module, code.index("a_method"), "attr", new_name="new_method")
        expected1 = dedent("""\
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self, p):
                    return self.attr.new_method(p)
        """)
        self.assertEqual(expected1, self.origin_module.read())
        expected2 = dedent("""\
            class B(object):

                def new_method(self, p):
                    return p
        """)
        self.assertEqual(expected2, self.mod2.read())

    def test_moving_globals_to_a_module_with_only_docstrings(self) -> None:
        self.origin_module.write(dedent("""\
            import sys


            def f():
                print(sys.version)
        """))
        self.destination_module.write(dedent('''\
            """doc

            More docs ...

            """
        '''))
        self._move(self.origin_module, self.origin_module.read().index("f()") + 1, self.destination_module)
        self.assertEqual(
            dedent('''\
                """doc

                More docs ...

                """
                import sys


                def f():
                    print(sys.version)
            '''),
            self.destination_module.read(),
        )

    def test_moving_globals_to_a_module_with_only_docstrings2(self) -> None:
        code = dedent("""\
            import os
            import sys


            def f():
                print(sys.version, os.path)
        """)
        self.origin_module.write(code)
        self.destination_module.write(dedent('''\
            """doc

            More docs ...

            """
        '''))
        self._move(self.origin_module, self.origin_module.read().index("f()") + 1, self.destination_module)
        expected = dedent('''\
            """doc

            More docs ...

            """
            import os
            import sys


            def f():
                print(sys.version, os.path)
        ''')
        self.assertEqual(expected, self.destination_module.read())

    def test_moving_a_global_when_it_is_used_after_a_multiline_str(self) -> None:
        code = dedent('''\
            def f():
                pass
            s = """\\
            """
            r = f()
        ''')
        self.origin_module.write(code)
        self._move(self.origin_module, code.index("f()") + 1, self.destination_module)
        expected = dedent('''\
            import destination_module
            s = """\\
            """
            r = destination_module.f()
        ''')
        self.assertEqual(expected, self.origin_module.read())

    def test_raising_an_exception_when_moving_non_package_folders(self) -> None:
        dir = self.project.root.create_folder("dir")
        with self.assertRaisesRegex(
            exceptions.RefactoringError,
            r"Cannot move non-package folder\.",
        ):
            move.create_move(self.project, dir)

    def test_moving_to_a_module_with_encoding_cookie(self) -> None:
        code = dedent("""\
            def f(): pass
        """)
        self.origin_module.write(code)
        self.destination_module.write("# -*- coding: utf-8 -*-")
        self._move(self.origin_module, code.index("f()") + 1, self.destination_module)
        expected = dedent("""\
            # -*- coding: utf-8 -*-
            def f(): pass
        """)
        self.assertEqual(expected, self.destination_module.read())

    def test_moving_decorated_function(self) -> None:
        self.origin_module.write(dedent("""\
            def hello(func):
                return func
            @hello
            def foo():
                pass
        """))
        self._move(self.origin_module, self.origin_module.read().index("foo") + 1, self.destination_module)
        self.assertEqual(
            dedent("""\
                def hello(func):
                    return func
            """), 
            self.origin_module.read(),
        )
        self.assertEqual(
            dedent("""\
                from origin_module import hello


                @hello
                def foo():
                    pass
            """),
            self.destination_module.read(),
        )

    def test_moving_decorated_class(self) -> None:
        self.origin_module.write(dedent("""\
            from dataclasses import dataclass
            @dataclass
            class AClass:
                pass
        """))
        self._move(self.origin_module, self.origin_module.read().index("AClass") + 1, self.destination_module)
        self.assertEqual("", self.origin_module.read())
        self.assertEqual(
            dedent("""\
                from dataclasses import dataclass


                @dataclass
                class AClass:
                    pass
            """),
            self.destination_module.read(),
        )
