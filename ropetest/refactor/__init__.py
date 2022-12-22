import unittest
from textwrap import dedent

import rope.base.taskhandle
import rope.refactor.introduce_parameter
import ropetest.refactor.extracttest
import ropetest.refactor.importutilstest
import ropetest.refactor.inlinetest
import ropetest.refactor.movetest
import ropetest.refactor.multiprojecttest
import ropetest.refactor.patchedasttest
import ropetest.refactor.renametest
import ropetest.refactor.restructuretest
import ropetest.refactor.suitestest
import ropetest.refactor.usefunctiontest
from rope.base.exceptions import InterruptedTaskError, RefactoringError
from rope.refactor.encapsulate_field import EncapsulateField
from rope.refactor.introduce_factory import IntroduceFactory
from rope.refactor.localtofield import LocalToField
from rope.refactor.method_object import MethodObject
from ropetest import testutils
from ropetest.refactor import change_signature_test, similarfindertest


class MethodObjectTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, "mod")

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def test_empty_method(self):
        code = dedent("""\
            def func():
                pass
        """)
        self.mod.write(code)
        replacer = MethodObject(self.project, self.mod, code.index("func"))
        expected = dedent("""\
            class _New(object):

                def __call__(self):
                    pass
        """)
        self.assertEqual(
            expected,
            replacer.get_new_class("_New"),
        )

    def test_trivial_return(self):
        code = dedent("""\
            def func():
                return 1
        """)
        self.mod.write(code)
        replacer = MethodObject(self.project, self.mod, code.index("func"))
        expected = dedent("""\
            class _New(object):

                def __call__(self):
                    return 1
        """)
        self.assertEqual(
            expected,
            replacer.get_new_class("_New"),
        )

    def test_multi_line_header(self):
        code = dedent("""\
            def func(
                ):
                return 1
        """)
        self.mod.write(code)
        replacer = MethodObject(self.project, self.mod, code.index("func"))
        expected = dedent("""\
            class _New(object):

                def __call__(self):
                    return 1
        """)
        self.assertEqual(
            expected,
            replacer.get_new_class("_New"),
        )

    def test_a_single_parameter(self):
        code = dedent("""\
            def func(param):
                return 1
        """)
        self.mod.write(code)
        replacer = MethodObject(self.project, self.mod, code.index("func"))
        expected = dedent("""\
            class _New(object):

                def __init__(self, param):
                    self.param = param

                def __call__(self):
                    return 1
        """)
        self.assertEqual(
            expected,
            replacer.get_new_class("_New"),
        )

    def test_self_parameter(self):
        code = dedent("""\
            def func(self):
                return 1
        """)
        self.mod.write(code)
        replacer = MethodObject(self.project, self.mod, code.index("func"))
        expected = dedent("""\
            class _New(object):

                def __init__(self, host):
                    self.self = host

                def __call__(self):
                    return 1
        """)
        self.assertEqual(
            expected,
            replacer.get_new_class("_New"),
        )

    def test_simple_using_passed_parameters(self):
        code = dedent("""\
            def func(param):
                return param
        """)
        self.mod.write(code)
        replacer = MethodObject(self.project, self.mod, code.index("func"))
        expected = dedent("""\
            class _New(object):

                def __init__(self, param):
                    self.param = param

                def __call__(self):
                    return self.param
        """)
        self.assertEqual(
            expected,
            replacer.get_new_class("_New"),
        )

    def test_self_keywords_and_args_parameters(self):
        code = dedent("""\
            def func(arg, *args, **kwds):
                result = arg + args[0] + kwds[arg]
                return result
        """)
        self.mod.write(code)
        replacer = MethodObject(self.project, self.mod, code.index("func"))
        expected = dedent("""\
            class _New(object):

                def __init__(self, arg, args, kwds):
                    self.arg = arg
                    self.args = args
                    self.kwds = kwds

                def __call__(self):
                    result = self.arg + self.args[0] + self.kwds[self.arg]
                    return result
        """)
        self.assertEqual(expected, replacer.get_new_class("_New"))

    def test_performing_on_not_a_function(self):
        code = dedent("""\
            my_var = 10
        """)
        self.mod.write(code)
        with self.assertRaises(RefactoringError):
            MethodObject(self.project, self.mod, code.index("my_var"))

    def test_changing_the_module(self):
        code = dedent("""\
            def func():
                return 1
        """)
        self.mod.write(code)
        replacer = MethodObject(self.project, self.mod, code.index("func"))
        self.project.do(replacer.get_changes("_New"))
        expected = dedent("""\
            def func():
                return _New()()


            class _New(object):

                def __call__(self):
                    return 1
        """)
        self.assertEqual(expected, self.mod.read())

    def test_changing_the_module_and_class_methods(self):
        code = dedent("""\
            class C(object):

                def a_func(self):
                    return 1

                def another_func(self):
                    pass
        """)
        self.mod.write(code)
        replacer = MethodObject(self.project, self.mod, code.index("func"))
        self.project.do(replacer.get_changes("_New"))
        expected = dedent("""\
            class C(object):

                def a_func(self):
                    return _New(self)()

                def another_func(self):
                    pass


            class _New(object):

                def __init__(self, host):
                    self.self = host

                def __call__(self):
                    return 1
        """)
        self.assertEqual(expected, self.mod.read())


class IntroduceFactoryTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def _introduce_factory(self, resource, offset, *args, **kwds):
        factory_introducer = IntroduceFactory(self.project, resource, offset)
        changes = factory_introducer.get_changes(*args, **kwds)
        self.project.do(changes)

    def test_adding_the_method(self):
        code = dedent("""\
            class AClass(object):
                an_attr = 10
        """)
        mod = testutils.create_module(self.project, "mod")
        mod.write(code)
        expected = dedent("""\
            class AClass(object):
                an_attr = 10

                @staticmethod
                def create(*args, **kwds):
                    return AClass(*args, **kwds)
        """)
        self._introduce_factory(mod, mod.read().index("AClass") + 1, "create")
        self.assertEqual(expected, mod.read())

    def test_changing_occurrences_in_the_main_module(self):
        code = dedent("""\
            class AClass(object):
                an_attr = 10
            a_var = AClass()""")
        mod = testutils.create_module(self.project, "mod")
        mod.write(code)
        expected = dedent("""\
            class AClass(object):
                an_attr = 10

                @staticmethod
                def create(*args, **kwds):
                    return AClass(*args, **kwds)
            a_var = AClass.create()""")
        self._introduce_factory(mod, mod.read().index("AClass") + 1, "create")
        self.assertEqual(expected, mod.read())

    def test_changing_occurrences_with_arguments(self):
        code = dedent("""\
            class AClass(object):
                def __init__(self, arg):
                    pass
            a_var = AClass(10)
        """)
        mod = testutils.create_module(self.project, "mod")
        mod.write(code)
        expected = dedent("""\
            class AClass(object):
                def __init__(self, arg):
                    pass

                @staticmethod
                def create(*args, **kwds):
                    return AClass(*args, **kwds)
            a_var = AClass.create(10)
        """)
        self._introduce_factory(mod, mod.read().index("AClass") + 1, "create")
        self.assertEqual(expected, mod.read())

    def test_changing_occurrences_in_other_modules(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write("class AClass(object):\n    an_attr = 10\n")
        mod2.write("import mod1\na_var = mod1.AClass()\n")
        self._introduce_factory(mod1, mod1.read().index("AClass") + 1, "create")
        expected1 = dedent("""\
            class AClass(object):
                an_attr = 10

                @staticmethod
                def create(*args, **kwds):
                    return AClass(*args, **kwds)
        """)
        expected2 = dedent("""\
            import mod1
            a_var = mod1.AClass.create()
        """)
        self.assertEqual(expected1, mod1.read())
        self.assertEqual(expected2, mod2.read())

    def test_raising_exception_for_non_classes(self):
        mod = testutils.create_module(self.project, "mod")
        mod.write("def a_func():\n    pass\n")
        with self.assertRaises(RefactoringError):
            self._introduce_factory(mod, mod.read().index("a_func") + 1, "create")

    def test_undoing_introduce_factory(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        code1 = dedent("""\
            class AClass(object):
                an_attr = 10
        """)
        mod1.write(code1)
        code2 = dedent("""\
            from mod1 import AClass
            a_var = AClass()
        """)
        mod2.write(code2)
        self._introduce_factory(mod1, mod1.read().index("AClass") + 1, "create")
        self.project.history.undo()
        self.assertEqual(code1, mod1.read())
        self.assertEqual(code2, mod2.read())

    def test_using_on_an_occurrence_outside_the_main_module(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write("class AClass(object):\n    an_attr = 10\n")
        mod2.write("import mod1\na_var = mod1.AClass()\n")
        self._introduce_factory(mod2, mod2.read().index("AClass") + 1, "create")
        expected1 = dedent("""\
            class AClass(object):
                an_attr = 10

                @staticmethod
                def create(*args, **kwds):
                    return AClass(*args, **kwds)
        """)
        expected2 = "import mod1\n" "a_var = mod1.AClass.create()\n"
        self.assertEqual(expected1, mod1.read())
        self.assertEqual(expected2, mod2.read())

    def test_introduce_factory_in_nested_scopes(self):
        code = dedent("""\
            def create_var():
                class AClass(object):
                    an_attr = 10
                return AClass()
        """)
        mod = testutils.create_module(self.project, "mod")
        mod.write(code)
        expected = dedent("""\
            def create_var():
                class AClass(object):
                    an_attr = 10

                    @staticmethod
                    def create(*args, **kwds):
                        return AClass(*args, **kwds)
                return AClass.create()
        """)
        self._introduce_factory(mod, mod.read().index("AClass") + 1, "create")
        self.assertEqual(expected, mod.read())

    def test_adding_factory_for_global_factories(self):
        code = dedent("""\
            class AClass(object):
                an_attr = 10
        """)
        mod = testutils.create_module(self.project, "mod")
        mod.write(code)
        expected = dedent("""\
            class AClass(object):
                an_attr = 10

            def create(*args, **kwds):
                return AClass(*args, **kwds)
        """)
        self._introduce_factory(
            mod, mod.read().index("AClass") + 1, "create", global_factory=True
        )
        self.assertEqual(expected, mod.read())

    def test_get_name_for_factories(self):
        code = dedent("""\
            class C(object):
                pass
        """)
        mod = testutils.create_module(self.project, "mod")
        mod.write(code)
        factory = IntroduceFactory(self.project, mod, mod.read().index("C") + 1)
        self.assertEqual("C", factory.get_name())

    def test_raising_exception_for_global_factory_for_nested_classes(self):
        code = dedent("""\
            def create_var():
                class AClass(object):
                    an_attr = 10
                return AClass()
        """)
        mod = testutils.create_module(self.project, "mod")
        mod.write(code)
        with self.assertRaises(RefactoringError):
            self._introduce_factory(
                mod, mod.read().index("AClass") + 1, "create", global_factory=True
            )

    def test_changing_occurrences_in_the_main_module_for_global_factories(self):
        code = dedent("""\
            class AClass(object):
                an_attr = 10
            a_var = AClass()""")
        mod = testutils.create_module(self.project, "mod")
        mod.write(code)
        expected = dedent("""\
            class AClass(object):
                an_attr = 10

            def create(*args, **kwds):
                return AClass(*args, **kwds)
            a_var = create()""")
        self._introduce_factory(
            mod, mod.read().index("AClass") + 1, "create", global_factory=True
        )
        self.assertEqual(expected, mod.read())

    def test_changing_occurrences_in_other_modules_for_global_factories(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write("class AClass(object):\n    an_attr = 10\n")
        mod2.write("import mod1\na_var = mod1.AClass()\n")
        self._introduce_factory(
            mod1, mod1.read().index("AClass") + 1, "create", global_factory=True
        )
        expected1 = dedent("""\
            class AClass(object):
                an_attr = 10

            def create(*args, **kwds):
                return AClass(*args, **kwds)
        """)
        expected2 = "import mod1\n" "a_var = mod1.create()\n"
        self.assertEqual(expected1, mod1.read())
        self.assertEqual(expected2, mod2.read())

    def test_import_if_necessary_in_other_mods_for_global_factories(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write("class AClass(object):\n    an_attr = 10\n")
        mod2.write("from mod1 import AClass\npair = AClass(), AClass\n")
        self._introduce_factory(
            mod1, mod1.read().index("AClass") + 1, "create", global_factory=True
        )
        expected1 = dedent("""\
            class AClass(object):
                an_attr = 10

            def create(*args, **kwds):
                return AClass(*args, **kwds)
        """)
        expected2 = dedent("""\
            from mod1 import AClass, create
            pair = create(), AClass
        """)
        self.assertEqual(expected1, mod1.read())
        self.assertEqual(expected2, mod2.read())

    def test_changing_occurrences_for_renamed_classes(self):
        code = dedent("""\
            class AClass(object):
                an_attr = 10
            a_class = AClass
            a_var = a_class()""")
        mod = testutils.create_module(self.project, "mod")
        mod.write(code)
        expected = dedent("""\
            class AClass(object):
                an_attr = 10

                @staticmethod
                def create(*args, **kwds):
                    return AClass(*args, **kwds)
            a_class = AClass
            a_var = a_class()""")
        self._introduce_factory(mod, mod.read().index("a_class") + 1, "create")
        self.assertEqual(expected, mod.read())

    def test_changing_occurs_in_the_same_module_with_conflict_ranges(self):
        mod = testutils.create_module(self.project, "mod")
        code = dedent("""\
            class C(object):
                def create(self):
                    return C()
        """)
        mod.write(code)
        self._introduce_factory(mod, mod.read().index("C"), "create_c", True)
        expected = dedent("""\
            class C(object):
                def create(self):
                    return create_c()
        """)
        self.assertTrue(mod.read().startswith(expected))

    def _transform_module_to_package(self, resource):
        self.project.do(
            rope.refactor.ModuleToPackage(self.project, resource).get_changes()
        )

    def test_transform_module_to_package(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod1.write("import mod2\nfrom mod2 import AClass\n")
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write("class AClass(object):\n    pass\n")
        self._transform_module_to_package(mod2)
        mod2 = self.project.get_resource("mod2")
        root_folder = self.project.root
        self.assertFalse(root_folder.has_child("mod2.py"))
        self.assertEqual(
            "class AClass(object):\n    pass\n",
            root_folder.get_child("mod2").get_child("__init__.py").read(),
        )

    def test_transform_module_to_package_undoing(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod = testutils.create_module(self.project, "mod", pkg)
        self._transform_module_to_package(mod)
        self.assertFalse(pkg.has_child("mod.py"))
        self.assertTrue(pkg.get_child("mod").has_child("__init__.py"))
        self.project.history.undo()
        self.assertTrue(pkg.has_child("mod.py"))
        self.assertFalse(pkg.has_child("mod"))

    def test_transform_module_to_package_with_relative_imports(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod1 = testutils.create_module(self.project, "mod1", pkg)
        mod1.write("import mod2\nfrom mod2 import AClass\n")
        mod2 = testutils.create_module(self.project, "mod2", pkg)
        mod2.write("class AClass(object):\n    pass\n")
        self._transform_module_to_package(mod1)
        new_init = self.project.get_resource("pkg/mod1/__init__.py")
        self.assertEqual(
            "import pkg.mod2\nfrom pkg.mod2 import AClass\n", new_init.read()
        )

    def test_resources_parameter(self):
        code = dedent("""\
            class A(object):
                an_attr = 10
        """)
        code1 = dedent("""\
            import mod
            a = mod.A()
        """)
        mod = testutils.create_module(self.project, "mod")
        mod1 = testutils.create_module(self.project, "mod1")
        mod.write(code)
        mod1.write(code1)
        expected = dedent("""\
            class A(object):
                an_attr = 10

                @staticmethod
                def create(*args, **kwds):
                    return A(*args, **kwds)
        """)
        self._introduce_factory(
            mod, mod.read().index("A") + 1, "create", resources=[mod]
        )
        self.assertEqual(expected, mod.read())
        self.assertEqual(code1, mod1.read())


class EncapsulateFieldTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, "mod")
        self.mod1 = testutils.create_module(self.project, "mod1")
        self.a_class = dedent("""\
            class A(object):
                def __init__(self):
                    self.attr = 1
        """)
        self.added_methods = (
            "\n"
            "    def get_attr(self):\n"
            "        return self.attr\n\n"
            "    def set_attr(self, value):\n"
            "        self.attr = value\n"
        )
        self.encapsulated = self.a_class + self.added_methods

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def _encapsulate(self, resource, offset, **args):
        changes = EncapsulateField(self.project, resource, offset).get_changes(**args)
        self.project.do(changes)

    def test_adding_getters_and_setters(self):
        code = self.a_class
        self.mod.write(code)
        self._encapsulate(self.mod, code.index("attr") + 1)
        self.assertEqual(self.encapsulated, self.mod.read())

    def test_changing_getters_in_other_modules(self):
        code = dedent("""\
            import mod
            a_var = mod.A()
            range(a_var.attr)
        """)
        self.mod1.write(code)
        self.mod.write(self.a_class)
        self._encapsulate(self.mod, self.mod.read().index("attr") + 1)
        expected = dedent("""\
            import mod
            a_var = mod.A()
            range(a_var.get_attr())
        """)
        self.assertEqual(expected, self.mod1.read())

    def test_changing_setters_in_other_modules(self):
        code = dedent("""\
            import mod
            a_var = mod.A()
            a_var.attr = 1
        """)
        self.mod1.write(code)
        self.mod.write(self.a_class)
        self._encapsulate(self.mod, self.mod.read().index("attr") + 1)
        expected = dedent("""\
            import mod
            a_var = mod.A()
            a_var.set_attr(1)
        """)
        self.assertEqual(expected, self.mod1.read())

    def test_changing_getters_in_setters(self):
        code = dedent("""\
            import mod
            a_var = mod.A()
            a_var.attr = 1 + a_var.attr
        """)
        self.mod1.write(code)
        self.mod.write(self.a_class)
        self._encapsulate(self.mod, self.mod.read().index("attr") + 1)
        expected = dedent("""\
            import mod
            a_var = mod.A()
            a_var.set_attr(1 + a_var.get_attr())
        """)
        self.assertEqual(expected, self.mod1.read())

    def test_appending_to_class_end(self):
        self.mod1.write(self.a_class + "a_var = A()\n")
        self._encapsulate(self.mod1, self.mod1.read().index("attr") + 1)
        self.assertEqual(self.encapsulated + "a_var = A()\n", self.mod1.read())

    def test_performing_in_other_modules(self):
        code = dedent("""\
            import mod
            a_var = mod.A()
            range(a_var.attr)
        """)
        self.mod1.write(code)
        self.mod.write(self.a_class)
        self._encapsulate(self.mod1, self.mod1.read().index("attr") + 1)
        self.assertEqual(self.encapsulated, self.mod.read())
        expected = dedent("""\
            import mod
            a_var = mod.A()
            range(a_var.get_attr())
        """)
        self.assertEqual(expected, self.mod1.read())

    def test_changing_main_module_occurrences(self):
        code = self.a_class + "a_var = A()\n" "a_var.attr = a_var.attr * 2\n"
        self.mod1.write(code)
        self._encapsulate(self.mod1, self.mod1.read().index("attr") + 1)
        expected = (
            self.encapsulated + "a_var = A()\n" "a_var.set_attr(a_var.get_attr() * 2)\n"
        )
        self.assertEqual(expected, self.mod1.read())

    def test_raising_exception_when_performed_on_non_attributes(self):
        self.mod1.write("attr = 10")
        with self.assertRaises(RefactoringError):
            self._encapsulate(self.mod1, self.mod1.read().index("attr") + 1)

    def test_raising_exception_on_tuple_assignments(self):
        self.mod.write(self.a_class)
        code = dedent("""\
            import mod
            a_var = mod.A()
            a_var.attr = 1
            a_var.attr, b = 1, 2
        """)
        self.mod1.write(code)
        with self.assertRaises(RefactoringError):
            self._encapsulate(self.mod1, self.mod1.read().index("attr") + 1)

    def test_raising_exception_on_tuple_assignments2(self):
        self.mod.write(self.a_class)
        code = dedent("""\
            import mod
            a_var = mod.A()
            a_var.attr = 1
            b, a_var.attr = 1, 2
        """)
        self.mod1.write(code)
        with self.assertRaises(RefactoringError):
            self._encapsulate(self.mod1, self.mod1.read().index("attr") + 1)

    def test_tuple_assignments_and_function_calls(self):
        code = dedent("""\
            import mod
            def func(a1=0, a2=0):
                pass
            a_var = mod.A()
            func(a_var.attr, a2=2)
        """)
        self.mod1.write(code)
        self.mod.write(self.a_class)
        self._encapsulate(self.mod, self.mod.read().index("attr") + 1)
        expected = dedent("""\
            import mod
            def func(a1=0, a2=0):
                pass
            a_var = mod.A()
            func(a_var.get_attr(), a2=2)
        """)
        self.assertEqual(expected, self.mod1.read())

    def test_tuple_assignments(self):
        code = dedent("""\
            import mod
            a_var = mod.A()
            a, b = a_var.attr, 1
        """)
        self.mod1.write(code)
        self.mod.write(self.a_class)
        self._encapsulate(self.mod, self.mod.read().index("attr") + 1)
        expected = dedent("""\
            import mod
            a_var = mod.A()
            a, b = a_var.get_attr(), 1
        """)
        self.assertEqual(expected, self.mod1.read())

    def test_changing_augmented_assignments(self):
        code = "import mod\n" "a_var = mod.A()\n" "a_var.attr += 1\n"
        self.mod1.write(code)
        self.mod.write(self.a_class)
        self._encapsulate(self.mod, self.mod.read().index("attr") + 1)
        expected = dedent("""\
            import mod
            a_var = mod.A()
            a_var.set_attr(a_var.get_attr() + 1)
        """)
        self.assertEqual(expected, self.mod1.read())

    def test_changing_augmented_assignments2(self):
        code = dedent("""\
            import mod
            a_var = mod.A()
            a_var.attr <<= 1
        """)
        self.mod1.write(code)
        self.mod.write(self.a_class)
        self._encapsulate(self.mod, self.mod.read().index("attr") + 1)
        expected = dedent("""\
            import mod
            a_var = mod.A()
            a_var.set_attr(a_var.get_attr() << 1)
        """)
        self.assertEqual(expected, self.mod1.read())

    def test_changing_occurrences_inside_the_class(self):
        new_class = (
            self.a_class + "\n" "    def a_func(self):\n" "        self.attr = 1\n"
        )
        self.mod.write(new_class)
        self._encapsulate(self.mod, self.mod.read().index("attr") + 1)
        expected = (
            self.a_class + "\n"
            "    def a_func(self):\n"
            "        self.set_attr(1)\n" + self.added_methods
        )
        self.assertEqual(expected, self.mod.read())

    def test_getter_and_setter_parameters(self):
        self.mod.write(self.a_class)
        self._encapsulate(
            self.mod,
            self.mod.read().index("attr") + 1,
            getter="getAttr",
            setter="setAttr",
        )
        new_methods = self.added_methods.replace("get_attr", "getAttr").replace(
            "set_attr", "setAttr"
        )
        expected = self.a_class + new_methods
        self.assertEqual(expected, self.mod.read())

    def test_using_resources_parameter(self):
        self.mod1.write("import mod\na = mod.A()\nvar = a.attr\n")
        self.mod.write(self.a_class)
        self._encapsulate(
            self.mod, self.mod.read().index("attr") + 1, resources=[self.mod]
        )
        self.assertEqual("import mod\na = mod.A()\nvar = a.attr\n", self.mod1.read())
        expected = self.a_class + self.added_methods
        self.assertEqual(expected, self.mod.read())


class LocalToFieldTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, "mod")

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def _perform_convert_local_variable_to_field(self, resource, offset):
        changes = LocalToField(self.project, resource, offset).get_changes()
        self.project.do(changes)

    def test_simple_local_to_field(self):
        code = dedent("""\
            class A(object):
                def a_func(self):
                    var = 10
        """)
        self.mod.write(code)
        self._perform_convert_local_variable_to_field(self.mod, code.index("var") + 1)
        expected = dedent("""\
            class A(object):
                def a_func(self):
                    self.var = 10
        """)
        self.assertEqual(expected, self.mod.read())

    def test_raising_exception_when_performed_on_a_global_var(self):
        self.mod.write("var = 10\n")
        with self.assertRaises(RefactoringError):
            self._perform_convert_local_variable_to_field(
                self.mod, self.mod.read().index("var") + 1
            )

    def test_raising_exception_when_performed_on_field(self):
        code = dedent("""\
            class A(object):
                def a_func(self):
                    self.var = 10
        """)
        self.mod.write(code)
        with self.assertRaises(RefactoringError):
            self._perform_convert_local_variable_to_field(
                self.mod, self.mod.read().index("var") + 1
            )

    def test_raising_exception_when_performed_on_a_parameter(self):
        code = dedent("""\
            class A(object):
                def a_func(self, var):
                    a = var
        """)
        self.mod.write(code)
        with self.assertRaises(RefactoringError):
            self._perform_convert_local_variable_to_field(
                self.mod, self.mod.read().index("var") + 1
            )

    # NOTE: This situation happens a lot and is normally not an error
    # @testutils.assert_raises(RefactoringError)
    def test_not_raise_exception_when_there_is_a_field_with_the_same_name(self):
        code = dedent("""\
            class A(object):
                def __init__(self):
                    self.var = 1
                def a_func(self):
                    var = 10
        """)
        self.mod.write(code)
        self._perform_convert_local_variable_to_field(
            self.mod, self.mod.read().rindex("var") + 1
        )

    def test_local_to_field_with_self_renamed(self):
        code = dedent("""\
            class A(object):
                def a_func(myself):
                    var = 10
        """)
        self.mod.write(code)
        self._perform_convert_local_variable_to_field(self.mod, code.index("var") + 1)
        expected = dedent("""\
            class A(object):
                def a_func(myself):
                    myself.var = 10
        """)
        self.assertEqual(expected, self.mod.read())


class IntroduceParameterTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, "mod")

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def _introduce_parameter(self, offset, name):
        rope.refactor.introduce_parameter.IntroduceParameter(
            self.project, self.mod, offset
        ).get_changes(name).do()

    def test_simple_case(self):
        code = dedent("""\
            var = 1
            def f():
                b = var
        """)
        self.mod.write(code)
        offset = self.mod.read().rindex("var")
        self._introduce_parameter(offset, "var")
        expected = dedent("""\
            var = 1
            def f(var=var):
                b = var
        """)
        self.assertEqual(expected, self.mod.read())

    def test_changing_function_body(self):
        code = dedent("""\
            var = 1
            def f():
                b = var
        """)
        self.mod.write(code)
        offset = self.mod.read().rindex("var")
        self._introduce_parameter(offset, "p1")
        expected = dedent("""\
            var = 1
            def f(p1=var):
                b = p1
        """)
        self.assertEqual(expected, self.mod.read())

    def test_unknown_variables(self):
        self.mod.write("def f():\n    b = var + c\n")
        offset = self.mod.read().rindex("var")
        with self.assertRaises(RefactoringError):
            self._introduce_parameter(offset, "p1")
            self.assertEqual("def f(p1=var):\n    b = p1 + c\n", self.mod.read())

    def test_failing_when_not_inside(self):
        self.mod.write("var = 10\nb = var\n")
        offset = self.mod.read().rindex("var")
        with self.assertRaises(RefactoringError):
            self._introduce_parameter(offset, "p1")

    def test_attribute_accesses(self):
        code = dedent("""\
            class C(object):
                a = 10
            c = C()
            def f():
                b = c.a
        """)
        self.mod.write(code)
        offset = self.mod.read().rindex("a")
        self._introduce_parameter(offset, "p1")
        expected = dedent("""\
            class C(object):
                a = 10
            c = C()
            def f(p1=c.a):
                b = p1
        """)
        self.assertEqual(expected, self.mod.read())

    def test_introducing_parameters_for_methods(self):
        code = dedent("""\
            var = 1
            class C(object):
                def f(self):
                    b = var
        """)
        self.mod.write(code)
        offset = self.mod.read().rindex("var")
        self._introduce_parameter(offset, "p1")
        expected = dedent("""\
            var = 1
            class C(object):
                def f(self, p1=var):
                    b = p1
        """)
        self.assertEqual(expected, self.mod.read())


class _MockTaskObserver:
    def __init__(self):
        self.called = 0

    def __call__(self):
        self.called += 1


class TaskHandleTest(unittest.TestCase):
    def test_trivial_case(self):
        handle = rope.base.taskhandle.TaskHandle()
        self.assertFalse(handle.is_stopped())

    def test_stopping(self):
        handle = rope.base.taskhandle.TaskHandle()
        handle.stop()
        self.assertTrue(handle.is_stopped())

    def test_job_sets(self):
        handle = rope.base.taskhandle.TaskHandle()
        jobs = handle.create_jobset()
        self.assertEqual([jobs], handle.get_jobsets())

    def test_starting_and_finishing_jobs(self):
        handle = rope.base.taskhandle.TaskHandle()
        jobs = handle.create_jobset(name="test job set", count=1)
        jobs.started_job("job1")
        jobs.finished_job()

    def test_test_checking_status(self):
        handle = rope.base.taskhandle.TaskHandle()
        jobs = handle.create_jobset()
        handle.stop()
        with self.assertRaises(InterruptedTaskError):
            jobs.check_status()

    def test_test_checking_status_when_starting(self):
        handle = rope.base.taskhandle.TaskHandle()
        jobs = handle.create_jobset()
        handle.stop()
        with self.assertRaises(InterruptedTaskError):
            jobs.started_job("job1")

    def test_calling_the_observer_after_stopping(self):
        handle = rope.base.taskhandle.TaskHandle()
        observer = _MockTaskObserver()
        handle.add_observer(observer)
        handle.stop()
        self.assertEqual(1, observer.called)

    def test_calling_the_observer_after_creating_job_sets(self):
        handle = rope.base.taskhandle.TaskHandle()
        observer = _MockTaskObserver()
        handle.add_observer(observer)
        jobs = handle.create_jobset()  # noqa
        self.assertEqual(1, observer.called)

    def test_calling_the_observer_when_starting_and_finishing_jobs(self):
        handle = rope.base.taskhandle.TaskHandle()
        observer = _MockTaskObserver()
        handle.add_observer(observer)
        jobs = handle.create_jobset(name="test job set", count=1)
        jobs.started_job("job1")
        jobs.finished_job()
        self.assertEqual(3, observer.called)

    def test_job_set_get_percent_done(self):
        handle = rope.base.taskhandle.TaskHandle()
        jobs = handle.create_jobset(name="test job set", count=2)
        self.assertEqual(0, jobs.get_percent_done())
        jobs.started_job("job1")
        jobs.finished_job()
        self.assertEqual(50, jobs.get_percent_done())
        jobs.started_job("job2")
        jobs.finished_job()
        self.assertEqual(100, jobs.get_percent_done())

    def test_getting_job_name(self):
        handle = rope.base.taskhandle.TaskHandle()
        jobs = handle.create_jobset(name="test job set", count=1)
        # recommended name/job_name attribute
        self.assertEqual("test job set", jobs.name)
        self.assertEqual(None, jobs.job_name)
        # deprecated getters
        self.assertEqual("test job set", jobs.get_name())
        self.assertEqual(None, jobs.get_active_job_name())
        jobs.started_job("job1")
        # recommended name/job_name attribute
        self.assertEqual("test job set", jobs.get_name())
        # deprecated getters
        self.assertEqual("job1", jobs.get_active_job_name())
