import unittest
from textwrap import dedent

from rope.base import exceptions
from rope.contrib import generate
from ropetest import testutils


class GenerateTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, "mod1")
        self.mod2 = testutils.create_module(self.project, "mod2")
        self.pkg = testutils.create_package(self.project, "pkg")

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def _get_generate(self, offset):
        return generate.GenerateVariable(self.project, self.mod, offset)

    def _get_generate_class(self, offset, goal_mod=None):
        return generate.GenerateClass(
            self.project, self.mod, offset, goal_resource=goal_mod
        )

    def _get_generate_module(self, offset):
        return generate.GenerateModule(self.project, self.mod, offset)

    def _get_generate_package(self, offset):
        return generate.GeneratePackage(self.project, self.mod, offset)

    def _get_generate_function(self, offset):
        return generate.GenerateFunction(self.project, self.mod, offset)

    def test_getting_location(self):
        code = "a_var = name\n"
        self.mod.write(code)
        generator = self._get_generate(code.index("name"))
        self.assertEqual((self.mod, 1), generator.get_location())

    def test_generating_variable(self):
        code = dedent("""\
            a_var = name
        """)
        self.mod.write(code)
        changes = self._get_generate(code.index("name")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                name = None


                a_var = name
            """),
            self.mod.read(),
        )

    def test_generating_variable_inserting_before_statement(self):
        code = dedent("""\
            c = 1
            c = b
        """)
        self.mod.write(code)
        changes = self._get_generate(code.index("b")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                c = 1
                b = None


                c = b
            """),
            self.mod.read(),
        )

    def test_generating_variable_in_local_scopes(self):
        code = dedent("""\
            def f():
                c = 1
                c = b
        """)
        self.mod.write(code)
        changes = self._get_generate(code.index("b")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                def f():
                    c = 1
                    b = None
                    c = b
            """),
            self.mod.read(),
        )

    def test_generating_variable_in_other_modules(self):
        code = dedent("""\
            import mod2
            c = mod2.b
        """)
        self.mod.write(code)
        generator = self._get_generate(code.index("b"))
        self.project.do(generator.get_changes())
        self.assertEqual((self.mod2, 1), generator.get_location())
        self.assertEqual("b = None\n", self.mod2.read())

    def test_generating_variable_in_classes(self):
        code = dedent("""\
            class C(object):
                def f(self):
                    pass
            c = C()
            a_var = c.attr""")
        self.mod.write(code)
        changes = self._get_generate(code.index("attr")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                class C(object):
                    def f(self):
                        pass

                    attr = None
                c = C()
                a_var = c.attr"""),
            self.mod.read(),
        )

    def test_generating_variable_in_classes_removing_pass(self):
        code = dedent("""\
            class C(object):
                pass
            c = C()
            a_var = c.attr""")
        self.mod.write(code)
        changes = self._get_generate(code.index("attr")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                class C(object):

                    attr = None
                c = C()
                a_var = c.attr"""),
            self.mod.read(),
        )

    def test_generating_variable_in_packages(self):
        code = "import pkg\na = pkg.a\n"
        self.mod.write(code)
        generator = self._get_generate(code.rindex("a"))
        self.project.do(generator.get_changes())
        init = self.pkg.get_child("__init__.py")
        self.assertEqual((init, 1), generator.get_location())
        self.assertEqual("a = None\n", init.read())

    def test_generating_classes(self):
        code = "c = C()\n"
        self.mod.write(code)
        changes = self._get_generate_class(code.index("C")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                class C(object):
                    pass


                c = C()
            """),
            self.mod.read(),
        )

    def test_generating_classes_in_other_module(self):
        code = "c = C()\n"
        self.mod.write(code)
        changes = self._get_generate_class(code.index("C"), self.mod2).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                class C(object):
                    pass
            """),
            self.mod2.read(),
        )
        self.assertEqual(
            dedent("""\
                from mod2 import C
                c = C()
            """),
            self.mod.read(),
        )

    def test_generating_modules(self):
        code = dedent("""\
            import pkg
            pkg.mod
        """)
        self.mod.write(code)
        generator = self._get_generate_module(code.rindex("mod"))
        self.project.do(generator.get_changes())
        mod = self.pkg.get_child("mod.py")
        self.assertEqual((mod, 1), generator.get_location())
        self.assertEqual(
            dedent("""\
                import pkg.mod
                pkg.mod
            """),
            self.mod.read(),
        )

    def test_generating_packages(self):
        code = dedent("""\
            import pkg
            pkg.pkg2
        """)
        self.mod.write(code)
        generator = self._get_generate_package(code.rindex("pkg2"))
        self.project.do(generator.get_changes())
        pkg2 = self.pkg.get_child("pkg2")
        init = pkg2.get_child("__init__.py")
        self.assertEqual((init, 1), generator.get_location())
        self.assertEqual(
            dedent("""\
                import pkg.pkg2
                pkg.pkg2
            """),
            self.mod.read(),
        )

    def test_generating_function(self):
        code = "a_func()\n"
        self.mod.write(code)
        changes = self._get_generate_function(code.index("a_func")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                def a_func():
                    pass


                a_func()
            """),
            self.mod.read(),
        )

    def test_generating_modules_with_empty_primary(self):
        code = "mod\n"
        self.mod.write(code)
        generator = self._get_generate_module(code.rindex("mod"))
        self.project.do(generator.get_changes())
        mod = self.project.root.get_child("mod.py")
        self.assertEqual((mod, 1), generator.get_location())
        self.assertEqual("import mod\nmod\n", self.mod.read())

    def test_generating_variable_already_exists(self):
        code = dedent("""\
            b = 1
            c = b
        """)
        self.mod.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            self._get_generate(code.index("b")).get_changes()

    def test_generating_variable_primary_cannot_be_determined(self):
        code = "c = can_not_be_found.b\n"
        self.mod.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            self._get_generate(code.rindex("b")).get_changes()

    def test_generating_modules_when_already_exists(self):
        code = "mod2\n"
        self.mod.write(code)
        generator = self._get_generate_module(code.rindex("mod"))
        with self.assertRaises(exceptions.RefactoringError):
            self.project.do(generator.get_changes())

    def test_generating_static_methods(self):
        code = dedent("""\
            class C(object):
                pass
            C.a_func()
        """)
        self.mod.write(code)
        changes = self._get_generate_function(code.index("a_func")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                class C(object):

                    @staticmethod
                    def a_func():
                        pass
                C.a_func()
            """),
            self.mod.read(),
        )

    def test_generating_methods(self):
        code = dedent("""\
            class C(object):
                pass
            c = C()
            c.a_func()
        """)
        self.mod.write(code)
        changes = self._get_generate_function(code.index("a_func")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                class C(object):

                    def a_func(self):
                        pass
                c = C()
                c.a_func()
            """),
            self.mod.read(),
        )

    def test_generating_constructors(self):
        code = dedent("""\
            class C(object):
                pass
            c = C()
        """)
        self.mod.write(code)
        changes = self._get_generate_function(code.rindex("C")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                class C(object):

                    def __init__(self):
                        pass
                c = C()
            """),
            self.mod.read(),
        )

    def test_generating_calls(self):
        code = dedent("""\
            class C(object):
                pass
            c = C()
            c()
        """)
        self.mod.write(code)
        changes = self._get_generate_function(code.rindex("c")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                class C(object):

                    def __call__(self):
                        pass
                c = C()
                c()
            """),
            self.mod.read(),
        )

    def test_generating_calls_in_other_modules(self):
        self.mod2.write(dedent("""\
            class C(object):
                pass
        """))
        code = dedent("""\
            import mod2
            c = mod2.C()
            c()
        """)
        self.mod.write(code)
        changes = self._get_generate_function(code.rindex("c")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                class C(object):

                    def __call__(self):
                        pass
            """),
            self.mod2.read(),
        )

    def test_generating_function_handling_arguments(self):
        code = "a_func(1)\n"
        self.mod.write(code)
        changes = self._get_generate_function(code.index("a_func")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                def a_func(arg0):
                    pass


                a_func(1)
            """),
            self.mod.read(),
        )

    def test_generating_function_handling_keyword_xarguments(self):
        code = "a_func(p=1)\n"
        self.mod.write(code)
        changes = self._get_generate_function(code.index("a_func")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                def a_func(p):
                    pass


                a_func(p=1)
            """),
            self.mod.read(),
        )

    def test_generating_function_handling_arguments_better_naming(self):
        code = dedent("""\
            a_var = 1
            a_func(a_var)
        """)
        self.mod.write(code)
        changes = self._get_generate_function(code.index("a_func")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                a_var = 1
                def a_func(a_var):
                    pass


                a_func(a_var)
            """),
            self.mod.read(),
        )

    def test_generating_variable_in_other_modules2(self):
        self.mod2.write("\n\n\nprint(1)\n")
        code = dedent("""\
            import mod2
            c = mod2.b
        """)
        self.mod.write(code)
        generator = self._get_generate(code.index("b"))
        self.project.do(generator.get_changes())
        self.assertEqual((self.mod2, 5), generator.get_location())
        self.assertEqual(
            dedent("""\



                print(1)


                b = None
            """),
            self.mod2.read(),
        )

    def test_generating_function_in_a_suite(self):
        code = dedent("""\
            if True:
                a_func()
        """)
        self.mod.write(code)
        changes = self._get_generate_function(code.index("a_func")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                def a_func():
                    pass


                if True:
                    a_func()
            """),
            self.mod.read(),
        )

    def test_generating_function_in_a_suite_in_a_function(self):
        code = dedent("""\
            def f():
                a = 1
                if 1:
                    g()
        """)
        self.mod.write(code)
        changes = self._get_generate_function(code.index("g()")).get_changes()
        self.project.do(changes)
        self.assertEqual(
            dedent("""\
                def f():
                    a = 1
                    def g():
                        pass
                    if 1:
                        g()
            """),
            self.mod.read(),
        )

    def test_create_generate_class_with_goal_resource(self):
        code = "c = C()\n"
        self.mod.write(code)

        result = generate.create_generate(
            "class", self.project, self.mod, code.index("C"), goal_resource=self.mod2
        )

        self.assertTrue(isinstance(result, generate.GenerateClass))
        self.assertEqual(result.goal_resource, self.mod2)

    def test_create_generate_class_without_goal_resource(self):
        code = "c = C()\n"
        self.mod.write(code)

        result = generate.create_generate(
            "class", self.project, self.mod, code.index("C")
        )

        self.assertTrue(isinstance(result, generate.GenerateClass))
        self.assertIsNone(result.goal_resource)
