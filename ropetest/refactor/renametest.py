import sys
import unittest
from textwrap import dedent
from rope.base import exceptions

import rope.base.codeanalyze
import rope.refactor.occurrences
from rope.refactor import rename
from rope.refactor.rename import Rename
from ropetest import testutils


class RenameTestMixin:
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def _local_rename(self, source_code, offset, new_name, **kwds):
        testmod = testutils.create_module(self.project, "testmod")
        testmod.write(source_code)
        changes = Rename(self.project, testmod, offset).get_changes(
            new_name, resources=[testmod], **kwds
        )
        self.project.do(changes)
        return testmod.read()

    def _rename(self, resource, offset, new_name, **kwds):
        changes = Rename(self.project, resource, offset).get_changes(new_name, **kwds)
        self.project.do(changes)


class RenameRefactoringTest(RenameTestMixin, unittest.TestCase):
    def test_local_variable_but_not_parameter(self):
        code = dedent("""\
            a = 10
            foo = dict(a=a)
        """)

        refactored = self._local_rename(code, 1, "new_a")
        self.assertEqual(
            dedent("""\
                new_a = 10
                foo = dict(a=new_a)
            """),
            refactored,
        )

    def test_simple_global_variable_renaming(self):
        refactored = self._local_rename("a_var = 20\n", 2, "new_var")
        self.assertEqual("new_var = 20\n", refactored)

    def test_variable_renaming_only_in_its_scope(self):
        refactored = self._local_rename(
            dedent("""\
                a_var = 20
                def a_func():
                    a_var = 10
            """),
            32,
            "new_var",
        )
        self.assertEqual(
            dedent("""\
                a_var = 20
                def a_func():
                    new_var = 10
            """),
            refactored,
        )

    def test_not_renaming_dot_name(self):
        refactored = self._local_rename(
            dedent("""\
                replace = True
                'aaa'.replace('a', 'b')
            """),
            1,
            "new_var",
        )
        self.assertEqual(
            dedent("""\
                new_var = True
                'aaa'.replace('a', 'b')
            """),
            refactored,
        )

    def test_renaming_multiple_names_in_the_same_line(self):
        refactored = self._local_rename(
            dedent("""\
                a_var = 10
                a_var = 10 + a_var / 2
            """),
            2,
            "new_var",
        )
        self.assertEqual(
            dedent("""\
                new_var = 10
                new_var = 10 + new_var / 2
            """),
            refactored,
        )

    def test_renaming_names_when_getting_some_attribute(self):
        refactored = self._local_rename(
            dedent("""\
                a_var = 'a b c'
                a_var.split('\\n')
            """),
            2,
            "new_var",
        )
        self.assertEqual(
            dedent("""\
                new_var = 'a b c'
                new_var.split('\\n')
            """),
            refactored,
        )

    def test_renaming_names_when_getting_some_attribute2(self):
        refactored = self._local_rename(
            dedent("""\
                a_var = 'a b c'
                a_var.split('\\n')
            """),
            20,
            "new_var",
        )
        self.assertEqual(
            dedent("""\
                new_var = 'a b c'
                new_var.split('\\n')
            """),
            refactored,
        )

    def test_renaming_function_parameters1(self):
        refactored = self._local_rename(
            dedent("""\
                def f(a_param):
                    print(a_param)
            """),
            8,
            "new_param",
        )
        self.assertEqual(
            dedent("""\
                def f(new_param):
                    print(new_param)
            """),
            refactored,
        )

    def test_renaming_function_parameters2(self):
        refactored = self._local_rename(
            dedent("""\
                def f(a_param):
                    print(a_param)
            """),
            30,
            "new_param",
        )
        self.assertEqual(
            dedent("""\
                def f(new_param):
                    print(new_param)
            """),
            refactored,
        )

    def test_renaming_occurrences_inside_functions(self):
        code = dedent("""\
            def a_func(p1):
                a = p1
            a_func(1)
        """)
        refactored = self._local_rename(code, code.index("p1") + 1, "new_param")
        self.assertEqual(
            dedent("""\
                def a_func(new_param):
                    a = new_param
                a_func(1)
            """),
            refactored,
        )

    def test_renaming_comprehension_loop_variables(self):
        code = "[b_var for b_var, c_var in d_var if b_var == c_var]"
        refactored = self._local_rename(code, code.index("b_var") + 1, "new_var")
        self.assertEqual(
            "[new_var for new_var, c_var in d_var if new_var == c_var]", refactored
        )

    def test_renaming_list_comprehension_loop_variables_in_assignment(self):
        code = "a_var = [b_var for b_var, c_var in d_var if b_var == c_var]"
        refactored = self._local_rename(code, code.index("b_var") + 1, "new_var")
        self.assertEqual(
            "a_var = [new_var for new_var, c_var in d_var if new_var == c_var]",
            refactored,
        )

    def test_renaming_generator_comprehension_loop_variables(self):
        code = "a_var = (b_var for b_var, c_var in d_var if b_var == c_var)"
        refactored = self._local_rename(code, code.index("b_var") + 1, "new_var")
        self.assertEqual(
            "a_var = (new_var for new_var, c_var in d_var if new_var == c_var)",
            refactored,
        )

    def test_renaming_comprehension_loop_variables_scope(self):
        code = dedent("""\
            [b_var for b_var, c_var in d_var if b_var == c_var]
            b_var = 10
        """)
        refactored = self._local_rename(code, code.index("b_var") + 1, "new_var")
        self.assertEqual(
            dedent("""\
                [new_var for new_var, c_var in d_var if new_var == c_var]
                b_var = 10
            """),
            refactored,
        )

    @testutils.only_for_versions_higher("3.8")
    def test_renaming_inline_assignment(self):
        code = dedent("""\
            while a_var := next(foo):
                print(a_var)
        """)
        refactored = self._local_rename(code, code.index("a_var") + 1, "new_var")
        self.assertEqual(
            dedent("""\
                while new_var := next(foo):
                    print(new_var)
            """),
            refactored,
        )

    def test_renaming_arguments_for_normal_args_changing_calls(self):
        code = dedent("""\
            def a_func(p1=None, p2=None):
                pass
            a_func(p2=1)
        """)
        refactored = self._local_rename(code, code.index("p2") + 1, "p3")
        self.assertEqual(
            dedent("""\
                def a_func(p1=None, p3=None):
                    pass
                a_func(p3=1)
            """),
            refactored,
        )

    def test_renaming_function_parameters_of_class_init(self):
        code = dedent("""\
            class A(object):
                def __init__(self, a_param):
                    pass
            a_var = A(a_param=1)
        """)
        refactored = self._local_rename(code, code.index("a_param") + 1, "new_param")
        expected = dedent("""\
            class A(object):
                def __init__(self, new_param):
                    pass
            a_var = A(new_param=1)
        """)
        self.assertEqual(expected, refactored)

    def test_rename_functions_parameters_and_occurrences_in_other_modules(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write(dedent("""\
            def a_func(a_param):
                print(a_param)
        """))
        mod2.write(dedent("""\
            from mod1 import a_func
            a_func(a_param=10)
        """))
        self._rename(mod1, mod1.read().index("a_param") + 1, "new_param")
        self.assertEqual(
            dedent("""\
                def a_func(new_param):
                    print(new_param)
            """),
            mod1.read(),
        )
        self.assertEqual(
            dedent("""\
                from mod1 import a_func
                a_func(new_param=10)
            """),
            mod2.read(),
        )

    def test_renaming_with_backslash_continued_names(self):
        refactored = self._local_rename(
            "replace = True\n'ali'.\\\nreplace\n", 2, "is_replace"
        )
        self.assertEqual("is_replace = True\n'ali'.\\\nreplace\n", refactored)

    def test_renaming_occurrence_in_f_string(self):
        code = dedent("""\
            a_var = 20
            a_string=f'value: {a_var}'
        """)
        expected = dedent("""\
            new_var = 20
            a_string=f'value: {new_var}'
        """)
        refactored = self._local_rename(code, 2, "new_var")
        self.assertEqual(expected, refactored)

    def test_renaming_occurrence_in_nested_f_string(self):
        code = dedent("""\
            a_var = 20
            a_string=f'{f"{a_var}"}'
        """)
        expected = dedent("""\
            new_var = 20
            a_string=f'{f"{new_var}"}'
        """)
        refactored = self._local_rename(code, 2, "new_var")
        self.assertEqual(expected, refactored)

    def test_renaming_attribute_occurrences_in_f_string(self):
        code = dedent("""\
            class MyClass:
                def __init__(self):
                    self.abc = 123

                def func(obj):
                    print(f'{obj.abc}')
                    return obj.abc
        """)
        expected = dedent("""\
            class MyClass:
                def __init__(self):
                    self.new_var = 123

                def func(obj):
                    print(f'{obj.new_var}')
                    return obj.new_var
        """)
        refactored = self._local_rename(code, code.index('abc'), "new_var")
        self.assertEqual(expected, refactored)

    def test_not_renaming_string_contents_in_f_string(self):
        refactored = self._local_rename(
            "a_var = 20\na_string=f'{\"a_var\"}'\n", 2, "new_var"
        )
        self.assertEqual(
            dedent("""\
                new_var = 20
                a_string=f'{"a_var"}'
            """),
            refactored,
        )

    def test_not_renaming_string_contents(self):
        refactored = self._local_rename("a_var = 20\na_string='a_var'\n", 2, "new_var")
        self.assertEqual(
            dedent("""\
                new_var = 20
                a_string='a_var'
            """),
            refactored,
        )

    def test_not_renaming_comment_contents(self):
        refactored = self._local_rename("a_var = 20\n# a_var\n", 2, "new_var")
        self.assertEqual(
            dedent("""\
                new_var = 20
                # a_var
            """),
            refactored,
        )

    def test_renaming_all_occurrences_in_containing_scope(self):
        code = dedent("""\
            if True:
                a_var = 1
            else:
                a_var = 20
        """)
        refactored = self._local_rename(code, 16, "new_var")
        self.assertEqual(
            dedent("""\
                if True:
                    new_var = 1
                else:
                    new_var = 20
            """),
            refactored,
        )

    def test_renaming_a_variable_with_arguement_name(self):
        code = dedent("""\
            a_var = 10
            def a_func(a_var):
                print(a_var)
        """)
        refactored = self._local_rename(code, 1, "new_var")
        self.assertEqual(
            dedent("""\
                new_var = 10
                def a_func(a_var):
                    print(a_var)
            """),
            refactored,
        )

    def test_renaming_an_arguement_with_variable_name(self):
        code = dedent("""\
            a_var = 10
            def a_func(a_var):
                print(a_var)
        """)
        refactored = self._local_rename(code, len(code) - 3, "new_var")
        self.assertEqual(
            dedent("""\
                a_var = 10
                def a_func(new_var):
                    print(new_var)
            """),
            refactored,
        )

    def test_renaming_function_with_local_variable_name(self):
        code = dedent("""\
            def a_func():
                a_func=20
            a_func()""")
        refactored = self._local_rename(code, len(code) - 3, "new_func")
        self.assertEqual(
            dedent("""\
                def new_func():
                    a_func=20
                new_func()"""),
            refactored,
        )

    def test_renaming_functions(self):
        code = dedent("""\
            def a_func():
                pass
            a_func()
        """)
        refactored = self._local_rename(code, len(code) - 5, "new_func")
        self.assertEqual(
            dedent("""\
                def new_func():
                    pass
                new_func()
            """),
            refactored,
        )

    def test_renaming_async_function(self):
        code = dedent("""\
            async def a_func():
                pass
            a_func()""")
        refactored = self._local_rename(code, len(code) - 5, "new_func")
        self.assertEqual(
            dedent("""\
                async def new_func():
                    pass
                new_func()"""),
            refactored,
        )

    def test_renaming_await(self):
        code = dedent("""\
            async def b_func():
                pass
            async def a_func():
                await b_func()""")
        refactored = self._local_rename(code, len(code) - 5, "new_func")
        self.assertEqual(
            dedent("""\
                async def new_func():
                    pass
                async def a_func():
                    await new_func()"""),
            refactored,
        )

    def test_renaming_functions_across_modules(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            def a_func():
                pass
            a_func()
        """))
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write(dedent("""\
            import mod1
            mod1.a_func()
        """))
        self._rename(mod1, len(mod1.read()) - 5, "new_func")
        self.assertEqual(
            dedent("""\
                def new_func():
                    pass
                new_func()
            """),
            mod1.read(),
        )
        self.assertEqual(
            dedent("""\
                import mod1
                mod1.new_func()
            """),
            mod2.read(),
        )

    def test_renaming_functions_across_modules_from_import(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            def a_func():
                pass
            a_func()
        """))
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write(dedent("""\
            from mod1 import a_func
            a_func()
        """))
        self._rename(mod1, len(mod1.read()) - 5, "new_func")
        self.assertEqual(
            dedent("""\
                def new_func():
                    pass
                new_func()
            """),
            mod1.read(),
        )
        self.assertEqual(
            dedent("""\
                from mod1 import new_func
                new_func()
            """),
            mod2.read(),
        )

    def test_renaming_functions_from_another_module(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            def a_func():
                pass
            a_func()
        """))
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write(dedent("""\
            import mod1
            mod1.a_func()
        """))
        self._rename(mod2, len(mod2.read()) - 5, "new_func")
        self.assertEqual(
            dedent("""\
                def new_func():
                    pass
                new_func()
            """),
            mod1.read(),
        )
        self.assertEqual(
            dedent("""\
                import mod1
                mod1.new_func()
            """),
            mod2.read(),
        )

    def test_applying_all_changes_together(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            import mod2
            mod2.a_func()
        """))
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write(dedent("""\
            def a_func():
                pass
            a_func()
        """))
        self._rename(mod2, len(mod2.read()) - 5, "new_func")
        self.assertEqual(
            dedent("""\
                import mod2
                mod2.new_func()
            """),
            mod1.read(),
        )
        self.assertEqual(
            dedent("""\
                def new_func():
                    pass
                new_func()
            """),
            mod2.read(),
        )

    def test_renaming_modules(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            def a_func():
                pass
        """))
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write("from mod1 import a_func\n")
        self._rename(mod2, mod2.read().index("mod1") + 1, "newmod")
        self.assertTrue(
            not mod1.exists() and self.project.find_module("newmod") is not None
        )
        self.assertEqual("from newmod import a_func\n", mod2.read())

    def test_renaming_modules_aliased(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            def a_func():
                pass
        """))
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write(dedent("""\
            import mod1 as m
            m.a_func()
        """))
        self._rename(mod1, None, "newmod")
        self.assertTrue(
            not mod1.exists() and self.project.find_module("newmod") is not None
        )
        self.assertEqual("import newmod as m\nm.a_func()\n", mod2.read())

    def test_renaming_packages(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod1 = testutils.create_module(self.project, "mod1", pkg)
        mod1.write(dedent("""\
            def a_func():
                pass
        """))
        mod2 = testutils.create_module(self.project, "mod2", pkg)
        mod2.write("from pkg.mod1 import a_func\n")
        self._rename(mod2, 6, "newpkg")
        self.assertTrue(self.project.find_module("newpkg.mod1") is not None)
        new_mod2 = self.project.find_module("newpkg.mod2")
        self.assertEqual("from newpkg.mod1 import a_func\n", new_mod2.read())

    def test_module_dependencies(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            class AClass(object):
                pass
        """))
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write(dedent("""\
            import mod1
            a_var = mod1.AClass()
        """))
        self.project.get_pymodule(mod2).get_attributes()["mod1"]
        mod1.write(dedent("""\
            def AClass():
                return 0
        """))

        self._rename(mod2, len(mod2.read()) - 3, "a_func")
        self.assertEqual(
            dedent("""\
                def a_func():
                    return 0
            """),
            mod1.read(),
        )
        self.assertEqual(
            dedent("""\
                import mod1
                a_var = mod1.a_func()
            """),
            mod2.read(),
        )

    def test_renaming_class_attributes(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            class AClass(object):
                def __init__(self):
                    self.an_attr = 10
        """))
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write(dedent("""\
            import mod1
            a_var = mod1.AClass()
            another_var = a_var.an_attr"""))

        self._rename(mod1, mod1.read().index("an_attr"), "attr")
        self.assertEqual(
            dedent("""\
                class AClass(object):
                    def __init__(self):
                        self.attr = 10
            """),
            mod1.read(),
        )
        self.assertEqual(
            dedent("""\
                import mod1
                a_var = mod1.AClass()
                another_var = a_var.attr"""),
            mod2.read(),
        )

    def test_renaming_class_attributes2(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            class AClass(object):
                def __init__(self):
                    an_attr = 10
                    self.an_attr = 10
        """))
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write(dedent("""\
            import mod1
            a_var = mod1.AClass()
            another_var = a_var.an_attr"""))

        self._rename(mod1, mod1.read().rindex("an_attr"), "attr")
        self.assertEqual(
            dedent("""\
                class AClass(object):
                    def __init__(self):
                        an_attr = 10
                        self.attr = 10
            """),
            mod1.read(),
        )
        self.assertEqual(
            dedent("""\
                import mod1
                a_var = mod1.AClass()
                another_var = a_var.attr"""),
            mod2.read(),
        )

    def test_undoing_refactorings(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            def a_func():
                pass
            a_func()
        """))
        self._rename(mod1, len(mod1.read()) - 5, "new_func")
        self.project.history.undo()
        self.assertEqual(
            dedent("""\
                def a_func():
                    pass
                a_func()
            """),
            mod1.read(),
        )

    def test_undoing_renaming_modules(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(dedent("""\
            def a_func():
                pass
        """))
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write("from mod1 import a_func\n")
        self._rename(mod2, 6, "newmod")
        self.project.history.undo()
        self.assertEqual("mod1.py", mod1.path)
        self.assertEqual("from mod1 import a_func\n", mod2.read())

    def test_rename_in_module_renaming_one_letter_names_for_expressions(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write("a = 10\nprint(1+a)\n")
        pymod = self.project.get_module("mod1")
        old_pyname = pymod["a"]
        finder = rope.refactor.occurrences.create_finder(self.project, "a", old_pyname)
        refactored = rename.rename_in_module(
            finder, "new_var", pymodule=pymod, replace_primary=True
        )
        self.assertEqual(
            dedent("""\
                new_var = 10
                print(1+new_var)
            """),
            refactored,
        )

    def test_renaming_for_loop_variable(self):
        code = dedent("""\
            for var in range(10):
                print(var)
        """)
        refactored = self._local_rename(code, code.find("var") + 1, "new_var")
        self.assertEqual(
            dedent("""\
                for new_var in range(10):
                    print(new_var)
            """),
            refactored,
        )

    def test_renaming_async_for_loop_variable(self):
        code = dedent("""\
            async def func():
                async for var in range(10):
                    print(var)
        """)
        refactored = self._local_rename(code, code.find("var") + 1, "new_var")
        self.assertEqual(
            dedent("""\
                async def func():
                    async for new_var in range(10):
                        print(new_var)
            """),
            refactored,
        )

    def test_renaming_async_with_context_manager(self):
        code = dedent("""\
            def a_cm(): pass
            async def a_func():
                async with a_cm() as x: pass""")
        refactored = self._local_rename(code, code.find("a_cm") + 1, "another_cm")
        expected = dedent("""\
            def another_cm(): pass
            async def a_func():
                async with another_cm() as x: pass""")
        self.assertEqual(refactored, expected)

    def test_renaming_async_with_as_variable(self):
        code = dedent("""\
            async def func():
                async with a_func() as var:
                    print(var)
        """)
        refactored = self._local_rename(code, code.find("var") + 1, "new_var")
        self.assertEqual(
            dedent("""\
                async def func():
                    async with a_func() as new_var:
                        print(new_var)
            """),
            refactored,
        )

    def test_renaming_parameters(self):
        code = dedent("""\
            def a_func(param):
                print(param)
            a_func(param=hey)
        """)
        refactored = self._local_rename(code, code.find("param") + 1, "new_param")
        self.assertEqual(
            dedent("""\
                def a_func(new_param):
                    print(new_param)
                a_func(new_param=hey)
            """),
            refactored,
        )

    def test_renaming_assigned_parameters(self):
        code = dedent("""\
            def f(p):
                p = p + 1
                return p
            f(p=1)
        """)
        refactored = self._local_rename(code, code.find("p"), "arg")
        self.assertEqual(
            dedent("""\
                def f(arg):
                    arg = arg + 1
                    return arg
                f(arg=1)
            """),
            refactored,
        )

    def test_renaming_parameters_not_renaming_others(self):
        code = dedent("""\
            def a_func(param):
                print(param)
            param=10
            a_func(param)
        """)
        refactored = self._local_rename(code, code.find("param") + 1, "new_param")
        self.assertEqual(
            dedent("""\
                def a_func(new_param):
                    print(new_param)
                param=10
                a_func(param)
            """),
            refactored,
        )

    def test_renaming_parameters_not_renaming_others2(self):
        code = dedent("""\
            def a_func(param):
                print(param)
            param=10
            a_func(param=param)""")
        refactored = self._local_rename(code, code.find("param") + 1, "new_param")
        self.assertEqual(
            dedent("""\
                def a_func(new_param):
                    print(new_param)
                param=10
                a_func(new_param=param)"""),
            refactored,
        )

    def test_renaming_parameters_with_multiple_params(self):
        code = dedent("""\
            def a_func(param1, param2):
                print(param1)
            a_func(param1=1, param2=2)
        """)
        refactored = self._local_rename(code, code.find("param1") + 1, "new_param")
        self.assertEqual(
            dedent("""\
                def a_func(new_param, param2):
                    print(new_param)
                a_func(new_param=1, param2=2)
            """),
            refactored,
        )

    def test_renaming_parameters_with_multiple_params2(self):
        code = dedent("""\
            def a_func(param1, param2):
                print(param1)
            a_func(param1=1, param2=2)
        """)
        refactored = self._local_rename(code, code.rfind("param2") + 1, "new_param")
        self.assertEqual(
            dedent("""\
                def a_func(param1, new_param):
                    print(param1)
                a_func(param1=1, new_param=2)
            """),
            refactored,
        )

    def test_renaming_parameters_on_calls(self):
        code = dedent("""\
            def a_func(param):
                print(param)
            a_func(param = hey)
        """)
        refactored = self._local_rename(code, code.rfind("param") + 1, "new_param")
        self.assertEqual(
            dedent("""\
                def a_func(new_param):
                    print(new_param)
                a_func(new_param = hey)
            """),
            refactored,
        )

    def test_renaming_parameters_spaces_before_call(self):
        code = dedent("""\
            def a_func(param):
                print(param)
            a_func  (param=hey)
        """)
        refactored = self._local_rename(code, code.rfind("param") + 1, "new_param")
        self.assertEqual(
            dedent("""\
                def a_func(new_param):
                    print(new_param)
                a_func  (new_param=hey)
            """),
            refactored,
        )

    def test_renaming_parameter_like_objects_after_keywords(self):
        code = dedent("""\
            def a_func(param):
                print(param)
            dict(param=hey)
        """)
        refactored = self._local_rename(code, code.find("param") + 1, "new_param")
        self.assertEqual(
            dedent("""\
                def a_func(new_param):
                    print(new_param)
                dict(param=hey)
            """),
            refactored,
        )

    def test_renaming_variables_in_init_dot_pys(self):
        pkg = testutils.create_package(self.project, "pkg")
        init_dot_py = pkg.get_child("__init__.py")
        init_dot_py.write("a_var = 10\n")
        mod = testutils.create_module(self.project, "mod")
        mod.write("import pkg\nprint(pkg.a_var)\n")
        self._rename(mod, mod.read().index("a_var") + 1, "new_var")
        self.assertEqual("new_var = 10\n", init_dot_py.read())
        self.assertEqual("import pkg\nprint(pkg.new_var)\n", mod.read())

    def test_renaming_variables_in_init_dot_pys2(self):
        pkg = testutils.create_package(self.project, "pkg")
        init_dot_py = pkg.get_child("__init__.py")
        init_dot_py.write("a_var = 10\n")
        mod = testutils.create_module(self.project, "mod")
        mod.write("import pkg\nprint(pkg.a_var)\n")
        self._rename(init_dot_py, init_dot_py.read().index("a_var") + 1, "new_var")
        self.assertEqual("new_var = 10\n", init_dot_py.read())
        self.assertEqual("import pkg\nprint(pkg.new_var)\n", mod.read())

    def test_renaming_variables_in_init_dot_pys3(self):
        pkg = testutils.create_package(self.project, "pkg")
        init_dot_py = pkg.get_child("__init__.py")
        init_dot_py.write("a_var = 10\n")
        mod = testutils.create_module(self.project, "mod")
        mod.write("import pkg\nprint(pkg.a_var)\n")
        self._rename(mod, mod.read().index("a_var") + 1, "new_var")
        self.assertEqual("new_var = 10\n", init_dot_py.read())
        self.assertEqual("import pkg\nprint(pkg.new_var)\n", mod.read())

    def test_renaming_resources_using_rename_module_refactoring(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write("a_var = 1")
        mod2.write("import mod1\nmy_var = mod1.a_var\n")
        renamer = rename.Rename(self.project, mod1)
        renamer.get_changes("newmod").do()
        self.assertEqual("import newmod\nmy_var = newmod.a_var\n", mod2.read())

    def test_renam_resources_using_rename_module_refactor_for_packages(self):
        mod1 = testutils.create_module(self.project, "mod1")
        pkg = testutils.create_package(self.project, "pkg")
        mod1.write("import pkg\nmy_pkg = pkg")
        renamer = rename.Rename(self.project, pkg)
        renamer.get_changes("newpkg").do()
        self.assertEqual("import newpkg\nmy_pkg = newpkg", mod1.read())

    def test_renam_resources_use_rename_module_refactor_for_init_dot_py(self):
        mod1 = testutils.create_module(self.project, "mod1")
        pkg = testutils.create_package(self.project, "pkg")
        mod1.write("import pkg\nmy_pkg = pkg")
        renamer = rename.Rename(self.project, pkg.get_child("__init__.py"))
        renamer.get_changes("newpkg").do()
        self.assertEqual("import newpkg\nmy_pkg = newpkg", mod1.read())

    def test_renaming_global_variables(self):
        code = dedent("""\
            a_var = 1
            def a_func():
                global a_var
                var = a_var
        """)
        refactored = self._local_rename(code, code.index("a_var"), "new_var")
        self.assertEqual(
            dedent("""\
                new_var = 1
                def a_func():
                    global new_var
                    var = new_var
            """),
            refactored,
        )

    def test_renaming_global_variables2(self):
        code = dedent("""\
            a_var = 1
            def a_func():
                global a_var
                var = a_var
        """)
        refactored = self._local_rename(code, code.rindex("a_var"), "new_var")
        self.assertEqual(
            dedent("""\
                new_var = 1
                def a_func():
                    global new_var
                    var = new_var
            """),
            refactored,
        )

    def test_renaming_when_unsure(self):
        code = dedent("""\
            class C(object):
                def a_func(self):
                    pass
            def f(arg):
                arg.a_func()
        """)
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(code)
        self._rename(mod1, code.index("a_func"), "new_func", unsure=self._true)
        self.assertEqual(
            dedent("""\
                class C(object):
                    def new_func(self):
                        pass
                def f(arg):
                    arg.new_func()
            """),
            mod1.read(),
        )

    def _true(self, *args):
        return True

    def test_renaming_when_unsure_with_confirmation(self):
        def confirm(occurrence):
            return False

        code = dedent("""\
            class C(object):
                def a_func(self):
                    pass
            def f(arg):
                arg.a_func()
        """)
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(code)
        self._rename(mod1, code.index("a_func"), "new_func", unsure=confirm)
        self.assertEqual(
            dedent("""\
                class C(object):
                    def new_func(self):
                        pass
                def f(arg):
                    arg.a_func()
            """),
            mod1.read(),
        )

    def test_renaming_when_unsure_not_renaming_knowns(self):
        code = dedent("""\
            class C1(object):
                def a_func(self):
                    pass
            class C2(object):
                def a_func(self):
                    pass
            c1 = C1()
            c1.a_func()
            c2 = C2()
            c2.a_func()
        """)
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(code)
        self._rename(mod1, code.index("a_func"), "new_func", unsure=self._true)
        self.assertEqual(
            dedent("""\
                class C1(object):
                    def new_func(self):
                        pass
                class C2(object):
                    def a_func(self):
                        pass
                c1 = C1()
                c1.new_func()
                c2 = C2()
                c2.a_func()
            """),
            mod1.read(),
        )

    def test_renaming_in_strings_and_comments(self):
        code = dedent("""\
            a_var = 1
            # a_var
        """)
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(code)
        self._rename(mod1, code.index("a_var"), "new_var", docs=True)
        self.assertEqual(
            dedent("""\
                new_var = 1
                # new_var
            """),
            mod1.read(),
        )

    def test_not_renaming_in_strings_and_comments_where_not_visible(self):
        code = dedent("""\
            def f():
                a_var = 1
            # a_var
        """)
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(code)
        self._rename(mod1, code.index("a_var"), "new_var", docs=True)
        self.assertEqual(
            dedent("""\
                def f():
                    new_var = 1
                # a_var
            """),
            mod1.read(),
        )

    def test_not_renaming_all_text_occurrences_in_strings_and_comments(self):
        code = dedent("""\
            a_var = 1
            # a_vard _a_var
        """)
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(code)
        self._rename(mod1, code.index("a_var"), "new_var", docs=True)
        self.assertEqual(
            dedent("""\
                new_var = 1
                # a_vard _a_var
            """),
            mod1.read(),
        )

    def test_renaming_occurrences_in_overwritten_scopes(self):
        refactored = self._local_rename(
            dedent("""\
                a_var = 20
                def f():
                    print(a_var)
                def f():
                    print(a_var)
            """),
            2,
            "new_var",
        )
        self.assertEqual(
            dedent("""\
                new_var = 20
                def f():
                    print(new_var)
                def f():
                    print(new_var)
            """),
            refactored,
        )

    def test_renaming_occurrences_in_overwritten_scopes2(self):
        code = dedent("""\
            def f():
                a_var = 1
                print(a_var)
            def f():
                a_var = 1
                print(a_var)
        """)
        refactored = self._local_rename(code, code.index("a_var") + 1, "new_var")
        self.assertEqual(code.replace("a_var", "new_var", 2), refactored)

    @testutils.only_for_versions_higher("3.5")
    def test_renaming_in_generalized_dict_unpacking(self):
        code = dedent("""\
            a_var = {**{'stuff': 'can'}, **{'stuff': 'crayon'}}

            if "stuff" in a_var:
                print("ya")
        """)
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(code)
        refactored = self._local_rename(code, code.index("a_var") + 1, "new_var")
        expected = dedent("""\
            new_var = {**{'stuff': 'can'}, **{'stuff': 'crayon'}}

            if "stuff" in new_var:
                print("ya")
        """)
        self.assertEqual(expected, refactored)

    def test_dos_line_ending_and_renaming(self):
        code = "\r\na = 1\r\n\r\nprint(2 + a + 2)\r\n"
        offset = code.replace("\r\n", "\n").rindex("a")
        refactored = self._local_rename(code, offset, "b")
        self.assertEqual(
            "\nb = 1\n\nprint(2 + b + 2)\n", refactored.replace("\r\n", "\n")
        )

    def test_multi_byte_strs_and_renaming(self):
        s = "{LATIN SMALL LETTER I WITH DIAERESIS}" * 4
        code = "# -*- coding: utf-8 -*-\n# " + s + "\na = 1\nprint(2 + a + 2)\n"
        refactored = self._local_rename(code, code.rindex("a"), "b")
        self.assertEqual(
            "# -*- coding: utf-8 -*-\n# " + s + "\nb = 1\nprint(2 + b + 2)\n",
            refactored,
        )

    def test_resources_parameter(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write(dedent("""\
            def f():
                pass
        """))
        mod2.write(dedent("""\
            import mod1
            mod1.f()
        """))
        self._rename(mod1, mod1.read().rindex("f"), "g", resources=[mod1])
        self.assertEqual(
            dedent("""\
                def g():
                    pass
            """),
            mod1.read(),
        )
        self.assertEqual(
            dedent("""\
                import mod1
                mod1.f()
            """),
            mod2.read(),
        )

    def test_resources_parameter_not_changing_defining_module(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write(dedent("""\
            def f():
                pass
        """))
        mod2.write(dedent("""\
            import mod1
            mod1.f()
        """))
        self._rename(mod1, mod1.read().rindex("f"), "g", resources=[mod2])
        self.assertEqual(
            dedent("""\
                def f():
                    pass
            """),
            mod1.read(),
        )
        self.assertEqual(
            dedent("""\
                import mod1
                mod1.g()
            """),
            mod2.read(),
        )

    # XXX: with variables should not leak
    def xxx_test_with_statement_variables_should_not_leak(self):
        code = dedent("""\
            f = 1
            with open("1.txt") as f:
                print(f)
        """)
        if sys.version_info < (2, 6, 0):
            code = "from __future__ import with_statement\n" + code
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write(code)
        self._rename(mod1, code.rindex("f"), "file")
        expected = dedent("""\
            f = 1
            with open("1.txt") as file:
                print(file)
        """)
        self.assertEqual(expected, mod1.read())

    def test_rename_in_list_comprehension(self):
        code = dedent("""\
            some_var = 1
            compr = [some_var for some_var in range(10)]
        """)
        offset = code.index("some_var")
        refactored = self._local_rename(code, offset, "new_var")
        expected = dedent("""\
            new_var = 1
            compr = [some_var for some_var in range(10)]
        """)
        self.assertEqual(refactored, expected)

    def test_renaming_modules_aliased_with_dots(self):
        pkg = testutils.create_package(self.project, "json")
        mod1 = testutils.create_module(self.project, "utils", pkg)

        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write(dedent("""\
            import json.utils as stdlib_json_utils
        """))
        self._rename(pkg, None, "new_json")
        self.assertTrue(
            not mod1.exists() and self.project.find_module("new_json.utils") is not None
        )
        self.assertEqual("import new_json.utils as stdlib_json_utils\n", mod2.read())

    def test_renaming_modules_aliased_many_dots(self):
        pkg = testutils.create_package(self.project, "json")
        mod1 = testutils.create_module(self.project, "utils", pkg)

        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write(dedent("""\
            import json.utils.a as stdlib_json_utils
        """))
        self._rename(pkg, None, "new_json")
        self.assertTrue(
            not mod1.exists() and self.project.find_module("new_json.utils") is not None
        )
        self.assertEqual("import new_json.utils.a as stdlib_json_utils\n", mod2.read())

    def test_rename_refuses_renaming_to_python_keyword(self):
        with self.assertRaises(exceptions.RefactoringError, msg="Invalid refactoring target name. 'class' is a Python keyword."):
            self._local_rename("a_var = 20\n", 2, "class")


class RenameRefactoringWithSuperclassTest(RenameTestMixin, unittest.TestCase):
    ORIGINAL_CODE = dedent("""\
        class Parent:
            def a_method(self):
                pass

        class Child(Parent):
            def a_method(self, strg):
                return super(Child, self).a_method(strg, *args, **kwargs)
    """)
    BOTH_RENAMED = dedent("""\
        class Parent:
            def new_method(self):
                pass

        class Child(Parent):
            def new_method(self, strg):
                return super(Child, self).new_method(strg, *args, **kwargs)
    """)

    PARENT_RENAMED = dedent("""\
        class Parent:
            def new_method(self):
                pass

        class Child(Parent):
            def a_method(self, strg):
                return super(Child, self).new_method(strg, *args, **kwargs)
    """)

    CHILD_RENAMED = dedent("""\
        class Parent:
            def a_method(self):
                pass

        class Child(Parent):
            def new_method(self, strg):
                return super(Child, self).a_method(strg, *args, **kwargs)
    """)

    FROM_PARENT = "a_method(self)"  # from Parent.a_method
    FROM_CHILD = "a_method(self, strg"  # from Child.a_method
    FROM_CALLER = "a_method(strg, *args"  # from super() line

    def test_rename_with_superclass_in_hierarchy_from_parent(self):
        code = self.ORIGINAL_CODE
        offset = code.index(self.FROM_PARENT)
        refactored = self._local_rename(code, offset, "new_method", in_hierarchy=True)
        self.assertEqual(refactored, self.BOTH_RENAMED)

    def test_rename_with_superclass_not_in_hierarchy_from_parent(self):
        code = self.ORIGINAL_CODE
        offset = code.index(self.FROM_PARENT)
        refactored = self._local_rename(code, offset, "new_method", in_hierarchy=False)
        self.assertEqual(refactored, self.PARENT_RENAMED)

    def test_rename_with_superclass_in_hierarchy_from_child(self):
        code = self.ORIGINAL_CODE
        offset = code.index(self.FROM_CHILD)
        refactored = self._local_rename(code, offset, "new_method", in_hierarchy=True)
        self.assertEqual(refactored, self.BOTH_RENAMED)

    def test_rename_with_superclass_not_in_hierarchy_from_child(self):
        code = self.ORIGINAL_CODE
        offset = code.index(self.FROM_CHILD)
        refactored = self._local_rename(code, offset, "new_method", in_hierarchy=False)
        self.assertEqual(refactored, self.CHILD_RENAMED)

    def test_rename_with_superclass_in_hierarchy_from_caller(self):
        code = self.ORIGINAL_CODE
        offset = code.index(self.FROM_CALLER)
        refactored = self._local_rename(code, offset, "new_method", in_hierarchy=True)
        self.assertEqual(refactored, self.BOTH_RENAMED)

    def test_rename_with_superclass_not_in_hierarchy_from_caller(self):
        code = self.ORIGINAL_CODE
        offset = code.index(self.FROM_CALLER)
        refactored = self._local_rename(code, offset, "new_method", in_hierarchy=False)
        self.assertEqual(refactored, self.PARENT_RENAMED)

    def test_renaming_methods_in_subclasses(self):
        mod = testutils.create_module(self.project, "mod1")
        mod.write(dedent("""\
            class A(object):
                def a_method(self):
                    pass
            class B(A):
                def a_method(self):
                    pass
        """))

        self._rename(
            mod, mod.read().rindex("a_method") + 1, "new_method", in_hierarchy=True
        )
        self.assertEqual(
            dedent("""\
                class A(object):
                    def new_method(self):
                        pass
                class B(A):
                    def new_method(self):
                        pass
            """),
            mod.read(),
        )

    def test_renaming_methods_in_sibling_classes(self):
        mod = testutils.create_module(self.project, "mod1")
        mod.write(dedent("""\
            class A(object):
                def a_method(self):
                    pass
            class B(A):
                def a_method(self):
                    pass
            class C(A):
                def a_method(self):
                    pass
        """))

        self._rename(
            mod, mod.read().rindex("a_method") + 1, "new_method", in_hierarchy=True
        )
        self.assertEqual(
            dedent("""\
                class A(object):
                    def new_method(self):
                        pass
                class B(A):
                    def new_method(self):
                        pass
                class C(A):
                    def new_method(self):
                        pass
            """),
            mod.read(),
        )

    def test_not_renaming_methods_in_hierarchies(self):
        mod = testutils.create_module(self.project, "mod1")
        mod.write(dedent("""\
            class A(object):
                def a_method(self):
                    pass
            class B(A):
                def a_method(self):
                    pass
        """))

        self._rename(
            mod, mod.read().rindex("a_method") + 1, "new_method", in_hierarchy=False
        )
        self.assertEqual(
            dedent("""\
                class A(object):
                    def a_method(self):
                        pass
                class B(A):
                    def new_method(self):
                        pass
            """),
            mod.read(),
        )


class ChangeOccurrencesTest(unittest.TestCase):
    def setUp(self):
        self.project = testutils.sample_project()
        self.mod = testutils.create_module(self.project, "mod")

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def test_simple_case(self):
        self.mod.write(dedent("""\
            a_var = 1
            print(a_var)
        """))
        changer = rename.ChangeOccurrences(
            self.project, self.mod, self.mod.read().index("a_var")
        )
        changer.get_changes("new_var").do()
        self.assertEqual(
            dedent("""\
                new_var = 1
                print(new_var)
            """),
            self.mod.read(),
        )

    def test_only_performing_inside_scopes(self):
        self.mod.write(dedent("""\
            a_var = 1
            new_var = 2
            def f():
                print(a_var)
        """))
        changer = rename.ChangeOccurrences(
            self.project, self.mod, self.mod.read().rindex("a_var")
        )
        changer.get_changes("new_var").do()
        self.assertEqual(
            dedent("""\
                a_var = 1
                new_var = 2
                def f():
                    print(new_var)
            """),
            self.mod.read(),
        )

    def test_only_performing_on_calls(self):
        self.mod.write(dedent("""\
            def f1():
                pass
            def f2():
                pass
            g = f1
            a = f1()
        """))
        changer = rename.ChangeOccurrences(
            self.project, self.mod, self.mod.read().rindex("f1")
        )
        changer.get_changes("f2", only_calls=True).do()
        self.assertEqual(
            dedent("""\
                def f1():
                    pass
                def f2():
                    pass
                g = f1
                a = f2()
            """),
            self.mod.read(),
        )

    def test_only_performing_on_reads(self):
        self.mod.write(dedent("""\
            a = 1
            b = 2
            print(a)
        """))
        changer = rename.ChangeOccurrences(
            self.project, self.mod, self.mod.read().rindex("a")
        )
        changer.get_changes("b", writes=False).do()
        self.assertEqual(
            dedent("""\
                a = 1
                b = 2
                print(b)
            """),
            self.mod.read(),
        )


class ImplicitInterfacesTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project(validate_objectdb=True)
        self.pycore = self.project.pycore
        self.mod1 = testutils.create_module(self.project, "mod1")
        self.mod2 = testutils.create_module(self.project, "mod2")

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def _rename(self, resource, offset, new_name, **kwds):
        changes = Rename(self.project, resource, offset).get_changes(new_name, **kwds)
        self.project.do(changes)

    def test_performing_rename_on_parameters(self):
        self.mod1.write("def f(arg):\n    arg.run()\n")
        self.mod2.write(dedent("""\
            import mod1


            class A(object):
                def run(self):
                    pass
            class B(object):
                def run(self):
                    pass
            mod1.f(A())
            mod1.f(B())
        """))
        self.pycore.analyze_module(self.mod2)
        self._rename(self.mod1, self.mod1.read().index("run"), "newrun")
        self.assertEqual("def f(arg):\n    arg.newrun()\n", self.mod1.read())
        self.assertEqual(
            dedent("""\
                import mod1


                class A(object):
                    def newrun(self):
                        pass
                class B(object):
                    def newrun(self):
                        pass
                mod1.f(A())
                mod1.f(B())
            """),
            self.mod2.read(),
        )
