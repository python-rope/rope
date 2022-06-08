from textwrap import dedent
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rope.base import exceptions
from rope.refactor import move
from ropetest import testutils


class MoveRefactoringTest(unittest.TestCase):
    def setUp(self):
        super(MoveRefactoringTest, self).setUp()
        self.project = testutils.sample_project()
        self.mod1 = testutils.create_module(self.project, "mod1")
        self.mod2 = testutils.create_module(self.project, "mod2")
        self.mod3 = testutils.create_module(self.project, "mod3")
        self.pkg = testutils.create_package(self.project, "pkg")
        self.mod4 = testutils.create_module(self.project, "mod4", self.pkg)
        self.mod5 = testutils.create_module(self.project, "mod5", self.pkg)

    def tearDown(self):
        testutils.remove_project(self.project)
        super(MoveRefactoringTest, self).tearDown()

    def _move(self, resource, offset, dest_resource):
        changes = move.create_move(self.project, resource, offset).get_changes(
            dest_resource
        )
        self.project.do(changes)

    def test_move_constant(self):
        self.mod1.write("foo = 123\n")
        self._move(self.mod1, self.mod1.read().index("foo") + 1, self.mod2)
        self.assertEqual("", self.mod1.read())
        self.assertEqual("foo = 123\n", self.mod2.read())

    def test_move_constant_2(self):
        self.mod1.write("bar = 321\nfoo = 123\n")
        self._move(self.mod1, self.mod1.read().index("foo") + 1, self.mod2)
        self.assertEqual("bar = 321\n", self.mod1.read())
        self.assertEqual("foo = 123\n", self.mod2.read())

    def test_move_constant_multiline(self):
        self.mod1.write(
            dedent("""\
                foo = (
                    123
                )
            """)
        )
        self._move(self.mod1, self.mod1.read().index("foo") + 1, self.mod2)
        self.assertEqual("", self.mod1.read())
        self.assertEqual(
            dedent("""\
                foo = (
                    123
                )
            """),
            self.mod2.read(),
        )

    def test_move_constant_multiple_statements(self):
        self.mod1.write(
            dedent("""\
                foo = 123
                foo += 3
                foo = 4
            """)
        )
        self._move(self.mod1, self.mod1.read().index("foo") + 1, self.mod2)
        self.assertEqual(
            dedent("""\
                import mod2
                mod2.foo += 3
                mod2.foo = 4
            """),
            self.mod1.read(),
        )
        self.assertEqual("foo = 123\n", self.mod2.read())

    def test_simple_moving(self):
        self.mod1.write(
            dedent("""\
                class AClass(object):
                    pass
            """)
        )
        self._move(self.mod1, self.mod1.read().index("AClass") + 1, self.mod2)
        self.assertEqual("", self.mod1.read())
        self.assertEqual(
            dedent("""\
                class AClass(object):
                    pass
            """),
            self.mod2.read(),
        )

    def test_moving_with_comment_prefix(self):
        self.mod1.write(
            dedent("""\
                a = 1
                # 1
                # 2
                class AClass(object):
                    pass
            """)
        )
        self._move(self.mod1, self.mod1.read().index("AClass") + 1, self.mod2)
        self.assertEqual("a = 1\n", self.mod1.read())
        self.assertEqual(
            dedent("""\
                # 1
                # 2
                class AClass(object):
                    pass
            """),
            self.mod2.read(),
        )

    def test_moving_with_comment_prefix_imports(self):
        self.mod1.write(
            dedent("""\
                import foo
                a = 1
                # 1
                # 2
                class AClass(foo.FooClass):
                    pass
            """)
        )
        self._move(self.mod1, self.mod1.read().index("AClass") + 1, self.mod2)
        self.assertEqual("a = 1\n", self.mod1.read())
        self.assertEqual(
            dedent("""\
                import foo


                # 1
                # 2
                class AClass(foo.FooClass):
                    pass
            """),
            self.mod2.read(),
        )

    def test_changing_other_modules_replacing_normal_imports(self):
        self.mod1.write("class AClass(object):\n    pass\n")
        self.mod3.write("import mod1\na_var = mod1.AClass()\n")
        self._move(self.mod1, self.mod1.read().index("AClass") + 1, self.mod2)
        self.assertEqual(
            dedent("""\
                import mod2
                a_var = mod2.AClass()
            """),
            self.mod3.read(),
        )

    def test_changing_other_modules_adding_normal_imports(self):
        self.mod1.write(
            dedent("""\
                class AClass(object):
                    pass
                def a_function():
                    pass
            """)
        )
        self.mod3.write(
            dedent("""\
                import mod1
                a_var = mod1.AClass()
                mod1.a_function()"""
            )
        )
        self._move(self.mod1, self.mod1.read().index("AClass") + 1, self.mod2)
        self.assertEqual(
            dedent("""\
                import mod1
                import mod2
                a_var = mod2.AClass()
                mod1.a_function()"""
            ),
            self.mod3.read(),
        )

    def test_adding_imports_prefer_from_module(self):
        self.project.prefs["prefer_module_from_imports"] = True
        self.mod1.write(
            dedent("""\
                class AClass(object):
                    pass
                def a_function():
                    pass
            """)
        )
        self.mod3.write(
            dedent("""\
                import mod1
                a_var = mod1.AClass()
                mod1.a_function()"""
            )
        )
        # Move to mod4 which is in a different package
        self._move(self.mod1, self.mod1.read().index("AClass") + 1, self.mod4)
        self.assertEqual(
            dedent("""\
                import mod1
                from pkg import mod4
                a_var = mod4.AClass()
                mod1.a_function()"""
            ),
            self.mod3.read(),
        )

    def test_adding_imports_noprefer_from_module(self):
        self.project.prefs["prefer_module_from_imports"] = False
        self.mod1.write(
            dedent("""\
                class AClass(object):
                    pass
                def a_function():
                    pass
            """)
        )
        self.mod3.write(
            dedent("""\
                import mod1
                a_var = mod1.AClass()
                mod1.a_function()"""
            )
        )
        # Move to mod4 which is in a different package
        self._move(self.mod1, self.mod1.read().index("AClass") + 1, self.mod4)
        self.assertEqual(
            dedent("""\
                import mod1
                import pkg.mod4
                a_var = pkg.mod4.AClass()
                mod1.a_function()"""
            ),
            self.mod3.read(),
        )

    def test_adding_imports_prefer_from_module_top_level_module(self):
        self.project.prefs["prefer_module_from_imports"] = True
        self.mod1.write(
            dedent("""\
                class AClass(object):
                    pass
                def a_function():
                    pass
            """)
        )
        self.mod3.write(
            dedent("""\
                import mod1
                a_var = mod1.AClass()
                mod1.a_function()"""
            )
        )
        self._move(self.mod1, self.mod1.read().index("AClass") + 1, self.mod2)
        self.assertEqual(
            dedent("""\
                import mod1
                import mod2
                a_var = mod2.AClass()
                mod1.a_function()"""
            ),
            self.mod3.read(),
        )

    def test_changing_other_modules_removing_from_imports(self):
        self.mod1.write(
            dedent("""\
                class AClass(object):
                    pass
            """)
        )
        self.mod3.write(
            dedent("""\
                from mod1 import AClass
                a_var = AClass()
            """)
        )
        self._move(self.mod1, self.mod1.read().index("AClass") + 1, self.mod2)
        self.assertEqual(
            dedent("""\
                import mod2
                a_var = mod2.AClass()
            """),
            self.mod3.read(),
        )

    def test_changing_source_module(self):
        self.mod1.write(
            dedent("""\
                class AClass(object):
                    pass
                a_var = AClass()
            """)
        )
        self._move(self.mod1, self.mod1.read().index("AClass") + 1, self.mod2)
        self.assertEqual(
            dedent("""\
                import mod2
                a_var = mod2.AClass()
            """),
            self.mod1.read(),
        )

    def test_changing_destination_module(self):
        self.mod1.write(
            dedent("""\
                class AClass(object):
                    pass
            """)
        )
        self.mod2.write(
            dedent("""\
                from mod1 import AClass
                a_var = AClass()
            """)
        )
        self._move(self.mod1, self.mod1.read().index("AClass") + 1, self.mod2)
        self.assertEqual(
            dedent("""\
                class AClass(object):
                    pass
                a_var = AClass()
            """),
            self.mod2.read(),
        )

    def test_folder_destination(self):
        folder = self.project.root.create_folder("folder")
        self.mod1.write(
            dedent("""\
                class AClass(object):
                    pass
            """)
        )
        with self.assertRaises(exceptions.RefactoringError):
            self._move(self.mod1, self.mod1.read().index("AClass") + 1, folder)

    def test_raising_exception_for_moving_non_global_elements(self):
        self.mod1.write(
            dedent("""\
                def a_func():
                    class AClass(object):
                        pass
            """)
        )
        with self.assertRaises(exceptions.RefactoringError):
            self._move(self.mod1, self.mod1.read().index("AClass") + 1, self.mod2)

    def test_raising_an_exception_for_moving_non_global_variable(self):
        code = dedent("""\
            class TestClass:
                CONSTANT = 5
        """)
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            mover = move.create_move(
                self.project, self.mod1, code.index("CONSTANT") + 1
            )

    def test_raising_exception_for_mov_glob_elemnts_to_the_same_module(self):
        self.mod1.write("def a_func():\n    pass\n")
        with self.assertRaises(exceptions.RefactoringError):
            self._move(self.mod1, self.mod1.read().index("a_func"), self.mod1)

    def test_moving_used_imports_to_destination_module(self):
        self.mod3.write("a_var = 10")
        code = dedent("""\
            import mod3
            from mod3 import a_var
            def a_func():
                print(mod3, a_var)
        """)
        self.mod1.write(code)
        self._move(self.mod1, code.index("a_func") + 1, self.mod2)
        expected = dedent("""\
            import mod3
            from mod3 import a_var


            def a_func():
                print(mod3, a_var)
        """)
        self.assertEqual(expected, self.mod2.read())

    def test_moving_used_names_to_destination_module2(self):
        code = dedent("""\
            a_var = 10
            def a_func():
                print(a_var)
        """)
        self.mod1.write(code)
        self._move(self.mod1, code.index("a_func") + 1, self.mod2)
        self.assertEqual(
            dedent("""\
                a_var = 10
            """),
            self.mod1.read(),
        )
        expected = dedent("""\
            from mod1 import a_var


            def a_func():
                print(a_var)
        """)
        self.assertEqual(expected, self.mod2.read())

    def test_moving_used_underlined_names_to_destination_module(self):
        code = dedent("""\
            _var = 10
            def a_func():
                print(_var)
        """)
        self.mod1.write(code)
        self._move(self.mod1, code.index("a_func") + 1, self.mod2)
        expected = dedent("""\
            from mod1 import _var


            def a_func():
                print(_var)
        """)
        self.assertEqual(expected, self.mod2.read())

    def test_moving_and_used_relative_imports(self):
        code = dedent("""\
            import mod5
            def a_func():
                print(mod5)
        """)
        self.mod4.write(code)
        self._move(self.mod4, code.index("a_func") + 1, self.mod1)
        expected = dedent("""\
            import pkg.mod5


            def a_func():
                print(pkg.mod5)
        """)
        self.assertEqual(expected, self.mod1.read())
        self.assertEqual("", self.mod4.read())

    def test_moving_modules(self):
        code = "import mod1\nprint(mod1)"
        self.mod2.write(code)
        self._move(self.mod2, code.index("mod1") + 1, self.pkg)
        expected = "import pkg.mod1\nprint(pkg.mod1)"
        self.assertEqual(expected, self.mod2.read())
        self.assertTrue(
            not self.mod1.exists() and self.project.find_module("pkg.mod1") is not None
        )

    def test_moving_modules_and_removing_out_of_date_imports(self):
        code = "import pkg.mod4\nprint(pkg.mod4)"
        self.mod2.write(code)
        self._move(self.mod2, code.index("mod4") + 1, self.project.root)
        expected = "import mod4\nprint(mod4)"
        self.assertEqual(expected, self.mod2.read())
        self.assertTrue(self.project.find_module("mod4") is not None)

    def test_moving_modules_and_removing_out_of_date_froms(self):
        code = "from pkg import mod4\nprint(mod4)"
        self.mod2.write(code)
        self._move(self.mod2, code.index("mod4") + 1, self.project.root)
        self.assertEqual("import mod4\nprint(mod4)", self.mod2.read())

    def test_moving_modules_and_removing_out_of_date_froms2(self):
        self.mod4.write("a_var = 10")
        code = "from pkg.mod4 import a_var\nprint(a_var)\n"
        self.mod2.write(code)
        self._move(self.mod2, code.index("mod4") + 1, self.project.root)
        expected = "from mod4 import a_var\nprint(a_var)\n"
        self.assertEqual(expected, self.mod2.read())

    def test_moving_modules_and_relative_import(self):
        self.mod4.write("import mod5\nprint(mod5)\n")
        code = "import pkg.mod4\nprint(pkg.mod4)"
        self.mod2.write(code)
        self._move(self.mod2, code.index("mod4") + 1, self.project.root)
        moved = self.project.find_module("mod4")
        expected = "import pkg.mod5\nprint(pkg.mod5)\n"
        self.assertEqual(expected, moved.read())

    def test_moving_module_kwarg_same_name_as_old(self):
        self.mod1.write("def foo(mod1=0):\n    pass")
        code = "import mod1\nmod1.foo(mod1=1)"
        self.mod2.write(code)
        self._move(self.mod1, None, self.pkg)
        moved = self.project.find_module("mod2")
        expected = "import pkg.mod1\npkg.mod1.foo(mod1=1)"
        self.assertEqual(expected, moved.read())

    def test_moving_packages(self):
        pkg2 = testutils.create_package(self.project, "pkg2")
        code = "import pkg.mod4\nprint(pkg.mod4)"
        self.mod1.write(code)
        self._move(self.mod1, code.index("pkg") + 1, pkg2)
        self.assertFalse(self.pkg.exists())
        self.assertTrue(self.project.find_module("pkg2.pkg.mod4") is not None)
        self.assertTrue(self.project.find_module("pkg2.pkg.mod4") is not None)
        self.assertTrue(self.project.find_module("pkg2.pkg.mod5") is not None)
        expected = "import pkg2.pkg.mod4\nprint(pkg2.pkg.mod4)"
        self.assertEqual(expected, self.mod1.read())

    def test_moving_modules_with_self_imports(self):
        self.mod1.write("import mod1\nprint(mod1)\n")
        self.mod2.write("import mod1\n")
        self._move(self.mod2, self.mod2.read().index("mod1") + 1, self.pkg)
        moved = self.project.find_module("pkg.mod1")
        self.assertEqual(
            dedent("""\
                import pkg.mod1
                print(pkg.mod1)
            """),
            moved.read(),
        )

    def test_moving_modules_with_from_imports(self):
        pkg2 = testutils.create_package(self.project, "pkg2")
        code = dedent("""\
            from pkg import mod4
            print(mod4)""")
        self.mod1.write(code)
        self._move(self.mod1, code.index("pkg") + 1, pkg2)
        self.assertFalse(self.pkg.exists())
        self.assertTrue(self.project.find_module("pkg2.pkg.mod4") is not None)
        self.assertTrue(self.project.find_module("pkg2.pkg.mod5") is not None)
        expected = dedent("""\
            from pkg2.pkg import mod4
            print(mod4)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_modules_with_from_import(self):
        pkg2 = testutils.create_package(self.project, "pkg2")
        pkg3 = testutils.create_package(self.project, "pkg3", pkg2)
        pkg4 = testutils.create_package(self.project, "pkg4", pkg3)
        code = dedent("""\
            from pkg import mod4
            print(mod4)""")
        self.mod1.write(code)
        self._move(self.mod4, None, pkg4)
        self.assertTrue(self.project.find_module("pkg2.pkg3.pkg4.mod4") is not None)
        expected = dedent("""\
            from pkg2.pkg3.pkg4 import mod4
            print(mod4)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_modules_with_multi_from_imports(self):
        pkg2 = testutils.create_package(self.project, "pkg2")
        pkg3 = testutils.create_package(self.project, "pkg3", pkg2)
        pkg4 = testutils.create_package(self.project, "pkg4", pkg3)
        code = dedent("""\
            from pkg import mod4, mod5
            print(mod4)""")
        self.mod1.write(code)
        self._move(self.mod4, None, pkg4)
        self.assertTrue(self.project.find_module("pkg2.pkg3.pkg4.mod4") is not None)
        expected = dedent("""\
            from pkg import mod5
            from pkg2.pkg3.pkg4 import mod4
            print(mod4)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_modules_with_from_and_normal_imports(self):
        pkg2 = testutils.create_package(self.project, "pkg2")
        pkg3 = testutils.create_package(self.project, "pkg3", pkg2)
        pkg4 = testutils.create_package(self.project, "pkg4", pkg3)
        code = dedent("""\
            from pkg import mod4
            import pkg.mod4
            print(mod4)
            print(pkg.mod4)""")
        self.mod1.write(code)
        self._move(self.mod4, None, pkg4)
        self.assertTrue(self.project.find_module("pkg2.pkg3.pkg4.mod4") is not None)
        expected = dedent("""\
            import pkg2.pkg3.pkg4.mod4
            from pkg2.pkg3.pkg4 import mod4
            print(mod4)
            print(pkg2.pkg3.pkg4.mod4)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_modules_with_normal_and_from_imports(self):
        pkg2 = testutils.create_package(self.project, "pkg2")
        pkg3 = testutils.create_package(self.project, "pkg3", pkg2)
        pkg4 = testutils.create_package(self.project, "pkg4", pkg3)
        code = dedent("""\
            import pkg.mod4
            from pkg import mod4
            print(mod4)
            print(pkg.mod4)""")
        self.mod1.write(code)
        self._move(self.mod4, None, pkg4)
        self.assertTrue(self.project.find_module("pkg2.pkg3.pkg4.mod4") is not None)
        expected = dedent("""\
            import pkg2.pkg3.pkg4.mod4
            from pkg2.pkg3.pkg4 import mod4
            print(mod4)
            print(pkg2.pkg3.pkg4.mod4)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_modules_from_import_variable(self):
        pkg2 = testutils.create_package(self.project, "pkg2")
        pkg3 = testutils.create_package(self.project, "pkg3", pkg2)
        pkg4 = testutils.create_package(self.project, "pkg4", pkg3)
        code = dedent("""\
            from pkg.mod4 import foo
            print(foo)""")
        self.mod1.write(code)
        self._move(self.mod4, None, pkg4)
        self.assertTrue(self.project.find_module("pkg2.pkg3.pkg4.mod4") is not None)
        expected = dedent("""\
            from pkg2.pkg3.pkg4.mod4 import foo
            print(foo)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_modules_normal_import(self):
        pkg2 = testutils.create_package(self.project, "pkg2")
        pkg3 = testutils.create_package(self.project, "pkg3", pkg2)
        pkg4 = testutils.create_package(self.project, "pkg4", pkg3)
        code = dedent("""\
            import pkg.mod4
            print(pkg.mod4)""")
        self.mod1.write(code)
        self._move(self.mod4, None, pkg4)
        self.assertTrue(self.project.find_module("pkg2.pkg3.pkg4.mod4") is not None)
        expected = dedent("""\
            import pkg2.pkg3.pkg4.mod4
            print(pkg2.pkg3.pkg4.mod4)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_package_with_from_and_normal_imports(self):
        pkg2 = testutils.create_package(self.project, "pkg2")
        code = dedent("""\
            from pkg import mod4
            import pkg.mod4
            print(pkg.mod4)
            print(mod4)""")
        self.mod1.write(code)
        self._move(self.mod1, code.index("pkg") + 1, pkg2)
        self.assertFalse(self.pkg.exists())
        self.assertTrue(self.project.find_module("pkg2.pkg.mod4") is not None)
        self.assertTrue(self.project.find_module("pkg2.pkg.mod5") is not None)
        expected = dedent("""\
            from pkg2.pkg import mod4
            import pkg2.pkg.mod4
            print(pkg2.pkg.mod4)
            print(mod4)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_package_with_from_and_normal_imports2(self):
        pkg2 = testutils.create_package(self.project, "pkg2")
        code = dedent("""\
            import pkg.mod4
            from pkg import mod4
            print(pkg.mod4)
            print(mod4)""")
        self.mod1.write(code)
        self._move(self.mod1, code.index("pkg") + 1, pkg2)
        self.assertFalse(self.pkg.exists())
        self.assertTrue(self.project.find_module("pkg2.pkg.mod4") is not None)
        self.assertTrue(self.project.find_module("pkg2.pkg.mod5") is not None)
        expected = dedent("""\
            import pkg2.pkg.mod4
            from pkg2.pkg import mod4
            print(pkg2.pkg.mod4)
            print(mod4)""")
        self.assertEqual(expected, self.mod1.read())

    def test_moving_package_and_retaining_blank_lines(self):
        pkg2 = testutils.create_package(self.project, "pkg2", self.pkg)
        code = dedent('''\
            """Docstring followed by blank lines."""

            import pkg.mod4

            from pkg import mod4
            from x import y
            from y import z
            from a import b
            from b import c
            print(pkg.mod4)
            print(mod4)''')
        self.mod1.write(code)
        self._move(self.mod4, None, pkg2)
        expected = dedent('''\
            """Docstring followed by blank lines."""

            import pkg.pkg2.mod4

            from x import y
            from y import z
            from a import b
            from b import c
            from pkg.pkg2 import mod4
            print(pkg.pkg2.mod4)
            print(mod4)''')
        self.assertEqual(expected, self.mod1.read())

    def test_moving_functions_to_imported_module(self):
        code = dedent("""\
            import mod1
            def a_func():
                var = mod1.a_var
        """)
        self.mod1.write("a_var = 1\n")
        self.mod2.write(code)
        self._move(self.mod2, code.index("a_func") + 1, self.mod1)
        expected = dedent("""\
            def a_func():
                var = a_var
            a_var = 1
        """)
        self.assertEqual(expected, self.mod1.read())

    def test_moving_resources_using_move_module_refactoring(self):
        self.mod1.write("a_var = 1")
        self.mod2.write(
            dedent("""\
                import mod1
                my_var = mod1.a_var
            """)
        )
        mover = move.create_move(self.project, self.mod1)
        mover.get_changes(self.pkg).do()
        expected = dedent("""\
            import pkg.mod1
            my_var = pkg.mod1.a_var
        """)
        self.assertEqual(expected, self.mod2.read())
        self.assertTrue(self.pkg.get_child("mod1.py") is not None)

    def test_moving_resources_using_move_module_for_packages(self):
        self.mod1.write(
            dedent("""\
                import pkg
                my_pkg = pkg"""
            )
        )
        pkg2 = testutils.create_package(self.project, "pkg2")
        mover = move.create_move(self.project, self.pkg)
        mover.get_changes(pkg2).do()
        expected = dedent("""\
            import pkg2.pkg
            my_pkg = pkg2.pkg""")
        self.assertEqual(expected, self.mod1.read())
        self.assertTrue(pkg2.get_child("pkg") is not None)

    def test_moving_resources_using_move_module_for_init_dot_py(self):
        self.mod1.write(
            dedent("""\
                import pkg
                my_pkg = pkg"""
            )
        )
        pkg2 = testutils.create_package(self.project, "pkg2")
        init = self.pkg.get_child("__init__.py")
        mover = move.create_move(self.project, init)
        mover.get_changes(pkg2).do()
        self.assertEqual(
            dedent("""\
                import pkg2.pkg
                my_pkg = pkg2.pkg"""
            ),
            self.mod1.read(),
        )
        self.assertTrue(pkg2.get_child("pkg") is not None)

    def test_moving_module_and_star_imports(self):
        self.mod1.write("a_var = 1")
        self.mod2.write(
            dedent("""\
                from mod1 import *
                a = a_var
            """)
        )
        mover = move.create_move(self.project, self.mod1)
        mover.get_changes(self.pkg).do()
        self.assertEqual(
            dedent("""\
                from pkg.mod1 import *
                a = a_var
            """),
            self.mod2.read(),
        )

    def test_moving_module_and_not_removing_blanks_after_imports(self):
        self.mod4.write("a_var = 1")
        self.mod2.write(
            dedent("""\
                from pkg import mod4
                import os


                print(mod4.a_var)
            """)
        )
        mover = move.create_move(self.project, self.mod4)
        mover.get_changes(self.project.root).do()
        self.assertEqual(
            dedent("""\
                import os
                import mod4


                print(mod4.a_var)
            """),
            self.mod2.read(),
        )

    def test_moving_module_refactoring_and_nonexistent_destinations(self):
        self.mod4.write("a_var = 1")
        self.mod2.write(
            dedent("""\
                from pkg import mod4
                import os


                print(mod4.a_var)
            """)
        )
        with self.assertRaises(exceptions.RefactoringError):
            mover = move.create_move(self.project, self.mod4)
            mover.get_changes(None).do()

    def test_moving_methods_choosing_the_correct_class(self):
        code = dedent("""\
            class A(object):
                def a_method(self):
                    pass
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        self.assertTrue(isinstance(mover, move.MoveMethod))

    def test_moving_methods_getting_new_method_for_empty_methods(self):
        code = dedent("""\
            class A(object):
                def a_method(self):
                    pass
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self):
                    pass
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_getting_new_method_for_constant_methods(self):
        code = dedent("""\
            class A(object):
                def a_method(self):
                    return 1
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self):
                    return 1
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_getting_new_method_passing_simple_paremters(self):
        code = dedent("""\
            class A(object):
                def a_method(self, p):
                    return p
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self, p):
                    return p
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_getting_new_method_using_main_object(self):
        code = dedent("""\
            class A(object):
                attr = 1
                def a_method(host):
                    return host.attr
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self, host):
                    return host.attr
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_getting_new_method_renaming_main_object(self):
        code = dedent("""\
            class A(object):
                attr = 1
                def a_method(self):
                    return self.attr
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self, host):
                    return host.attr
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_gettin_new_method_with_keyword_arguments(self):
        code = dedent("""\
            class A(object):
                attr = 1
                def a_method(self, p=None):
                    return p
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self, p=None):
                    return p
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_gettin_new_method_with_many_kinds_arguments(self):
        code = dedent("""\
            class A(object):
                attr = 1
                def a_method(self, p1, *args, **kwds):
                    return self.attr
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        expected = dedent("""\
            def new_method(self, host, p1, *args, **kwds):
                return host.attr
        """)
        self.assertEqual(expected, mover.get_new_method("new_method"))

    def test_moving_methods_getting_new_method_for_multi_line_methods(self):
        code = dedent("""\
            class A(object):
                def a_method(self):
                    a = 2
                    return a
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        self.assertEqual(
            dedent("""\
                def new_method(self):
                    a = 2
                    return a
            """),
            mover.get_new_method("new_method"),
        )

    def test_moving_methods_getting_old_method_for_constant_methods(self):
        self.mod2.write("class B(object):\n    pass\n")
        code = dedent("""\
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self):
                    return 1
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        mover.get_changes("attr", "new_method").do()
        expected = dedent("""\
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self):
                    return self.attr.new_method()
        """)
        self.assertEqual(expected, self.mod1.read())

    def test_moving_methods_getting_getting_changes_for_goal_class(self):
        self.mod2.write("class B(object):\n    var = 1\n")
        code = dedent("""\
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self):
                    return 1
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        mover.get_changes("attr", "new_method").do()
        expected = dedent("""\
            class B(object):
                var = 1


                def new_method(self):
                    return 1
        """)
        self.assertEqual(expected, self.mod2.read())

    def test_moving_methods_getting_getting_changes_for_goal_class2(self):
        code = dedent("""\
            class B(object):
                var = 1

            class A(object):
                attr = B()
                def a_method(self):
                    return 1
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        mover.get_changes("attr", "new_method").do()
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
            self.mod1.read(),
        )

    def test_moving_methods_and_nonexistent_attributes(self):
        code = dedent("""\
            class A(object):
                def a_method(self):
                    return 1
        """)
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            mover = move.create_move(self.project, self.mod1, code.index("a_method"))
            mover.get_changes("x", "new_method")

    def test_unknown_attribute_type(self):
        code = dedent("""\
            class A(object):
                attr = 1
                def a_method(self):
                    return 1
        """)
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            mover = move.create_move(self.project, self.mod1, code.index("a_method"))
            mover.get_changes("attr", "new_method")

    def test_moving_methods_and_moving_used_imports(self):
        self.mod2.write("class B(object):\n    var = 1\n")
        code = dedent("""\
            import sys
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self):
                    return sys.version
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        mover.get_changes("attr", "new_method").do()
        code = dedent("""\
            import sys
            class B(object):
                var = 1


                def new_method(self):
                    return sys.version
        """)
        self.assertEqual(code, self.mod2.read())

    def test_moving_methods_getting_getting_changes_for_goal_class3(self):
        self.mod2.write(
            dedent("""\
                class B(object):
                    pass
            """)
        )
        code = dedent("""\
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self):
                    return 1
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        mover.get_changes("attr", "new_method").do()
        expected = dedent("""\
            class B(object):

                def new_method(self):
                    return 1
        """)
        self.assertEqual(expected, self.mod2.read())

    def test_moving_methods_and_source_class_with_parameters(self):
        self.mod2.write("class B(object):\n    pass\n")
        code = dedent("""\
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self, p):
                    return p
        """)
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("a_method"))
        mover.get_changes("attr", "new_method").do()
        expected1 = dedent("""\
            import mod2

            class A(object):
                attr = mod2.B()
                def a_method(self, p):
                    return self.attr.new_method(p)
        """)
        self.assertEqual(expected1, self.mod1.read())
        expected2 = dedent("""\
            class B(object):

                def new_method(self, p):
                    return p
        """)
        self.assertEqual(expected2, self.mod2.read())

    def test_moving_globals_to_a_module_with_only_docstrings(self):
        self.mod1.write(
            dedent("""\
                import sys


                def f():
                    print(sys.version)
            """)
        )
        self.mod2.write(
            dedent('''\
                """doc

                More docs ...

                """
            ''')
        )
        mover = move.create_move(
            self.project, self.mod1, self.mod1.read().index("f()") + 1
        )
        self.project.do(mover.get_changes(self.mod2))
        self.assertEqual(
            dedent('''\
                """doc

                More docs ...

                """
                import sys


                def f():
                    print(sys.version)
            '''),
            self.mod2.read(),
        )

    def test_moving_globals_to_a_module_with_only_docstrings2(self):
        code = dedent("""\
            import os
            import sys


            def f():
                print(sys.version, os.path)
        """)
        self.mod1.write(code)
        self.mod2.write('"""doc\n\nMore docs ...\n\n"""\n')
        mover = move.create_move(
            self.project, self.mod1, self.mod1.read().index("f()") + 1
        )
        self.project.do(mover.get_changes(self.mod2))
        expected = dedent('''\
            """doc

            More docs ...

            """
            import os
            import sys


            def f():
                print(sys.version, os.path)
        ''')
        self.assertEqual(expected, self.mod2.read())

    def test_moving_a_global_when_it_is_used_after_a_multiline_str(self):
        code = dedent('''\
            def f():
                pass
            s = """\\
            """
            r = f()
        ''')
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1, code.index("f()") + 1)
        self.project.do(mover.get_changes(self.mod2))
        expected = dedent('''\
            import mod2
            s = """\\
            """
            r = mod2.f()
        ''')
        self.assertEqual(expected, self.mod1.read())

    def test_raising_an_exception_when_moving_non_package_folders(self):
        dir = self.project.root.create_folder("dir")
        with self.assertRaises(exceptions.RefactoringError):
            move.create_move(self.project, dir)

    def test_moving_to_a_module_with_encoding_cookie(self):
        code1 = "# -*- coding: utf-8 -*-"
        self.mod1.write(code1)
        code2 = dedent("""\
            def f(): pass
        """)
        self.mod2.write(code2)
        mover = move.create_move(self.project, self.mod2, code2.index("f()") + 1)
        self.project.do(mover.get_changes(self.mod1))
        expected = "%s\n%s" % (code1, code2)
        self.assertEqual(expected, self.mod1.read())

    def test_moving_decorated_function(self):
        self.mod1.write(
            dedent("""\
                def hello(func):
                    return func
                @hello
                def foo():
                    pass
            """)
        )
        self._move(self.mod1, self.mod1.read().index("foo") + 1, self.mod2)
        self.assertEqual("def hello(func):\n    return func\n", self.mod1.read())
        self.assertEqual(
            dedent("""\
                from mod1 import hello
                

                @hello
                def foo():
                    pass
            """),
            self.mod2.read(),
        )

    def test_moving_decorated_class(self):
        self.mod1.write(
            dedent("""\
                from dataclasses import dataclass
                @dataclass
                class AClass:
                    pass
            """)
        )
        self._move(self.mod1, self.mod1.read().index("AClass") + 1, self.mod2)
        self.assertEqual("", self.mod1.read())
        self.assertEqual(
            dedent("""\
                from dataclasses import dataclass
                

                @dataclass
                class AClass:
                    pass
            """),
            self.mod2.read(),
        )
