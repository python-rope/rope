from __future__ import annotations

import runpy
import sys
import unittest
from textwrap import dedent
from typing import TYPE_CHECKING, Union

from rope.base import exceptions, libutils
from rope.refactor import move, occurrences
from ropetest import testutils

if TYPE_CHECKING:
    from rope.base import project, resources

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

    def test_move_nested_class_to_existing_class(self):
        self.mod1.write(dedent("""\
            from collections.abc import Mapping

            class Owner:
                class Inner:
                    def size(self, value: Mapping[str, int]) -> int:
                        return len(value)
        """))
        self.mod2.write(dedent("""\
            class Target:
                pass
        """))
        self.mod3.write(dedent("""\
            from mod1 import Owner
            value = Owner.Inner()
        """))
        mover = move.create_move(
            self.project, self.mod1, self.mod1.read().index("Inner")
        )
        changes = mover.get_changes(
            self.mod2, destination_offset=self.mod2.read().index("Target")
        )
        self.project.do(changes)
        self.assertNotIn("class Inner", self.mod1.read())
        self.assertIn("class Inner", self.mod2.read())
        self.assertIn("Mapping", self.mod2.read())
        self.assertIn("mod2.Target.Inner()", self.mod3.read())
        namespace = runpy.run_path(self.mod2.real_path)
        self.assertEqual(1, namespace["Target"].Inner().size({"a": 1}))

    def test_move_nested_class_preserves_explicit_namespace_import_root(self):
        project = testutils.sample_project(source_folders=[""])
        try:
            namespace = project.root.create_folder("infra")
            package = testutils.create_package(project, "contracts", namespace)
            origin = testutils.create_module(project, "origin", package)
            target = testutils.create_module(project, "current", package)
            consumer = testutils.create_module(project, "consumer")
            origin.write(dedent("""\
                class Owner:
                    class Inner:
                        pass
            """))
            target.write(dedent("""\
                class Target:
                    pass
            """))
            consumer.write(dedent("""\
                from infra.contracts.origin import Owner
                value = Owner.Inner()
            """))
            self.assertIs(project.get_module("infra.contracts.current"), project.get_pymodule(target))
            self.assertEqual("infra.contracts.current", libutils.modname(target))
            mover = move.create_move(project, origin, origin.read().index("Inner"))
            project.do(mover.get_changes(target, destination_offset=target.read().index("Target")))
            self.assertIn("infra.contracts.current", consumer.read())
            namespace = runpy.run_path(target.real_path)
            self.assertIsInstance(namespace["Target"].Inner(), namespace["Target"].Inner)
        finally:
            testutils.remove_project(project)

    def test_move_nested_class_with_recursive_nested_references(self):
        self.mod1.write(dedent("""\
            class Owner:
                class Inner:
                    class Child:
                        pass
                    def clone(self):
                        return Owner.Inner()
                    def child(self):
                        return Owner.Inner.Child()
        """))
        self.mod2.write(dedent("""\
            class Target:
                pass
        """))
        mover = move.create_move(self.project, self.mod1, self.mod1.read().index("Inner"))
        self.project.do(mover.get_changes(self.mod2, destination_offset=self.mod2.read().index("Target")))
        namespace = runpy.run_path(self.mod2.real_path)
        inner = namespace["Target"].Inner
        self.assertIsInstance(inner().clone(), inner)
        self.assertIsInstance(inner().child(), inner.Child)

    def test_move_nested_class_to_module(self):
        self.mod1.write(dedent("""\
            class Owner:
                class Inner:
                    pass
        """))
        self.mod3.write(dedent("""\
            from mod1 import Owner
            value = Owner.Inner()
        """))
        self._move(self.mod1, self.mod1.read().index("Inner"), self.mod2)
        self.assertIn("mod2.Inner()", self.mod3.read())
        self.assertIn("class Inner:", self.mod2.read())
        compile(self.mod1.read(), self.mod1.path, "exec")

    def test_move_nested_class_in_same_module(self):
        self.mod1.write(dedent("""\
            class Owner:
                class Inner:
                    pass
            class Target:
                pass
            value = Owner.Inner()
        """))
        mover = move.create_move(self.project, self.mod1, self.mod1.read().index("Inner"))
        self.project.do(mover.get_changes(self.mod1, destination_offset=self.mod1.read().index("Target")))
        namespace = runpy.run_path(self.mod1.real_path)
        self.assertIsInstance(namespace["value"], namespace["Target"].Inner)

    def test_move_nested_class_rejects_enclosing_class_dependency(self):
        source = dedent("""\
            class Owner:
                class Base:
                    pass
                class Inner(Base):
                    pass
        """)
        self.mod1.write(source)
        mover = move.create_move(self.project, self.mod1, source.index("Inner"))
        with self.assertRaisesRegex(exceptions.RefactoringError, "enclosing"):
            mover.get_changes(self.mod2)
        self.assertEqual(source, self.mod1.read())

    def test_move_nested_class_rejects_shadowed_enclosing_dependency(self):
        source = dedent("""\
            Base = object
            class Owner:
                class Base:
                    pass
                class Inner(Base):
                    pass
        """)
        self.mod1.write(source)
        mover = move.create_move(self.project, self.mod1, source.index("Inner"))
        with self.assertRaisesRegex(exceptions.RefactoringError, "enclosing"):
            mover.get_changes(self.mod2)
        self.assertEqual(source, self.mod1.read())

    def test_move_decorated_nested_class_copies_imports(self):
        self.mod1.write(dedent("""\
            from dataclasses import dataclass
            class Owner:
                @dataclass
                class Inner:
                    value: int
        """))
        self.mod2.write(dedent("""\
            class Target:
                pass
        """))
        mover = move.create_move(self.project, self.mod1, self.mod1.read().index("Inner"))
        self.project.do(mover.get_changes(self.mod2, destination_offset=self.mod2.read().index("Target")))
        namespace = runpy.run_path(self.mod2.real_path)
        self.assertEqual(3, namespace["Target"].Inner(3).value)

    def test_move_nested_class_rejects_destination_collision(self):
        self.mod1.write(dedent("""\
            class Owner:
                class Inner:
                    pass
        """))
        destination = dedent("""\
            class Target:
                class Inner:
                    pass
        """)
        self.mod2.write(destination)
        mover = move.create_move(self.project, self.mod1, self.mod1.read().index("Inner"))
        with self.assertRaisesRegex(exceptions.RefactoringError, "Occupied"):
            mover.get_changes(self.mod2, destination_offset=destination.index("Target"))
        self.assertEqual(destination, self.mod2.read())

    def test_move_nested_class_reference_filter_keeps_composed_access(self):
        self.mod1.write(dedent("""\
            class Owner:
                class Inner:
                    pass
            class Public(Owner):
                pass
        """))
        self.mod2.write(dedent("""\
            class Target:
                pass
        """))
        self.mod3.write(dedent("""\
            from mod1 import Owner, Public
            direct = Owner.Inner
            composed = Public.Inner
            direct_annotation: 'Owner.Inner'
            composed_annotation: 'Public.Inner'
        """))
        mover = move.create_move(self.project, self.mod1, self.mod1.read().index("Inner"))
        public = self.project.get_pymodule(self.mod1)["Public"].get_object()
        changes = mover.get_changes(
            self.mod2,
            destination_offset=self.mod2.read().index("Target"),
            match_filter=lambda occurrence: occurrence.get_primary_and_pyname()[0].get_object() is not public,
        )
        self.project.do(changes)
        self.assertIn("direct = mod2.Target.Inner", self.mod3.read())
        self.assertIn("composed = Public.Inner", self.mod3.read())
        self.assertIn("direct_annotation: 'mod2.Target.Inner'", self.mod3.read())
        self.assertIn("composed_annotation: 'Public.Inner'", self.mod3.read())

    def test_move_nested_class_filter_preserves_exact_proven_destination_sites(self):
        for unknown in (False, True):
            with self.subTest(unknown=unknown):
                self.mod1.write(dedent("""\
                    class Owner:
                        class Inner:
                            pass
                """))
                self.mod2.write(dedent("""\
                    class Target:
                        class Inner:
                            pass
                """))
                self.mod3.write(dedent("""\
                    import mod1
                    import mod2
                    direct = mod1.Owner.Inner()
                    current = mod2.Target.Inner()
                """) + (dedent("""\
                    def unresolved(value):
                        return value.Inner
                """) if unknown else ""))
                current = self.project.get_pymodule(self.mod2)["Target"].get_object()["Inner"]
                finder = occurrences.create_finder(self.project, "Inner", current)
                proven = {
                    (site.resource.path, site.get_primary_range())
                    for site in finder.find_occurrences(self.mod3)
                }
                self.assertEqual(1, len(proven))
                self.mod2.write(dedent("""\
                    class Target:
                        pass
                """))
                mover = move.create_move(self.project, self.mod1, self.mod1.read().index("Inner"))
                destination_offset = self.mod2.read().index("Target")
                with self.assertRaisesRegex(exceptions.RefactoringError, "Unproven"):
                    mover.get_changes(self.mod2, destination_offset=destination_offset)
                def selected(site):
                    return (site.resource.path, site.get_primary_range()) not in proven
                if unknown:
                    with self.assertRaisesRegex(exceptions.RefactoringError, "Unproven"):
                        mover.get_changes(self.mod2, destination_offset=destination_offset, match_filter=selected)
                else:
                    self.project.do(mover.get_changes(self.mod2, destination_offset=destination_offset, match_filter=selected))
                    self.assertNotIn("mod1.Owner.Inner", self.mod3.read())
                    self.assertIn("current = mod2.Target.Inner()", self.mod3.read())
                    namespace = runpy.run_path(self.mod2.real_path)
                    self.assertIsInstance(namespace["Target"].Inner(), namespace["Target"].Inner)

    def test_move_nested_class_rejects_import_collision(self):
        self.mod1.write(dedent("""\
            from collections.abc import Mapping
            class Owner:
                class Inner:
                    value: Mapping
        """))
        self.mod2.write(dedent("""\
            Mapping = str
            class Target:
                pass
        """))
        mover = move.create_move(self.project, self.mod1, self.mod1.read().index("Inner"))
        with self.assertRaisesRegex(exceptions.RefactoringError, "import conflicts"):
            mover.get_changes(self.mod2, destination_offset=self.mod2.read().index("Target"))

    def test_move_nested_class_rewrites_quoted_type_operands_only(self):
        self.mod1.write(dedent("""\
            class Owner:
                class Inner:
                    pass
        """))
        self.mod2.write(dedent("""\
            class Target:
                pass
        """))
        self.mod4.write("class ForwardRef: pass\n")
        self.mod3.write(dedent('''\
            from typing import Annotated as Meta, Literal as Value, ForwardRef as Ref
            import typing as ty
            from pkg.mod4 import ForwardRef as Fake
            from mod1 import Owner as Legacy
            text = "Legacy.Inner"
            def consume(value: 'Legacy.Inner') -> "list['Legacy.Inner']":
                """Legacy.Inner is explanatory text."""
                return [value]
            variable: 'Legacy.Inner'
            literal: Value['Legacy.Inner']
            metadata: Meta['Legacy.Inner', 'Legacy.Inner']
            explicit: Ref('Legacy.Inner')
            qualified: ty.ForwardRef('Legacy.Inner')
            unrelated: Fake('Legacy.Inner')
            escaped: "list[\\\"Legacy.Inner\\\"]"
        '''))
        mover = move.create_move(self.project, self.mod1, self.mod1.read().index("Inner"))
        self.project.do(mover.get_changes(self.mod2, destination_offset=self.mod2.read().index("Target")))
        self.assertIn("value: 'mod2.Target.Inner'", self.mod3.read())
        self.assertIn('"list[\'mod2.Target.Inner\']"', self.mod3.read())
        self.assertIn("variable: 'mod2.Target.Inner'", self.mod3.read())
        self.assertIn("Value['Legacy.Inner']", self.mod3.read())
        self.assertIn("Meta['mod2.Target.Inner', 'Legacy.Inner']", self.mod3.read())
        self.assertIn("Ref('mod2.Target.Inner')", self.mod3.read())
        self.assertIn("ty.ForwardRef('mod2.Target.Inner')", self.mod3.read())
        self.assertIn("Fake('Legacy.Inner')", self.mod3.read())
        self.assertIn('escaped: "list[\\\"mod2.Target.Inner\\\"]"', self.mod3.read())
        self.assertIn('text = "Legacy.Inner"', self.mod3.read())
        self.assertIn('"""Legacy.Inner is explanatory text."""', self.mod3.read())

    def test_move_nested_class_rejects_consumer_import_shadow(self):
        self.mod1.write(dedent("""\
            class Owner:
                class Inner:
                    pass
        """))
        self.mod2.write(dedent("""\
            class Target:
                pass
        """))
        self.mod3.write(dedent("""\
            from mod1 import Owner
            def use(mod2):
                return Owner.Inner()
        """))
        mover = move.create_move(self.project, self.mod1, self.mod1.read().index("Inner"))
        with self.assertRaisesRegex(exceptions.RefactoringError, "consumer binding"):
            mover.get_changes(self.mod2, destination_offset=self.mod2.read().index("Target"))

    def test_transfer_methods_to_enclosing_class_in_same_module(self):
        self.mod1.write(dedent("""\
            value = 7

            class Owner:
                class Helpers:
                    @staticmethod
                    def make(number=2):
                        return value + number

                    @classmethod
                    def name(cls):
                        return "name"

            result = Owner.Helpers.make()
        """))
        self.mod2.write("from mod1 import Owner\nresult = Owner.Helpers.make(5)\n")
        source = self.mod1.read()
        changes = move.MoveMethod.get_class_changes(
            self.project,
            [
                (self.mod1, source.index("def make") + 4, "make"),
                (self.mod1, source.index("def name") + 4, "name"),
            ],
            self.mod1,
            source.index("class Owner") + 6,
            resources=[self.mod1, self.mod2],
        )
        self.project.do(changes)
        changed = self.mod1.read()
        self.assertNotIn("from mod1 import", changed)
        namespace = {}
        exec(changed, namespace)
        owner = namespace["Owner"]
        self.assertIsInstance(owner.__dict__["make"], staticmethod)
        self.assertIsInstance(owner.__dict__["name"], classmethod)
        self.assertEqual(9, namespace["result"])
        self.assertEqual(12, owner.make(5))
        self.assertEqual("name", owner.name())
        self.assertIn("Owner.make(5)", self.mod2.read())

    def test_transfer_rejects_changed_class_scope_default(self):
        self.mod1.write(dedent("""\
            class Owner:
                value = 1
                class Helpers:
                    value = 2
                    @staticmethod
                    def make(number=value):
                        return number
        """))
        source = self.mod1.read()
        with self.assertRaises(exceptions.RefactoringError):
            move.MoveMethod.get_class_changes(
                self.project,
                [(self.mod1, source.index("def make") + 4, "make")],
                self.mod1,
                source.index("class Owner") + 6,
                resources=[self.mod1],
            )
        self.assertEqual(source, self.mod1.read())

    def test_transfer_rejects_changed_module_binding(self):
        self.mod1.write(dedent("""\
            class Owner:
                class Helpers:
                    @staticmethod
                    def make():
                        return value

            value = Owner.Helpers.make
        """))
        source = self.mod1.read()
        with self.assertRaises(exceptions.RefactoringError):
            move.MoveMethod.get_class_changes(
                self.project,
                [(self.mod1, source.index("def make") + 4, "make")],
                self.mod1,
                source.index("class Owner") + 6,
                resources=[self.mod1],
            )
        self.assertEqual(source, self.mod1.read())

    def test_transfer_rejects_ambiguous_module_reassignment(self):
        self.mod1.write(dedent("""\
            value = 1
            class Owner:
                class Helpers:
                    @staticmethod
                    def make():
                        return value

            value = Owner.Helpers.make
        """))
        source = self.mod1.read()
        with self.assertRaises(exceptions.RefactoringError):
            move.MoveMethod.get_class_changes(
                self.project,
                [(self.mod1, source.index("def make") + 4, "make")],
                self.mod1,
                source.index("class Owner") + 6,
                resources=[self.mod1],
            )
        self.assertEqual(source, self.mod1.read())

    def test_transfer_rejects_cross_module_redirected_globals(self):
        for statement in ("return value", "value = 3\n        return value"):
            with self.subTest(statement=statement):
                source = (
                    "value = 1\nclass A:\n    @staticmethod\n    def f():\n"
                    "        global value\n        " + statement + "\n"
                )
                destination = "value = 2\nclass B:\n    pass\n"
                self.mod1.write(source)
                self.mod2.write(destination)
                with self.assertRaises(exceptions.RefactoringError):
                    move.MoveMethod.get_class_changes(
                        self.project,
                        [(self.mod1, source.index("def f") + 4, "f")],
                        self.mod2,
                        destination.index("class B") + 6,
                        resources=[self.mod1, self.mod2],
                    )
                self.assertEqual(source, self.mod1.read())
                self.assertEqual(destination, self.mod2.read())

    def test_transfer_rejects_definition_time_changes(self):
        declarations = [
            "@staticmethod\n    def f(x=values[0]):",
            "@staticmethod if values[0] else classmethod\n    def f(x):",
        ]
        if sys.version_info < (3, 14):
            # Python 3.14+ evaluates annotations lazily on access, in the same
            # module globals before and after the move, so only eager
            # annotations change with the definition time.
            declarations.append("@staticmethod\n    def f(x: values[0]):")
        for declaration in declarations:
            with self.subTest(declaration=declaration):
                source = (
                    "values = [1]\nclass A:\n    " + declaration
                    + "\n        return x\nvalues[0] = 2\nclass B:\n    pass\n"
                )
                self.mod1.write(source)
                with self.assertRaises(exceptions.RefactoringError):
                    move.MoveMethod.get_class_changes(
                        self.project,
                        [(self.mod1, source.index("def f") + 4, "f")],
                        self.mod1,
                        source.index("class B") + 6,
                        resources=[self.mod1],
                    )
                self.assertEqual(source, self.mod1.read())

    @unittest.skipIf(
        sys.version_info < (3, 14), "lazy function annotations require Python 3.14"
    )
    def test_transfer_keeps_lazy_annotations(self):
        source = (
            "values = [1]\nclass A:\n    @staticmethod\n    def f(x: values[0]):\n"
            "        return x\nvalues[0] = 2\nclass B:\n    pass\n"
        )
        self.mod1.write(source)
        original = {}
        exec(source, original)
        self.project.do(
            move.MoveMethod.get_class_changes(
                self.project,
                [(self.mod1, source.index("def f") + 4, "f")],
                self.mod1,
                source.index("class B") + 6,
                resources=[self.mod1],
            )
        )
        moved = {}
        exec(self.mod1.read(), moved)
        self.assertEqual(
            original["A"].f.__annotations__, moved["B"].f.__annotations__
        )

    def test_transfer_rejects_early_same_module_references(self):
        for early in ("result = A.f()", "class C:\n    result = A.f()"):
            with self.subTest(early=early):
                source = (
                    "class A:\n    @staticmethod\n    def f():\n        return 1\n"
                    + early + "\nclass B:\n    pass\n"
                )
                self.mod1.write(source)
                original = {}
                exec(source, original)
                with self.assertRaises(exceptions.RefactoringError):
                    move.MoveMethod.get_class_changes(
                        self.project,
                        [(self.mod1, source.index("def f") + 4, "f")],
                        self.mod1,
                        source.index("class B") + 6,
                        resources=[self.mod1],
                    )
                self.assertEqual(source, self.mod1.read())

    def test_transfer_rejects_descriptor_mutation_during_class_execution(self):
        for statement in (
            "globals()['staticmethod'] = lambda f: 42",
            "globals()['classmethod'] = lambda f: 42",
        ):
            with self.subTest(statement=statement):
                descriptor = "classmethod" if "classmethod" in statement else "staticmethod"
                source = (
                    "class Owner:\n    class Helpers:\n        @" + descriptor
                    + "\n        def f(x=None):\n            return x\n    "
                    + statement + "\n"
                )
                self.mod1.write(source)
                original = {}
                exec(source, original)
                with self.assertRaises(exceptions.RefactoringError):
                    move.MoveMethod.get_class_changes(
                        self.project,
                        [(self.mod1, source.index("def f") + 4, "f")],
                        self.mod1,
                        source.index("class Owner") + 6,
                        resources=[self.mod1],
                    )
                self.assertEqual(source, self.mod1.read())

    def test_transfer_rejects_destination_metaclass_effects(self):
        for meta in (
            "    @classmethod\n    def __prepare__(cls, name, bases):\n"
            "        return {'staticmethod': lambda f: 42}\n",
            "    def __new__(cls, name, bases, namespace):\n"
            "        namespace['observed'] = 'f' in namespace\n"
            "        return super().__new__(cls, name, bases, namespace)\n",
        ):
            with self.subTest(meta=meta):
                source = (
                    "class Meta(type):\n" + meta
                    + "class Owner(metaclass=Meta):\n    class Helpers:\n"
                    "        @staticmethod\n        def f():\n            return 1\n"
                )
                self.mod1.write(source)
                original = {}
                exec(source, original)
                self.assertEqual(1, original["Owner"].Helpers.f())
                if "__new__" in meta:
                    self.assertFalse(original["Owner"].observed)
                with self.assertRaises(exceptions.RefactoringError):
                    move.MoveMethod.get_class_changes(
                        self.project,
                        [(self.mod1, source.index("def f") + 4, "f")],
                        self.mod1,
                        source.index("class Owner") + 6,
                        resources=[self.mod1],
                    )
                self.assertEqual(source, self.mod1.read())

    def test_transfer_rejects_cross_module_descriptor_mutation(self):
        for descriptor in ("staticmethod", "classmethod"):
            with self.subTest(descriptor=descriptor):
                source = (
                    "class A:\n    @" + descriptor
                    + "\n    def f(x=None):\n        return 1\n"
                )
                destination = (
                    "globals()['" + descriptor + "'] = lambda f: 42\n"
                    "class B:\n    pass\n"
                )
                self.mod1.write(source)
                self.mod2.write(destination)
                original = {}
                exec(source, original)
                self.assertEqual(1, original["A"].f())
                with self.assertRaises(exceptions.RefactoringError):
                    move.MoveMethod.get_class_changes(
                        self.project,
                        [(self.mod1, source.index("def f") + 4, "f")],
                        self.mod2,
                        destination.index("class B") + 6,
                        resources=[self.mod1, self.mod2],
                    )
                self.assertEqual(source, self.mod1.read())
                self.assertEqual(destination, self.mod2.read())

    def test_move_constant(self) -> None:
        self.origin_module.write("foo = 123\n")
        self._move(self.origin_module, self.origin_module.read().index("foo") + 1, self.destination_module)
        self.assertEqual("", self.origin_module.read())
        self.assertEqual("foo = 123\n", self.destination_module.read())

    def test_move_constant_preserves_used_module_alias(self) -> None:
        self.project.prefs["prefer_module_from_imports"] = True
        self.mod4.write(dedent("""\
            def keep():
                return 1

            value = 2
        """))
        self.mod5.write(dedent("""\
            def existing():
                return 3
        """))
        self.mod3.write(dedent("""\
            from pkg import mod5
            from pkg import mod4 as utils_module

            def run():
                return mod5.existing(), utils_module.keep(), utils_module.value
        """))
        self._move(self.mod4, self.mod4.read().index("value"), self.mod5)
        self.assertEqual(
            dedent("""\
                from pkg import mod5
                from pkg import mod4 as utils_module

                def run():
                    return mod5.existing(), utils_module.keep(), mod5.value
            """),
            self.mod3.read(),
        )
        self.assertEqual(dedent("""\
            def keep():
                return 1

        """), self.mod4.read())
        self.assertIn(dedent("""\
            value = 2
        """), self.mod5.read())

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
            r"Move refactoring should be performed on a global class, function or variable\.",
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
            r"Moving global elements to the same module\.",
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

    def test_moving_global_replaces_relative_from_imports_in_consumers(self) -> None:
        """A relative from-import of the moved name is rewritten like an absolute one"""
        self.origin_module_in_pkg.write("class AClass:\n    pass\n")
        self.mod4.write("from .origin_module_in_pkg import AClass\na_var = AClass()\n")
        self._move(self.origin_module_in_pkg, 6, self.destination_module_in_pkg)
        self.assertEqual(
            "import pkg.destination_module_in_pkg\n"
            "a_var = pkg.destination_module_in_pkg.AClass()\n",
            self.mod4.read(),
        )

    def test_moving_global_replaces_relative_package_imports_in_consumers(self) -> None:
        """A relative import of the source module is rewritten to the destination"""
        self.origin_module_in_pkg.write("class AClass:\n    pass\n")
        self.mod4.write(
            "from . import origin_module_in_pkg\n"
            "a_var = origin_module_in_pkg.AClass()\n"
        )
        self._move(self.origin_module_in_pkg, 6, self.destination_module_in_pkg)
        self.assertEqual(
            "import pkg.destination_module_in_pkg\n"
            "a_var = pkg.destination_module_in_pkg.AClass()\n",
            self.mod4.read(),
        )

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

    def test_moving_module_referenced_by_relative_import(self) -> None:
        self.mod4.write(dedent("""\
            from .mod5 import a
            print(a)
        """))
        self.mod5.write("a = 1\n")
        self._move(self.mod5, None, self.destination_pkg_root)
        expected = dedent("""\
            from destination_pkg_root.mod5 import a
            print(a)
        """)
        self.assertEqual(expected, self.mod4.read())

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

    def _transfer_static_method(self, body: str) -> None:
        self.origin_module.write(
            dedent(
                """\
                __all__ = ["Legacy"]
                TOKEN = "source value"

                class Legacy:
                    @staticmethod
                    def execute():
                """
            )
            + "        "
            + body
            + "\n"
        )
        self.destination_module.write("class Target:\n    pass\n")
        changes = move.MoveMethod.get_class_changes(
            self.project,
            [
                (
                    self.origin_module,
                    self.origin_module.read().index("execute"),
                    "execute",
                )
            ],
            self.destination_module,
            self.destination_module.read().index("Target"),
        )
        self.project.do(changes)

    def test_transfer_does_not_import_unused_export_metadata(self) -> None:
        self._transfer_static_method("return TOKEN")

        self.assertIn("from origin_module import TOKEN", self.destination_module.read())
        self.assertNotIn("from origin_module import __all__", self.destination_module.read())
        self.assertIn('__all__ = ["Legacy"]', self.origin_module.read())

    def test_transfer_imports_export_metadata_when_method_uses_it(self) -> None:
        self._transfer_static_method("return __all__")

        self.assertIn("from origin_module import __all__", self.destination_module.read())

    def test_transfer_preserves_future_annotations_without_origin_exports(self) -> None:
        self.origin_module.write(
            "from __future__ import annotations\n"
            "__all__ = ['Legacy']\n"
            "class Legacy:\n"
            "    @staticmethod\n"
            "    def execute(value: float) -> int:\n"
            "        return int(value)\n"
        )
        self.destination_module.write("__all__ = ['Target']\nclass Target:\n    pass\n")
        changes = move.MoveMethod.get_class_changes(
            self.project,
            [(self.origin_module, self.origin_module.read().index("execute"), "execute")],
            self.destination_module,
            self.destination_module.read().index("Target", self.destination_module.read().index("class ")),
        )
        self.project.do(changes)
        target = runpy.run_path(self.destination_module.real_path)["Target"]
        self.assertEqual(3, target.execute(3.7))
        self.assertEqual({"value": "float", "return": "int"}, target.execute.__annotations__)
        self.assertNotIn("from origin_module import __all__", self.destination_module.read())

    def test_moving_export_metadata_preserves_its_named_declarations(self) -> None:
        self.origin_module.write("class Exported:\n    pass\n__all__ = ['Exported']\n")
        self._move(
            self.origin_module,
            self.origin_module.read().index("__all__"),
            self.destination_module,
        )
        source = self.project.get_pymodule(self.origin_module)
        destination = self.project.get_pymodule(self.destination_module)
        self.assertIs(
            source.get_attribute("Exported").get_object(),
            destination.get_attribute("Exported").get_object(),
        )
        self.assertIn("__all__ = ['Exported']", self.destination_module.read())

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
