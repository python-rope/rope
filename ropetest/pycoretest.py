import collections.abc
import os
import sys
import tempfile
import typing
import unittest
from textwrap import dedent

from rope.base import evaluate, exceptions, libutils, pynames
from rope.base.builtins import BuiltinClass, File, builtins
from rope.base.project import Project
from rope.base.pycore import _TextChangeDetector
from rope.base.pynamesdef import AssignedName
from rope.base.pyobjects import (
    AbstractFunction,
    UnresolvedBase,
    get_base_type,
    get_unknown,
)
from ropetest import testutils


class PyCoreTest(unittest.TestCase):
    def test_stdlib_runtime_module_election_preserves_declaring_source(self):
        runtime = collections.abc
        self.assertIs(runtime, sys.modules[runtime.__spec__.name])
        result = self.project.get_module('collections.abc')
        # Same file, whatever spelling the runtime used (Windows: lib vs Lib).
        self.assertTrue(os.path.samefile(runtime.__file__, result.get_resource().real_path))
        self.assertIn('Sequence', result)

    def test_stdlib_module_election_does_not_cross_project_parent_shadow(self):
        package = testutils.create_package(self.project, 'collections')
        package.get_child('__init__.py').write("raise AssertionError('target code must not execute')\n")
        with self.assertRaises(exceptions.ModuleNotFoundError):
            self.project.get_module('collections.abc')

    def test_stdlib_module_election_does_not_cross_origin_shadow(self):
        import collections.abc

        import _collections_abc

        resource = testutils.create_module(self.project, '_collections_abc')
        resource.write("raise AssertionError('target code must not execute')\n")
        if collections.abc is _collections_abc:
            # Python 3.13+ aliases collections.abc to _collections_abc, so a
            # project module of that name would cross the stdlib origin.
            with self.assertRaises(exceptions.ModuleNotFoundError):
                self.project.get_module('collections.abc')
        else:
            # Earlier versions ship collections/abc.py as its own module.
            module = self.project.get_module('collections.abc')
            self.assertNotEqual(resource, module.get_resource())

    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

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
        mod.write(dedent("""\
            class SampleClass(object):
                pass
        """))
        mod_element = self.project.get_module("mod")
        result = mod_element["SampleClass"].get_object()
        self.assertEqual(get_base_type("Type"), result.get_type())

    def test_simple_function(self):
        mod = testutils.create_module(self.project, "mod")
        mod.write(dedent("""\
            def sample_function():
                pass
        """))
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
        mod.write(dedent("""\
            class SampleClass(object):
                var = 10
        """))
        mod_element = self.project.get_module("mod")
        sample_class = mod_element["SampleClass"].get_object()
        var = sample_class["var"]  # noqa

    def test_class_attributes_set_in_init(self):
        mod = testutils.create_module(self.project, "mod")
        mod.write(dedent("""\
            class C(object):
                def __init__(self):
                    self.var = 20
        """))
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
        mod = libutils.get_string_module(self.project, code)  # noqa

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

    def _assert_mro_matches_python(self, code, names):
        namespace = {}
        exec(code, namespace)
        mod = libutils.get_string_module(self.project, code)
        for name in names:
            with self.subTest(name=name):
                expected = [cls.__name__ for cls in namespace[name].__mro__]
                actual = [cls.get_name() for cls in mod[name].get_object().get_mro()]
                self.assertEqual(expected, actual)

    def test_bases_through_annotated_type_aliases_resolve_the_class(self):
        code = dedent("""\
            import typing
            from typing import TypeAlias as Declared
            class Parts:
                class Root[T]:
                    pass
            class Facade(Parts):
                Root: Declared = Parts.Root
            Alias: typing.TypeAlias = Parts.Root
            class ViaFacade(Facade.Root[int]):
                pass
            class ViaModule(Alias[int]):
                pass
            class Plain(Alias):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        root = mod["Parts"].get_object()["Root"].get_object()
        for name in ("ViaFacade", "ViaModule", "Plain"):
            with self.subTest(name=name):
                self.assertEqual([root], mod[name].get_object().get_superclasses())

    def test_type_checking_branch_is_taken_by_static_inference(self):
        # PEP 484: static analysis assumes typing.TYPE_CHECKING is true.
        guards = (
            ("from typing import TYPE_CHECKING", "TYPE_CHECKING"),
            ("from typing import TYPE_CHECKING as TC", "TC"),
            ("import typing", "typing.TYPE_CHECKING"),
            ("import typing as t", "t.TYPE_CHECKING"),
        )
        for guard_import, guard in guards:
            with self.subTest(guard=guard):
                code = dedent(f"""\
                    {guard_import}
                    from typing import TypeAlias
                    class Parts:
                        class Root[T]:
                            pass
                    class Facade(Parts):
                        if {guard}:
                            Root: TypeAlias = Parts.Root
                            Plain = Parts.Root
                    if {guard}:
                        Alias: TypeAlias = Parts.Root
                    else:
                        Alias = None
                    class ViaFacade(Facade.Root):
                        pass
                    class ViaGeneric(Facade.Root[int]):
                        pass
                    class ViaModule(Alias):
                        pass
                """)
                mod = libutils.get_string_module(self.project, code)
                root = mod["Parts"].get_object()["Root"].get_object()
                facade = mod["Facade"].get_object()
                self.assertIs(root, facade["Root"].get_object())
                self.assertIs(root, facade["Plain"].get_object())
                self.assertIs(root, mod["Alias"].get_object())
                for name in ("ViaFacade", "ViaGeneric", "ViaModule"):
                    derived = mod[name].get_object()
                    self.assertEqual([root], derived.get_superclasses())
                    self.assertEqual([derived, *root.get_mro()], derived.get_mro())

    def test_name_spelled_type_checking_outside_typing_keeps_both_arms(self):
        code = dedent("""\
            TYPE_CHECKING = False
            class Root:
                pass
            if TYPE_CHECKING:
                Alias = Root
        """)
        mod = libutils.get_string_module(self.project, code)
        self.assertIs(get_unknown(), mod["Alias"].get_object())

    def test_type_checking_body_wins_over_the_else_arm(self):
        code = dedent("""\
            from typing import TYPE_CHECKING
            class Checked:
                pass
            class Runtime:
                pass
            if TYPE_CHECKING:
                Alias = Checked
            else:
                Alias = Runtime
        """)
        mod = libutils.get_string_module(self.project, code)
        self.assertIs(mod["Checked"].get_object(), mod["Alias"].get_object())

    def test_branch_test_reading_the_inferred_name_keeps_agreeing_arms(self):
        code = dedent("""\
            class A:
                flag = True
            a = A
            if a.flag:
                a = A
        """)
        mod = libutils.get_string_module(self.project, code)
        self.assertIs(mod["A"].get_object(), mod["a"].get_object())

    def test_project_typing_module_without_type_checking(self):
        testutils.create_module(self.project, "typing").write("x = 1\n")
        code = dedent("""\
            import os
            from typing import TYPE_CHECKING
            flag = os.environ.get("FLAG")
            class A:
                pass
            if flag:
                X = A
            if TYPE_CHECKING:
                Y = A
        """)
        mod = libutils.get_string_module(self.project, code)
        self.assertIs(get_unknown(), mod["X"].get_object())
        self.assertIs(get_unknown(), mod["Y"].get_object())

    def test_type_checking_rebound_by_typing_extensions_is_taken(self):
        testutils.create_module(self.project, "typing_extensions").write(
            dedent("""\
                import typing
                TYPE_CHECKING = typing.TYPE_CHECKING
            """)
        )
        code = dedent("""\
            from typing_extensions import TYPE_CHECKING
            class Root:
                pass
            if TYPE_CHECKING:
                Alias = Root
        """)
        mod = libutils.get_string_module(self.project, code)
        self.assertIs(mod["Root"].get_object(), mod["Alias"].get_object())

    def test_type_checking_name_bound_more_than_once_stays_undecided(self):
        rebinds = (
            "TC &= False",
            "def rebind():\n    global TC\n    TC = False",
            "del TC",
        )
        for rebind in rebinds:
            with self.subTest(rebind=rebind):
                code = "\n".join((
                    "import typing",
                    "TC = typing.TYPE_CHECKING",
                    rebind,
                    "class Checked:",
                    "    pass",
                    "class Runtime:",
                    "    pass",
                    "if TC:",
                    "    Alias = Checked",
                    "else:",
                    "    Alias = Runtime",
                    "",
                ))
                mod = libutils.get_string_module(self.project, code)
                self.assertIs(get_unknown(), mod["Alias"].get_object())

    def test_type_checking_name_shadowed_in_another_scope_is_taken(self):
        code = dedent("""\
            import typing
            TC = typing.TYPE_CHECKING
            def shadow():
                TC = False
            class Root:
                TC = False
            if TC:
                Alias = Root
        """)
        mod = libutils.get_string_module(self.project, code)
        self.assertIs(mod["Root"].get_object(), mod["Alias"].get_object())

    def test_type_checking_decision_follows_the_module_that_binds_it(self):
        guard = testutils.create_module(self.project, "guard")
        guard.write("import typing\nTYPE_CHECKING = typing.TYPE_CHECKING\n")
        user = testutils.create_module(self.project, "user")
        user.write(
            dedent("""\
                from guard import TYPE_CHECKING
                class Checked:
                    pass
                class Runtime:
                    pass
                if TYPE_CHECKING:
                    Alias = Checked
                else:
                    Alias = Runtime
            """)
        )
        mod = self.project.get_pymodule(user)
        self.assertIs(mod["Checked"].get_object(), mod["Alias"].get_object())
        guard.write("TYPE_CHECKING = False\n")
        mod = self.project.get_pymodule(user)
        self.assertIs(get_unknown(), mod["Alias"].get_object())
        guard.write("import typing\nTYPE_CHECKING = typing.TYPE_CHECKING\n")
        mod = self.project.get_pymodule(user)
        self.assertIs(mod["Checked"].get_object(), mod["Alias"].get_object())

    def test_type_checking_decision_follows_a_project_typing_module(self):
        shadow = testutils.create_module(self.project, "typing")
        shadow.write("x = 1\n")
        user = testutils.create_module(self.project, "user")
        user.write(
            dedent("""\
                from typing import TYPE_CHECKING
                class Checked:
                    pass
                class Runtime:
                    pass
                if TYPE_CHECKING:
                    Alias = Checked
                else:
                    Alias = Runtime
            """)
        )
        mod = self.project.get_pymodule(user)
        self.assertIs(get_unknown(), mod["Alias"].get_object())
        shadow.remove()
        mod = self.project.get_pymodule(user)
        self.assertIs(mod["Checked"].get_object(), mod["Alias"].get_object())

    def test_annotation_named_like_type_alias_still_types_an_instance(self):
        code = dedent("""\
            class TypeAlias:
                pass
            class Root:
                pass
            value: TypeAlias = Root
        """)
        mod = libutils.get_string_module(self.project, code)
        self.assertEqual(
            mod["TypeAlias"].get_object(), mod["value"].get_object().get_type()
        )

    def test_base_type_markers_are_not_class_objects(self):
        for name in ("Type", "Module", "Function", "Unknown"):
            with self.subTest(marker=name):
                marker = get_base_type(name)
                self.assertEqual(get_base_type("Type"), marker.get_type())
                mod = libutils.get_string_module(
                    self.project, "class Derived(marker):\n    pass\n"
                )
                mod.get_scope().get_names()["marker"] = pynames.UnboundName(marker)
                derived = mod["Derived"].get_object()
                (unresolved,) = derived.get_bases()
                self.assertIsInstance(unresolved, UnresolvedBase)
                self.assertIs(marker, unresolved.pyobject)
                self.assertEqual([], derived.get_superclasses())
                self.assertEqual([derived, unresolved], derived.get_mro())

    def test_imported_nonclass_bases_preserve_resolved_ancestors(self):
        provider = testutils.create_module(self.project, "provider")
        provider.write("def function():\n    pass\n")
        for expression in ("provider", "provider.function", "provider.missing"):
            with self.subTest(expression=expression):
                code = dedent(f"""\
                    import provider
                    class Base(object):
                        pass
                    class Derived(Base, {expression}):
                        pass
                """)
                mod = libutils.get_string_module(self.project, code)
                base = mod["Base"].get_object()
                derived = mod["Derived"].get_object()
                resolved, unresolved = derived.get_bases()
                self.assertIs(base, resolved)
                self.assertIsInstance(unresolved, UnresolvedBase)
                self.assertEqual([base], derived.get_superclasses())
                self.assertEqual(
                    [derived, *base.get_mro(), unresolved],
                    derived.get_mro(),
                )

    def test_mro_of_diamond_inheritance(self):
        code = dedent("""\
            class A(object):
                pass
            class B(A):
                pass
            class C(A):
                pass
            class D(B, C):
                pass
        """)
        self._assert_mro_matches_python(code, ["A", "B", "C", "D"])

    def test_mro_matches_python_for_nested_hierarchies(self):
        code = dedent("""\
            class O(object):
                pass
            class A(O):
                pass
            class B(O):
                pass
            class C(O):
                pass
            class D(O):
                pass
            class E(O):
                pass
            class K1(A, B, C):
                pass
            class K2(D, B, E):
                pass
            class K3(D, A):
                pass
            class Z(K1, K2, K3):
                pass
        """)
        self._assert_mro_matches_python(code, ["K1", "K2", "K3", "Z"])

    def test_mro_matches_python_for_builtin_bases(self):
        code = dedent("""\
            class Base(dict):
                pass
            class Mixin(object):
                pass
            class Derived(Mixin, Base):
                pass
            class Flag(Mixin, int):
                pass
            class Failure(Mixin, KeyError):
                pass
        """)
        self._assert_mro_matches_python(code, ["Base", "Derived", "Flag", "Failure"])

    def test_builtin_ancestors_contribute_only_their_own_attributes(self):
        code = dedent("""\
            class Base(object):
                def __init__(self):
                    pass
                def __init_subclass__(cls):
                    pass
            class Mixin(object):
                pass
            class Derived(Mixin, Base):
                pass
            class Mapping(dict, Base):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        base = mod["Base"].get_object()
        derived = mod["Derived"].get_object()
        mapping = mod["Mapping"].get_object()
        self.assertEqual(base["__init__"].get_object(), derived["__init__"].get_object())
        self.assertEqual(
            base["__init_subclass__"].get_object(),
            mapping["__init_subclass__"].get_object(),
        )
        self.assertNotEqual(
            base["__init__"].get_object(), mapping["__init__"].get_object()
        )

    def test_subscripted_class_base_calls_implicit_class_getitem(self):
        code = dedent("""\
            class Base:
                def __class_getitem__(cls, item):
                    return cls
            class Derived(Base[int]):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertEqual((namespace["Base"],), namespace["Derived"].__bases__)
        mod = libutils.get_string_module(self.project, code)
        base = mod["Base"].get_object()
        derived = mod["Derived"].get_object()
        self.assertEqual([derived, base], derived.get_mro())

    def test_type_of_class_uses_its_metaclass_without_changing_kind(self):
        code = dedent("""\
            class Meta(type):
                pass
            class Base(metaclass=Meta):
                pass
            selected = type(Base)
            instance_type = type(Base())
            meta_type = type(Meta)
            created = Meta("Created", (), {})
            created_type = type(created)
            dynamic = type("Dynamic", (), {})
            dynamic_type = type(dynamic)
        """)
        namespace = {}
        exec(code, namespace)
        self.assertIs(namespace["selected"], namespace["Meta"])
        self.assertIs(namespace["instance_type"], namespace["Base"])
        self.assertIs(namespace["meta_type"], type)
        self.assertIs(namespace["created_type"], namespace["Meta"])
        self.assertIs(namespace["dynamic_type"], type)
        mod = libutils.get_string_module(self.project, code)
        base = mod["Base"].get_object()
        meta = mod["Meta"].get_object()
        self.assertIs(mod["selected"].get_object(), meta)
        self.assertIs(mod["instance_type"].get_object(), base)
        self.assertIs(mod["meta_type"].get_object(), builtins["type"].get_object())
        self.assertIs(mod["created_type"].get_object(), meta)
        self.assertIs(mod["dynamic_type"].get_object(), builtins["type"].get_object())
        self.assertIs(base.get_type(), get_base_type("Type"))
        self.assertIs(meta.get_type(), get_base_type("Type"))

    def test_type_of_class_preserves_unresolved_metaclass_witness(self):
        code = dedent("""\
            from builtins import missing
            class Base(missing):
                pass
            selected = type(Base)
        """)
        with self.assertRaises(ImportError):
            exec(code, {})
        mod = libutils.get_string_module(self.project, code)
        base = mod["Base"].get_object()
        (unresolved,) = base.get_bases()
        self.assertIsInstance(unresolved, UnresolvedBase)
        self.assertIs(mod["selected"].get_object(), unresolved)

    def test_type_of_builtin_instances_returns_the_canonical_class(self):
        code = dedent("""\
            number_type = type(1)
            text_type = type("value")
            list_type = type([1])
            dict_type = type({"key": 1})
            tuple_type = type((1, 2))
        """)
        namespace = {}
        exec(code, namespace)
        mod = libutils.get_string_module(self.project, code)
        for name, expected in (
            ("number_type", int),
            ("text_type", str),
            ("list_type", list),
            ("dict_type", dict),
            ("tuple_type", tuple),
        ):
            with self.subTest(name=name):
                self.assertIs(namespace[name], expected)
                self.assertIs(
                    mod[name].get_object(), builtins[expected.__name__].get_object()
                )

    def test_subscripted_class_base_uses_class_getitem_result(self):
        code = dedent("""\
            class Other:
                pass
            class Base:
                def __class_getitem__(cls, item):
                    return Other
            class Derived(Base[int]):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertEqual((namespace["Other"],), namespace["Derived"].__bases__)
        mod = libutils.get_string_module(self.project, code)
        other = mod["Other"].get_object()
        derived = mod["Derived"].get_object()
        self.assertEqual([derived, other], derived.get_mro())

    def test_subscripted_class_base_prefers_metaclass_getitem(self):
        code = dedent("""\
            class Other:
                pass
            class Meta(type):
                def __getitem__(cls, item):
                    return Other
            class Base(metaclass=Meta):
                def __class_getitem__(cls, item):
                    return cls
            class Derived(Base[int]):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertEqual((namespace["Other"],), namespace["Derived"].__bases__)
        mod = libutils.get_string_module(self.project, code)
        other = mod["Other"].get_object()
        derived = mod["Derived"].get_object()
        self.assertEqual([derived, other], derived.get_mro())

    def test_subscripted_class_metaclass_classmethod_receives_metaclass(self):
        code = dedent("""\
            class Meta(type):
                @classmethod
                def __getitem__(cls, item):
                    return cls
            class Base(metaclass=Meta):
                pass
            class Derived(Base[int]):
                pass
        """)
        self._assert_mro_matches_python(code, ["Derived"])

    def test_subscripted_class_retains_unresolved_metaclass_base(self):
        code = dedent("""\
            from builtins import missing
            class Base(missing):
                def __class_getitem__(cls, item):
                    return cls
            selected = Base[int]
        """)
        with self.assertRaises(ImportError):
            exec(code, {})
        mod = libutils.get_string_module(self.project, code)
        base = mod["Base"].get_object()
        (unresolved,) = base.get_bases()
        self.assertIsInstance(unresolved, UnresolvedBase)
        self.assertIs(base.get_metaclass(), unresolved)
        self.assertIs(mod["selected"].get_object(), unresolved)

    def test_subscripted_class_does_not_guess_an_unknown_explicit_metaclass(self):
        code = dedent("""\
            from builtins import missing
            class Base(metaclass=missing):
                def __class_getitem__(cls, item):
                    return cls
            selected = Base[int]
        """)
        with self.assertRaises(ImportError):
            exec(code, {})
        mod = libutils.get_string_module(self.project, code)
        unresolved = mod["Base"].get_object().get_metaclass()
        self.assertIsInstance(unresolved, UnresolvedBase)
        self.assertEqual("missing", unresolved.node.id)
        self.assertIs(mod["selected"].get_object(), unresolved)

    def test_subscripted_class_static_hook_receives_only_the_key(self):
        code = dedent("""\
            class Other:
                pass
            class Base:
                @staticmethod
                def __class_getitem__(item):
                    return item
            class Derived(Base[Other]):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertEqual((namespace["Other"],), namespace["Derived"].__bases__)
        mod = libutils.get_string_module(self.project, code)
        other = mod["Other"].get_object()
        derived = mod["Derived"].get_object()
        self.assertEqual([derived, other], derived.get_mro())

    def test_subscripted_class_static_lambda_receives_only_the_key(self):
        code = dedent("""\
            class Other:
                pass
            class Base:
                __class_getitem__ = staticmethod(lambda item: item)
            class Derived(Base[Other]):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertEqual((namespace["Other"],), namespace["Derived"].__bases__)
        mod = libutils.get_string_module(self.project, code)
        derived = mod["Derived"].get_object()
        self.assertEqual([derived, mod["Other"].get_object()], derived.get_mro())

    def test_subscripted_metaclass_class_lambda_receives_its_metaclass(self):
        code = dedent("""\
            class Meta(type):
                __getitem__ = classmethod(lambda cls, item: cls)
            class Base(metaclass=Meta):
                pass
            class Derived(Base[int]):
                pass
        """)
        self._assert_mro_matches_python(code, ["Derived"])

    def test_subscripted_typing_generic_base_preserves_native_ancestor(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        code = dedent("""\
            from typing import Generic, TypeVar
            T = TypeVar("T")
            class Foo(Generic[T]):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertEqual((namespace["Generic"],), namespace["Foo"].__bases__)
        mod = libutils.get_string_module(self.project, code)
        generic = self.project.get_module("typing")["Generic"].get_object()
        foo = mod["Foo"].get_object()
        self.assertIn(generic, foo.get_mro())

    def test_generic_alias_omits_generic_before_direct_protocol(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        code = dedent("""\
            from typing import Generic, Protocol, TypeVar
            T = TypeVar("T")
            class Derived(Generic[T], Protocol):
                pass
        """)
        self._assert_mro_matches_python(code, ["Derived"])

    def test_typing_protocol_specialization_preserves_native_ancestor(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        code = dedent("""\
            from typing import Protocol, TypeVar
            T = TypeVar("T")
            class Derived(Protocol[T]):
                pass
        """)
        self._assert_mro_matches_python(code, ["Derived"])

    def test_typing_protocol_rejects_nonvariable_parameter(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        code = dedent("""\
            from typing import Protocol
            class Derived(Protocol[int]):
                pass
        """)
        with self.assertRaises(TypeError):
            exec(code, {})
        mod = libutils.get_string_module(self.project, code)
        with self.assertRaises(TypeError):
            mod["Derived"].get_object().get_mro()

    def test_unpacked_typevartuple_preserves_generic_and_protocol_parameters(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        available = all(name in typing.__dict__ for name in ("Unpack", "TypeVarTuple"))
        for family in ("Generic", "Protocol"):
            with self.subTest(family=family):
                code = dedent(f"""\
                    from typing import {family}, TypeVarTuple, Unpack
                    Ts = TypeVarTuple("Ts")
                    inner = Unpack[Ts]
                    alias = {family}[inner]
                    class Derived(alias):
                        pass
                """)
                namespace = {}
                if available:
                    exec(code, namespace)
                    self.assertIs(namespace["inner"].__args__[0], namespace["Ts"])
                    mod = libutils.get_string_module(self.project, code)
                    derived = mod["Derived"].get_object()
                    self.assertEqual(
                        [cls.__name__ for cls in namespace["Derived"].__mro__],
                        [cls.get_name() for cls in derived.get_mro()],
                    )
                    inner = mod["inner"].get_object()
                    variable = (
                        inner["__args__"]
                        .get_object()
                        .get_type()
                        .get_holding_objects()[0]
                    )
                    self.assertIs(variable, mod["Ts"].get_object())
                    self.assertIs(mod["alias"].get_object().arguments[0], inner)
                else:
                    with self.assertRaises(ImportError):
                        exec(code, namespace)
                    mod = libutils.get_string_module(self.project, code)
                    for name in ("Unpack", "TypeVarTuple"):
                        if name not in typing.__dict__:
                            self.assertIs(mod[name].get_object(), get_unknown())
                    with self.assertRaises(TypeError):
                        mod["Derived"].get_object().get_mro()

    def test_raw_typevartuple_is_not_a_generic_or_protocol_parameter(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        for family in ("Generic", "Protocol"):
            with self.subTest(family=family):
                code = dedent(f"""\
                    from typing import {family}, TypeVarTuple
                    Ts = TypeVarTuple("Ts")
                    class Derived({family}[Ts]):
                        pass
                """)
                if "TypeVarTuple" in typing.__dict__:
                    with self.assertRaises(TypeError):
                        exec(code, {})
                else:
                    with self.assertRaises(ImportError):
                        exec(code, {})
                mod = libutils.get_string_module(self.project, code)
                with self.assertRaises(TypeError):
                    mod["Derived"].get_object().get_mro()

    def test_named_typing_module_does_not_replace_its_declared_class_hook(self):
        code = dedent("""\
            class Other:
                pass
            class Generic:
                def __class_getitem__(cls, item):
                    return Other
            class Derived(Generic[int]):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertEqual((namespace["Other"],), namespace["Derived"].__bases__)
        resource = testutils.create_module(self.project, "typing")
        resource.write(code)
        mod = self.project.get_pymodule(resource)
        derived = mod["Derived"].get_object()
        self.assertEqual([derived, mod["Other"].get_object()], derived.get_mro())

    def test_generic_alias_omits_generic_before_later_typing_alias(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        code = dedent("""\
            from typing import Generic, TypeVar
            T = TypeVar("T")
            class Base(Generic[T]):
                pass
            class Derived(Generic[T], Base[T]):
                pass
        """)
        self._assert_mro_matches_python(code, ["Base", "Derived"])

    def test_generic_alias_keeps_generic_before_builtin_alias(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        code = dedent("""\
            from typing import Generic, TypeVar
            T = TypeVar("T")
            class Derived(Generic[T], list[T]):
                pass
        """)
        self._assert_mro_matches_python(code, ["Derived"])

    def test_generic_alias_rejects_repeated_parameters(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        code = dedent("""\
            from typing import Generic, TypeVar
            T = TypeVar("T")
            class Derived(Generic[T, T]):
                pass
        """)
        with self.assertRaises(TypeError):
            exec(code, {})
        mod = libutils.get_string_module(self.project, code)
        with self.assertRaises(TypeError):
            mod["Derived"].get_object().get_mro()

    def test_generic_alias_keeps_all_declared_parameters(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        code = dedent("""\
            from typing import Generic, TypeVar
            T = TypeVar("T")
            U = TypeVar("U")
            V = TypeVar("V")
            W = TypeVar("W")
            X = TypeVar("X")
            alias = Generic[T, U, V, W, X]
            class Derived(alias):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertEqual(5, len(namespace["alias"].__args__))
        mod = libutils.get_string_module(self.project, code)
        alias = mod["alias"].get_object()
        self.assertEqual(5, len(alias.arguments))
        for name, argument in zip(("T", "U", "V", "W", "X"), alias.arguments):
            self.assertIs(mod[name].get_object(), argument)

    def test_generic_alias_rejects_multiple_generic_declarations(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        code = dedent("""\
            from typing import Generic, TypeVar
            T = TypeVar("T")
            U = TypeVar("U")
            class Derived(Generic[T], Generic[U]):
                pass
        """)
        with self.assertRaises(TypeError):
            exec(code, {})
        mod = libutils.get_string_module(self.project, code)
        with self.assertRaises(TypeError):
            mod["Derived"].get_object().get_mro()

    def test_source_mro_entries_uses_original_bases_and_returned_class(self):
        code = dedent("""\
            class Other:
                pass
            class Alias:
                def __mro_entries__(self, bases):
                    return (bases[1],)
            class Derived(Alias(), Other):
                pass
        """)
        with self.assertRaises(TypeError):
            exec(code, {})
        mod = libutils.get_string_module(self.project, code)
        with self.assertRaises(exceptions.InconsistentHierarchyError):
            mod["Derived"].get_object().get_mro()

    def test_source_mro_entries_preserves_returned_class_identity(self):
        code = dedent("""\
            class Other:
                pass
            class Alias:
                def __mro_entries__(self, bases):
                    return (Other,)
            class Derived(Alias()):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertEqual((namespace["Other"],), namespace["Derived"].__bases__)
        mod = libutils.get_string_module(self.project, code)
        derived = mod["Derived"].get_object()
        self.assertEqual([derived, mod["Other"].get_object()], derived.get_mro())

    def test_source_mro_entries_preserves_every_returned_base(self):
        for count in (4, 5):
            with self.subTest(count=count):
                names = "ABCDE"[:count]
                code = dedent(f"""\
                    class A(object):
                        pass
                    class B(object):
                        pass
                    class C(object):
                        pass
                    class D(object):
                        pass
                    class E(object):
                        pass
                    class Alias:
                        def __mro_entries__(self, bases):
                            return ({", ".join(names)},)
                    class Derived(Alias()):
                        pass
                """)
                namespace = {}
                exec(code, namespace)
                self.assertEqual(
                    tuple(namespace[name] for name in names),
                    namespace["Derived"].__bases__,
                )
                mod = libutils.get_string_module(self.project, code)
                derived = mod["Derived"].get_object()
                self.assertEqual(
                    [mod[name].get_object() for name in names], derived.get_bases()
                )
                self.assertEqual(
                    [cls.__name__ for cls in namespace["Derived"].__mro__],
                    [cls.get_name() for cls in derived.get_mro()],
                )

    def test_source_mro_entries_rejects_a_noncallable_hook(self):
        code = dedent("""\
            class Alias:
                __mro_entries__ = None
            class Derived(Alias()):
                pass
        """)
        with self.assertRaises(TypeError):
            exec(code, {})
        mod = libutils.get_string_module(self.project, code)
        with self.assertRaises(TypeError):
            mod["Derived"].get_object().get_mro()

    def test_source_mro_entries_staticmethod_receives_only_original_bases(self):
        code = dedent("""\
            class Other:
                pass
            class Alias:
                replacement = Other
                @staticmethod
                def __mro_entries__(bases):
                    return (bases[0].replacement,)
            class Derived(Alias()):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertEqual((namespace["Other"],), namespace["Derived"].__bases__)
        mod = libutils.get_string_module(self.project, code)
        derived = mod["Derived"].get_object()
        self.assertEqual([derived, mod["Other"].get_object()], derived.get_mro())

    def test_source_mro_entries_classmethod_receives_its_class(self):
        code = dedent("""\
            class Alias:
                @classmethod
                def __mro_entries__(cls, bases):
                    return (cls,)
            class Derived(Alias()):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertEqual((namespace["Alias"],), namespace["Derived"].__bases__)
        mod = libutils.get_string_module(self.project, code)
        derived = mod["Derived"].get_object()
        self.assertEqual([derived, mod["Alias"].get_object()], derived.get_mro())

    def test_source_mro_entries_invokes_callable_instance(self):
        code = dedent("""\
            class Other:
                pass
            class Rewriter:
                def __call__(self, bases):
                    return (Other,)
            class Alias:
                __mro_entries__ = Rewriter()
            class Derived(Alias()):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertEqual((namespace["Other"],), namespace["Derived"].__bases__)
        mod = libutils.get_string_module(self.project, code)
        derived = mod["Derived"].get_object()
        self.assertEqual([derived, mod["Other"].get_object()], derived.get_mro())

    def test_source_mro_entries_class_lambda_retains_original_bases(self):
        code = dedent("""\
            class Other:
                pass
            class Alias:
                replacement = Other
                __mro_entries__ = classmethod(
                    lambda cls, bases: (bases[0].replacement,)
                )
            class Derived(Alias()):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertEqual((namespace["Other"],), namespace["Derived"].__bases__)
        mod = libutils.get_string_module(self.project, code)
        derived = mod["Derived"].get_object()
        self.assertEqual([derived, mod["Other"].get_object()], derived.get_mro())

    @unittest.skipUnless(sys.version_info >= (3, 12), "PEP 695 requires Python 3.12")
    def test_implicit_generic_specialization_preserves_owner_and_bound(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        code = dedent("""\
            class Identity:
                pass
            class Ownership[Resource: Identity]:
                pass
            class Leaf(Ownership[Identity]):
                pass
        """)
        namespace = {}
        exec(code, namespace)
        self.assertIs(namespace["Ownership"].__type_params__[0].__bound__, namespace["Identity"])
        mod = libutils.get_string_module(self.project, code)
        owner = mod["Ownership"].get_object()
        leaf = mod["Leaf"].get_object()
        self.assertIs(leaf.get_mro()[1], owner)
        parameter = owner.get_ast().type_params[0]
        index = mod.get_source_binding_index()
        binding = index.context_for_node(parameter).environment.lookup("Resource")
        self.assertIs(binding.node, parameter)
        bound = index.context_for_node(parameter.bound).environment.lookup("Identity")
        self.assertIs(bound.get_object(), mod["Identity"].get_object())
        self.assertEqual(
            [cls.__name__ for cls in namespace["Leaf"].__mro__],
            [cls.get_name() for cls in leaf.get_mro()],
        )

    def test_mro_contains_object_only_when_declared(self):
        code = dedent("""\
            class Base:
                pass
            class Derived(Base):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        derived = mod["Derived"].get_object()
        self.assertEqual(
            ["Derived", "Base"], [cls.get_name() for cls in derived.get_mro()]
        )

    def test_diamond_attributes_follow_the_mro(self):
        code = dedent("""\
            class A(object):
                def method(self):
                    pass
            class B(A):
                pass
            class C(A):
                def method(self):
                    pass
            class D(B, C):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        c = mod["C"].get_object()
        d = mod["D"].get_object()
        self.assertEqual(c["method"].get_object(), d["method"].get_object())

    def test_unresolved_base_keeps_its_place(self):
        code = dedent("""\
            class Base(object):
                pass
            class Other(object):
                pass
            class Derived(Base, NotFound, Other):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        base = mod["Base"].get_object()
        other = mod["Other"].get_object()
        derived = mod["Derived"].get_object()
        first, unresolved, last = derived.get_bases()
        self.assertEqual(base, first)
        self.assertIsInstance(unresolved, UnresolvedBase)
        self.assertEqual("NotFound", unresolved.node.id)
        self.assertIsNone(unresolved.pyobject)
        self.assertEqual(other, last)
        self.assertEqual([base, other], derived.get_superclasses())
        self.assertEqual(
            [derived, base, unresolved, other, derived.get_mro()[-1]],
            derived.get_mro(),
        )
        self.assertEqual("object", derived.get_mro()[-1].get_name())

    def test_base_evaluating_to_a_non_class_is_unresolved(self):
        code = dedent("""\
            value = 1
            class Derived(value):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        derived = mod["Derived"].get_object()
        (unresolved,) = derived.get_bases()
        self.assertIsInstance(unresolved, UnresolvedBase)
        self.assertEqual(mod["value"].get_object(), unresolved.pyobject)
        self.assertEqual([], derived.get_superclasses())
        self.assertEqual([derived, unresolved], derived.get_mro())

    def test_imported_missing_base_preserves_resolved_ancestors(self):
        provider = testutils.create_module(self.project, "provider")
        provider.write("def function():\n    pass\n")
        code = dedent("""\
            from provider import missing
            class Base(object):
                pass
            class Derived(Base, missing):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        base = mod["Base"].get_object()
        derived = mod["Derived"].get_object()
        mro = derived.get_mro()
        resolved, unresolved = derived.get_bases()
        self.assertIs(base, resolved)
        self.assertIsInstance(unresolved, UnresolvedBase)
        self.assertEqual([base], derived.get_superclasses())
        self.assertEqual(
            [derived, *base.get_mro(), unresolved],
            mro,
        )

    def test_class_base_uses_import_before_rebinding_its_name(self):
        provider = testutils.create_module(self.project, "provider")
        provider.write(dedent("""\
            class Foo:
                member = 1
        """))
        resource = testutils.create_module(self.project, "consumer")
        resource.write(dedent("""\
            from provider import Foo
            class Foo(Foo):
                pass
        """))
        imported = self.project.get_pymodule(provider)["Foo"].get_object()
        derived = self.project.get_pymodule(resource)["Foo"].get_object()
        self.assertEqual([derived, imported], derived.get_mro())
        self.assertIs(derived["member"], imported["member"])

    def test_subscripted_base_uses_import_before_a_later_self_alias(self):
        provider = testutils.create_module(self.project, "provider")
        provider.write(dedent("""\
            class Service:
                member = 1
                def __class_getitem__(cls, item):
                    return cls
            s = Service
        """))
        resource = testutils.create_module(self.project, "consumer")
        resource.write(dedent("""\
            from provider import s
            class Guards:
                pass
            class AppService(Guards, s[dict]):
                pass
            s = AppService
        """))
        imported = self.project.get_pymodule(provider)["Service"].get_object()
        consumer = self.project.get_pymodule(resource)
        derived = consumer["AppService"].get_object()
        guards = consumer["Guards"].get_object()
        self.assertEqual([derived, guards, imported], derived.get_mro())
        self.assertIs(derived["member"], imported["member"])

    def test_attribute_base_uses_module_before_a_later_rebinding(self):
        provider = testutils.create_module(self.project, "provider")
        provider.write(dedent("""\
            class Base:
                member = 1
        """))
        resource = testutils.create_module(self.project, "consumer")
        resource.write(dedent("""\
            import provider
            class Derived(provider.Base):
                pass
            provider = Derived
        """))
        imported = self.project.get_pymodule(provider)["Base"].get_object()
        derived = self.project.get_pymodule(resource)["Derived"].get_object()
        self.assertEqual([derived, imported], derived.get_mro()[:2])
        self.assertIs(derived["member"], imported["member"])

    @unittest.skipUnless(sys.version_info >= (3, 12), "PEP 695 requires Python 3.12")
    def test_generic_class_base_uses_import_before_rebinding_its_name(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        provider = testutils.create_module(self.project, "provider")
        provider.write(dedent("""\
            class Foo:
                member = 1
        """))
        resource = testutils.create_module(self.project, "consumer")
        resource.write(dedent("""\
            from provider import Foo
            class Foo[T](Foo):
                pass
        """))
        imported = self.project.get_pymodule(provider)["Foo"].get_object()
        derived = self.project.get_pymodule(resource)["Foo"].get_object()
        namespace = {}
        exec(provider.read(), namespace)
        exec("class Foo[T](Foo):\n    pass\n", namespace)
        self.assertEqual(
            [cls.__name__ for cls in namespace["Foo"].__mro__],
            [cls.get_name() for cls in derived.get_mro()],
        )
        self.assertIs(derived.get_mro()[1], imported)
        self.assertIs(derived["member"], imported["member"])

    @unittest.skipUnless(sys.version_info >= (3, 12), "PEP 695 requires Python 3.12")
    def test_generic_parameter_precedes_imported_previous_class_name(self):
        self.project.prefs.set("import_dynload_stdmods", True)
        provider = testutils.create_module(self.project, "provider")
        provider.write(dedent("""\
            class Foo:
                pass
        """))
        resource = testutils.create_module(self.project, "consumer")
        resource.write(dedent("""\
            from provider import Foo
            class Foo[Foo](Foo):
                pass
        """))
        derived = self.project.get_pymodule(resource)["Foo"].get_object()
        unresolved, generic = derived.get_bases()
        self.assertIsInstance(unresolved, UnresolvedBase)
        self.assertIs(unresolved.pyobject, get_unknown())
        self.assertIs(self.project.get_module("typing")["Generic"].get_object(), generic)

    def test_inconsistent_mro(self):
        code = dedent("""\
            class A(object):
                pass
            class B(object):
                pass
            class X(A, B):
                pass
            class Y(B, A):
                pass
            class Z(X, Y):
                pass
            class W(Z):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        z = mod["Z"].get_object()
        with self.assertRaises(exceptions.InconsistentHierarchyError):
            z.get_mro()
        self.assertIsNone(z.get_consistent_mro())
        self.assertIsNone(mod["W"].get_object().get_consistent_mro())

    def test_inconsistent_mro_keeps_attributes_along_the_bases(self):
        # Python refuses to create these classes, but rope keeps analysing
        # them as it always did: only `get_mro()` reports the hierarchy.
        code = dedent("""\
            class A(object):
                def a_method(self):
                    pass
            class B(A):
                def b_method(self):
                    pass
            class C(A, B):
                def c_method(self):
                    pass
        """)
        mod = libutils.get_string_module(self.project, code)
        c = mod["C"].get_object()
        self.assertEqual(
            {"a_method", "b_method", "c_method"},
            {name for name in c.get_attributes() if name.endswith("_method")},
        )
        self.assertEqual(
            mod["B"].get_object()["b_method"].get_object(),
            c["b_method"].get_object(),
        )
        self.assertEqual(
            [mod["A"].get_object(), mod["B"].get_object()], c.get_superclasses()
        )

    def test_type_hinting_get_mro_walks_the_bases(self):
        from rope.base.oi.type_hinting.utils import get_mro

        code = dedent("""\
            class A(object):
                pass
            class B(A):
                pass
            class C(B, A):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        a, b, c = (mod[name].get_object() for name in ("A", "B", "C"))
        self.assertEqual([c, b, a], get_mro(c))

    def test_duplicate_base_class(self):
        code = dedent("""\
            class A(object):
                pass
            class B(A, A):
                pass
        """)
        mod = libutils.get_string_module(self.project, code)
        with self.assertRaises(exceptions.InconsistentHierarchyError):
            mod["B"].get_object().get_mro()
        self.assertIsNone(mod["B"].get_object().get_consistent_mro())

    def test_cyclic_inheritance(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write("from mod2 import B\nclass A(B):\n    pass\n")
        mod2.write("from mod1 import A\nclass B(A):\n    pass\n")
        a = self.project.get_module("mod1")["A"].get_object()
        with self.assertRaises(exceptions.InconsistentHierarchyError):
            a.get_mro()
        self.assertIsNone(a.get_consistent_mro())

    def test_offset_resolution_follows_changes_in_other_modules(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write("class C:\n    attr = 1\n")
        code = "from mod2 import C\nresult = C().attr\n"
        mod1.write(code)
        offset = code.rindex("attr")

        def attribute_definition():
            pymodule = self.project.get_pymodule(mod1)
            pyname = evaluate.eval_location(pymodule, offset)
            return pyname.get_definition_location()

        module, lineno = attribute_definition()
        self.assertEqual((self.project.get_pymodule(mod2), 2), (module, lineno))
        mod2.write("class C:\n\n    attr = 1\n")
        module, lineno = attribute_definition()
        self.assertEqual((self.project.get_pymodule(mod2), 3), (module, lineno))

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

    def test_find_module_prefers_module_to_namespace_directory(self):
        self.project.root.create_folder("sample")
        samplemod = testutils.create_module(self.project, "sample")
        self.assertEqual(samplemod, self.project.find_module("sample"))

    def test_find_module_retains_namespace_directory(self):
        namespace = self.project.root.create_folder("sample")
        self.project.close()
        self.project = Project(self.project.address, source_folders=[""])
        self.assertEqual(namespace, self.project.find_module("sample"))

    def test_find_nested_module_does_not_search_shadowed_namespace(self):
        namespace = self.project.root.create_folder("sample")
        testutils.create_module(self.project, "child", namespace)
        testutils.create_module(self.project, "sample")
        self.assertIsNone(self.project.find_module("sample.child"))

    def test_find_module_skips_python_path_files(self):
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        # Rope reports real paths; temporary directories may sit behind a
        # symlink (macOS /var) or a short name (Windows RUNNER~1).
        root = os.path.realpath(external.name)
        archive = os.path.join(root, "archive.zip")
        libs = os.path.join(root, "libs")
        os.mkdir(libs)
        open(archive, "w").close()
        with open(os.path.join(libs, "sample.py"), "w") as sample:
            sample.write("")
        self.project.close()
        self.project = Project(self.project.address, python_path=[archive, libs])
        self.assertEqual(
            os.path.join(libs, "sample.py"),
            self.project.find_module("sample").real_path,
        )

    def test_find_module_defers_namespace_to_later_source_module(self):
        first = self.project.root.create_folder("first")
        second = self.project.root.create_folder("second")
        first.create_folder("sample")
        samplemod = testutils.create_module(self.project, "sample", second)
        self.project.close()
        self.project = Project(self.project.address, source_folders=["first", "second"])
        self.assertEqual(samplemod, self.project.find_module("sample"))

    def test_find_module_defers_namespace_to_later_regular_package(self):
        first = self.project.root.create_folder("first")
        second = self.project.root.create_folder("second")
        namespace = first.create_folder("sample")
        testutils.create_module(self.project, "child", namespace)
        package = testutils.create_package(self.project, "sample", second)
        self.project.close()
        self.project = Project(self.project.address, source_folders=["first", "second"])
        self.assertEqual(package, self.project.find_module("sample"))
        self.assertIsNone(self.project.find_module("sample.child"))

    def test_find_nested_module_searches_namespace_portions(self):
        first = self.project.root.create_folder("first")
        second = self.project.root.create_folder("second")
        first.create_folder("sample")
        namespace = second.create_folder("sample")
        samplemod = testutils.create_module(self.project, "child", namespace)
        self.project.close()
        self.project = Project(self.project.address, source_folders=["first", "second"])
        self.assertEqual(samplemod, self.project.find_module("sample.child"))

    def test_relative_import_prefers_config_module_to_namespace_directory(self):
        package = testutils.create_package(self.project, "sample")
        package.create_folder("config")
        config = testutils.create_module(self.project, "config", package)
        config.write("class FlextCliConfig:\n    pass\n")
        consumer = testutils.create_module(self.project, "consumer", package)
        consumer.write("from .config import FlextCliConfig\n")
        expected = self.project.get_pymodule(config)["FlextCliConfig"].get_object()
        actual = self.project.get_pymodule(consumer)["FlextCliConfig"].get_object()
        self.assertEqual(expected, actual)

    def test_relative_import_keeps_regular_package_precedence(self):
        package = testutils.create_package(self.project, "sample")
        testutils.create_module(self.project, "config", package)
        config = testutils.create_package(self.project, "config", package)
        config.get_child("__init__.py").write("class Configuration:\n    pass\n")
        consumer = testutils.create_module(self.project, "consumer", package)
        consumer.write("from .config import Configuration\n")
        expected = self.project.get_pymodule(config)["Configuration"].get_object()
        actual = self.project.get_pymodule(consumer)["Configuration"].get_object()
        self.assertEqual(expected, actual)

    def test_relative_module_does_not_search_unrelated_source_roots(self):
        package = testutils.create_package(self.project, "sample")
        testutils.create_module(self.project, "config")
        with self.assertRaises(exceptions.ModuleNotFoundError):
            self.project.get_relative_module("config", package, 1)

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

    def test_get_pyname_definition_location_imported(self):
        testutils.create_module(self.project, "mod")
        code = "import mod\n"
        mod = libutils.get_string_module(self.project, code)
        imported_module = self.project.get_module("mod")
        module_pyname = mod["mod"]
        self.assertEqual((imported_module, 1), module_pyname.get_definition_location())

    def test_get_pyname_definition_location_imports(self):
        module_resource = testutils.create_module(self.project, "mod")
        module_resource.write(dedent("""\

            def a_func():
                pass
        """))
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
            "# -*- coding: utf-8 -*-\n" + "#\N{LATIN SMALL LETTER I WITH DIAERESIS}\n"
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

    def test_with_statement_variables(self):
        code = dedent("""\
            import threading
            with threading.lock() as var:    pass
        """)
        if sys.version_info < (2, 6, 0):
            code = "from __future__ import with_statement\n" + code
        pymod = libutils.get_string_module(self.project, code)
        self.assertTrue("var" in pymod)

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
        mod1.write(dedent("""\
            var1 = ""
            var2 = ""
        """))
        pymod1 = self.pycore.resource_to_pyobject(mod1)
        self.assertEqual(pymod1["var1"].get_object(), pymod1["var2"].get_object())


class PyCoreInProjectsTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
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
        super().tearDown()

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

    def test_from_import_star_not_importing_underlined(self):
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
        mod1.write(dedent("""\
            from mod2 import Sample2
            class Sample1(object):
                pass
        """))
        mod2.write(dedent("""\
            from mod1 import Sample1
            class Sample2(object):
                pass
        """))
        self.project.get_module("mod1").get_attributes()

    def test_multi_dot_imports(self):
        pkg = testutils.create_package(self.project, "pkg")
        pkg_mod = testutils.create_module(self.project, "mod", pkg)
        pkg_mod.write(dedent("""\
            def sample_func():
                pass
        """))
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
        mod1.write(dedent("""\
            def f():
                pass
        """))
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
        mod1.write(dedent("""\
            def a_func():
                pass
        """))
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

    def test_new_style_relative_imports(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod1 = testutils.create_module(self.project, "mod1", pkg)
        mod2 = testutils.create_module(self.project, "mod2", pkg)
        mod2.write("from . import mod1\n")
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEqual(mod1_object, mod2_object["mod1"].get_object())

    def test_new_style_relative_imports2(self):
        pkg = testutils.create_package(self.project, "pkg")
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2", pkg)
        mod1.write(dedent("""\
            def a_func():
                pass
        """))
        mod2.write("from ..mod1 import a_func\n")
        mod1_object = self.pycore.resource_to_pyobject(mod1)
        mod2_object = self.pycore.resource_to_pyobject(mod2)
        self.assertEqual(
            mod1_object["a_func"].get_object(), mod2_object["a_func"].get_object()
        )

    def test_invalidating_cache_for_from_imports_after_resource_change(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write(dedent("""\
            def a_func():
                print(1)
        """))
        mod1.write(dedent("""\
            from mod2 import a_func
            a_func()
        """))

        pymod1 = self.project.get_module("mod1")
        pymod2 = self.project.get_module("mod2")
        self.assertEqual(pymod1["a_func"].get_object(), pymod2["a_func"].get_object())
        mod2.write(mod2.read() + "\n")
        pymod2 = self.project.get_module("mod2")
        self.assertEqual(pymod1["a_func"].get_object(), pymod2["a_func"].get_object())

    def test_invalidating_superclasses_after_change(self):
        mod1 = testutils.create_module(self.project, "mod1")
        mod2 = testutils.create_module(self.project, "mod2")
        mod1.write(dedent("""\
            class A(object):
                def func1(self):
                    pass
        """))
        mod2.write(dedent("""\
            import mod1
            class B(mod1.A):
                pass
        """))

        b_class = self.project.get_module("mod2")["B"].get_object()
        self.assertTrue("func1" in b_class)

        mod1.write(dedent("""\
            class A(object):
                def func2(self):
                    pass
        """))
        self.assertTrue("func2" in b_class)

    def test_caching_pymodule_with_syntax_errors(self):
        self.project.prefs["ignore_syntax_errors"] = True
        self.project.prefs["automatic_soa"] = True
        self.project.pycore._init_automatic_soa()
        source = dedent("""\
            import sys
            ab cd
        """)
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
        super().setUp()
        self.project = None

    def tearDown(self):
        if self.project:
            testutils.remove_project(self.project)
        super().tearDown()

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
