from __future__ import annotations

import importlib
import sys
import unittest
from textwrap import dedent

from rope.base import exceptions
from rope.refactor import move
from ropetest import testutils


class InstanceMethodTransferTest(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.project = testutils.sample_project()
        self.handlers = testutils.create_module(self.project, "handlers")
        self.source = testutils.create_module(self.project, "source")
        self.destination = testutils.create_module(self.project, "destination")
        self.handlers.write(
            dedent("""\
                class Handlers:
                    @staticmethod
                    def handler(command):
                        def decorate(func):
                            if hasattr(func, "_handler_config"):
                                raise ValueError("duplicate")
                            setattr(func, "_handler_config", command)
                            return func
                        return decorate

                h = Handlers
            """)
        )
        self.destination.write(
            dedent("""\
                class Target:
                    queue_service: object
            """)
        )

    def tearDown(self) -> None:
        testutils.remove_project(self.project)
        super().tearDown()

    def _move(self):
        source = dedent("""\
            from handlers import h

            class Legacy:
                @h.handler(command=int)
                def execute(self, request):
                    return self.queue.execute(request)
        """)
        self.source.write(source)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        self.assertIsInstance(operation, move.MoveMethod)
        changes = operation.get_instance_class_changes(
            self.project,
            [(self.source, source.index("execute(self") + 1, "execute")],
            self.destination,
            self.destination.read().index("Target") + 1,
            receiver_rewrites={"queue": "queue_service.queue"},
            resources=[self.handlers, self.source, self.destination],
        )
        self.project.do(changes)

    def _load_runtime_module(self, name: str):
        module_names = ("handlers", name)
        prior = {module: sys.modules.pop(module, None) for module in module_names}
        sys.path.insert(0, self.project.address)
        try:
            return importlib.import_module(name)
        finally:
            sys.path.remove(self.project.address)
            for module, previous in prior.items():
                sys.modules.pop(module, None)
                if previous is not None:
                    sys.modules[module] = previous

    def test_transfers_handler_with_port_rewrite_without_forwarding(self) -> None:
        self._move()
        self.assertNotIn("def execute", self.source.read())
        self.assertIn("@h.handler(command=int)", self.destination.read())
        self.assertIn(
            "self.queue_service.queue.execute(request)", self.destination.read()
        )
        self.assertNotIn("return self.", self.source.read())
        destination = self._load_runtime_module("destination")
        self.assertIs(destination.Target.execute._handler_config, int)

        class Queue:
            @staticmethod
            def execute(request):
                return request + 1

        class QueuePort:
            queue = Queue()

        target = destination.Target()
        target.queue_service = QueuePort()
        self.assertEqual(target.execute(4), 5)

    def test_same_module_transfer_keeps_local_dependencies_without_self_import(
        self,
    ) -> None:
        source = dedent("""\
            def handler(command):
                def decorate(func):
                    setattr(func, "_handler_config", command)
                    return func
                return decorate

            class Target:
                queue_service: object

            class Legacy:
                @handler(command=int)
                def execute(self, request):
                    return self.queue.execute(request)
        """)
        self.source.write(source)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        changes = operation.get_instance_class_changes(
            self.project,
            [(self.source, source.index("execute(self") + 1, "execute")],
            self.source,
            source.index("Target") + 1,
            receiver_rewrites={"queue": "queue_service.queue"},
            resources=[self.source],
        )
        self.project.do(changes)
        self.assertNotIn("import", self.source.read())
        module = self._load_runtime_module("source")
        self.assertIs(module.Target.execute._handler_config, int)

    def test_same_module_transfer_from_function_local_class(self) -> None:
        source = dedent("""\
            from handlers import h

            class Target:
                queue_service: object

            def build():
                class Legacy:
                    @h.handler(command=int)
                    def execute(self, request):
                        return self.queue.execute(request)
                return Legacy
        """)
        self.source.write(source)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        changes = operation.get_instance_class_changes(
            self.project,
            [(self.source, source.index("execute(self") + 1, "execute")],
            self.source,
            source.index("Target") + 1,
            receiver_rewrites={"queue": "queue_service.queue"},
            resources=[self.handlers, self.source],
        )
        self.project.do(changes)
        module = self._load_runtime_module("source")
        self.assertIs(module.Target.execute._handler_config, int)
        self.assertFalse(hasattr(module.build(), "execute"))

    def test_transfer_applies_the_requested_method_name(self) -> None:
        source = dedent("""\
            from handlers import h

            class Legacy:
                @h.handler(command=int)
                def execute(self, request):
                    return self.queue.execute(request)
        """)
        self.source.write(source)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        changes = operation.get_instance_class_changes(
            self.project,
            [(self.source, source.index("execute(self") + 1, "run")],
            self.destination,
            self.destination.read().index("Target") + 1,
            receiver_rewrites={"queue": "queue_service.queue"},
            resources=[self.handlers, self.source, self.destination],
        )
        self.project.do(changes)
        destination = self._load_runtime_module("destination")
        self.assertIs(destination.Target.run._handler_config, int)
        self.assertFalse(hasattr(destination.Target, "execute"))

    def test_refuses_method_private_name_mangling_after_runtime_proof(self) -> None:
        source = dedent("""\
            from handlers import h

            class Legacy:
                def __init__(self):
                    self.__secret = "preserved"

                @h.handler(command=int)
                def execute(self, request):
                    return self.__secret
        """)
        self.source.write(source)
        legacy = self._load_runtime_module("source").Legacy
        self.assertEqual(legacy().execute(1), "preserved")
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "Private identifier changes"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={},
                resources=[self.handlers, self.source, self.destination],
            )

    def test_refuses_decorator_private_binding_after_runtime_proof(self) -> None:
        source = dedent("""\
            from handlers import h

            class Legacy:
                __Command = int

                @h.handler(command=__Command)
                def execute(self, request):
                    return request
        """)
        self.destination.write(
            self.destination.read().replace(
                "class Target:\n    queue_service: object",
                "class Target:\n    __Command = str\n    queue_service: object",
            )
        )
        self.source.write(source)
        legacy = self._load_runtime_module("source").Legacy
        self.assertIs(legacy.execute._handler_config, int)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "Private identifier changes"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={},
                resources=[self.handlers, self.source, self.destination],
            )

    def test_refuses_annotation_private_binding_after_runtime_proof(self) -> None:
        source = dedent("""\
            from handlers import h

            class Legacy:
                __Request = int

                @h.handler(command=int)
                def execute(self, request: __Request):
                    return request
        """)
        self.destination.write(
            self.destination.read().replace(
                "class Target:\n    queue_service: object",
                "class Target:\n    __Request = str\n    queue_service: object",
            )
        )
        self.source.write(source)
        legacy = self._load_runtime_module("source").Legacy
        self.assertIs(legacy.execute.__annotations__["request"], int)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "Private identifier changes"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={},
                resources=[self.handlers, self.source, self.destination],
            )

    def test_refuses_class_scope_default_and_annotation_binding_changes(self) -> None:
        source = dedent("""\
            from handlers import h

            class Legacy:
                TYPE = int
                DEFAULT = 7

                @h.handler(command=int)
                def execute(self, request: TYPE = DEFAULT):
                    return request
        """)
        self.destination.write(
            dedent("""\
                class Target:
                    TYPE = str
                    DEFAULT = "destination"
                    queue_service: object
            """)
        )
        naive = testutils.create_module(self.project, "naive")
        naive.write(
            dedent("""\
                from handlers import h

                class Target:
                    TYPE = str
                    DEFAULT = "destination"

                    @h.handler(command=int)
                    def execute(self, request: TYPE = DEFAULT):
                        return request
            """)
        )
        self.source.write(source)
        legacy = self._load_runtime_module("source").Legacy
        naive_target = self._load_runtime_module("naive").Target
        self.assertEqual(legacy.execute.__defaults__, (7,))
        self.assertIs(legacy.execute.__annotations__["request"], int)
        self.assertEqual(naive_target.execute.__defaults__, ("destination",))
        self.assertIs(naive_target.execute.__annotations__["request"], str)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "signature binding changed"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={},
                resources=[self.handlers, self.source, self.destination],
            )

    def test_refuses_custom_descriptor_default_after_runtime_proof(self) -> None:
        self.handlers.write(
            self.handlers.read()
            + dedent("""\
                class Descriptor:
                    def __init__(self):
                        self.reads = 0
                    def __get__(self, instance, owner):
                        self.reads += 1
                        return self.reads
                class Settings:
                    value = Descriptor()
            """)
        )
        source = dedent("""\
            from handlers import h, Settings
            class Legacy:
                @h.handler(command=int)
                def execute(self, request=Settings.value):
                    return request
        """)
        self.source.write(source)
        legacy = self._load_runtime_module("source").Legacy
        self.assertEqual(legacy.execute.__defaults__, (1,))
        original_destination = self.destination.read()
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "attribute may invoke descriptor behavior"
        ):
            move.MoveMethod.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={},
                resources=[self.handlers, self.source, self.destination],
            )
        self.assertEqual(self.source.read(), source)
        self.assertEqual(self.destination.read(), original_destination)

    def test_refuses_decorator_that_wraps_the_method(self) -> None:
        self.handlers.write(
            dedent("""\
                class Handlers:
                    @staticmethod
                    def handler(command):
                        def decorate(func):
                            def wrapped(self, request):
                                return func(self, request)
                            return wrapped
                        return decorate

                h = Handlers
            """)
        )
        source = dedent("""\
            from handlers import h

            class Legacy:
                @h.handler(command=int)
                def execute(self, request):
                    return self.queue.execute(request)
        """)
        self.source.write(source)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "original method"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={"queue": "queue_service.queue"},
                resources=[self.handlers, self.source, self.destination],
            )

    def test_refuses_identity_decorator_with_conditional_return(self) -> None:
        self.handlers.write(
            dedent("""\
                class Handlers:
                    @staticmethod
                    def handler(command):
                        def decorate(func):
                            if hasattr(func, "_handler_config"):
                                raise ValueError("duplicate")
                            setattr(func, "_handler_config", command)
                            if command is int:
                                return func
                        return decorate

                h = Handlers
            """)
        )
        source = dedent("""\
            from handlers import h

            class Legacy:
                @h.handler(command=int)
                def execute(self, request):
                    return request
        """)
        self.source.write(source)
        legacy = self._load_runtime_module("source").Legacy
        self.assertEqual(legacy().execute(4), 4)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "explicit return"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={},
                resources=[self.handlers, self.source, self.destination],
            )

    def test_refuses_identity_decorator_with_unproven_helper(self) -> None:
        self.handlers.write(
            dedent("""\
                def add_metadata(func, command):
                    setattr(func, "_handler_config", command)

                class Handlers:
                    @staticmethod
                    def handler(command):
                        def decorate(func):
                            add_metadata(func, command)
                            return func
                        return decorate

                h = Handlers
            """)
        )
        source = dedent("""\
            from handlers import h

            class Legacy:
                @h.handler(command=int)
                def execute(self, request):
                    return request
        """)
        self.source.write(source)
        legacy = self._load_runtime_module("source").Legacy
        self.assertEqual(legacy().execute(4), 4)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "Identity decorator"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={},
                resources=[self.handlers, self.source, self.destination],
            )

    def test_refuses_same_named_local_metadata_constructor_with_runtime_effect(self) -> None:
        self.handlers.write(
            dedent("""\
                class DecoratorConfig:
                    def __init__(self, func, command):
                        if func.__qualname__.startswith("Target."):
                            func.__code__ = (
                                lambda self, request: "changed"
                            ).__code__
                        self.command = command

                class Handlers:
                    @staticmethod
                    def handler(command):
                        def decorate(func):
                            settings = DecoratorConfig(func, command)
                            setattr(func, "_handler_config", settings.command)
                            return func
                        return decorate

                h = Handlers
            """)
        )
        source = dedent("""\
            from handlers import h

            class Legacy:
                @h.handler(command=int)
                def execute(self, request):
                    return request
        """)
        naive = testutils.create_module(self.project, "naive")
        naive.write(
            dedent("""\
                from handlers import h

                class Target:
                    @h.handler(command=int)
                    def execute(self, request):
                        return request
            """)
        )
        self.source.write(source)
        legacy = self._load_runtime_module("source").Legacy
        target = self._load_runtime_module("naive").Target
        self.assertEqual(legacy().execute(4), 4)
        self.assertEqual(target().execute(4), "changed")
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "canonical source identity"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={},
                resources=[self.handlers, self.source, self.destination],
            )

    def test_refuses_decorator_argument_with_caller_dependent_effect(self) -> None:
        self.handlers.write(
            dedent("""\
                import inspect

                def choose():
                    caller = inspect.currentframe().f_back.f_globals["__name__"]
                    return int if caller == "source" else str

                class Handlers:
                    @staticmethod
                    def handler(command):
                        def decorate(func):
                            setattr(func, "_handler_config", command)
                            return func
                        return decorate

                h = Handlers
            """)
        )
        source = dedent("""\
            from handlers import choose, h

            class Legacy:
                @h.handler(command=choose())
                def execute(self, request):
                    return request
        """)
        naive = testutils.create_module(self.project, "naive")
        naive.write(
            dedent("""\
                from handlers import choose, h

                class Target:
                    @h.handler(command=choose())
                    def execute(self, request):
                        return request
            """)
        )
        self.source.write(source)
        legacy = self._load_runtime_module("source").Legacy
        target = self._load_runtime_module("naive").Target
        self.assertIs(legacy.execute._handler_config, int)
        self.assertIs(target.execute._handler_config, str)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "handler decorator.*effects"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={},
                resources=[self.handlers, self.source, self.destination],
            )

    def test_refuses_decorator_attribute_with_custom_getattribute_effect(self) -> None:
        self.handlers.write(
            dedent("""\
                import inspect

                class DynamicMeta(type):
                    def __getattribute__(cls, name):
                        if name == "command":
                            caller = inspect.currentframe().f_back.f_globals["__name__"]
                            return int if caller == "source" else str
                        return super().__getattribute__(name)

                class Selector(metaclass=DynamicMeta):
                    command = int

                class Handlers:
                    @staticmethod
                    def handler(command):
                        def decorate(func):
                            setattr(func, "_handler_config", command)
                            return func
                        return decorate

                h = Handlers
            """)
        )
        source = dedent("""\
            from handlers import Selector, h

            class Legacy:
                @h.handler(command=Selector.command)
                def execute(self, request):
                    return request
        """)
        naive = testutils.create_module(self.project, "naive")
        naive.write(
            dedent("""\
                from handlers import Selector, h

                class Target:
                    @h.handler(command=Selector.command)
                    def execute(self, request):
                        return request
            """)
        )
        self.source.write(source)
        legacy = self._load_runtime_module("source").Legacy
        target = self._load_runtime_module("naive").Target
        self.assertIs(legacy.execute._handler_config, int)
        self.assertIs(target.execute._handler_config, str)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "native __getattribute__"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={},
                resources=[self.handlers, self.source, self.destination],
            )

    def test_refuses_future_annotations_policy_change_after_runtime_proof(self) -> None:
        source = dedent("""\
            from handlers import h

            class Legacy:
                TYPE = int

                @h.handler(command=int)
                def execute(self, request: TYPE):
                    return request
        """)
        self.destination.write(
            dedent("""\
                from __future__ import annotations

                class Target:
                    TYPE = str
                    queue_service: object
            """)
        )
        naive = testutils.create_module(self.project, "naive")
        naive.write(
            dedent("""\
                from __future__ import annotations
                from handlers import h

                class Target:
                    TYPE = str

                    @h.handler(command=int)
                    def execute(self, request: TYPE):
                        return request
            """)
        )
        self.source.write(source)
        legacy = self._load_runtime_module("source").Legacy
        naive_target = self._load_runtime_module("naive").Target
        self.assertIs(legacy.execute.__annotations__["request"], int)
        self.assertEqual(naive_target.execute.__annotations__["request"], "TYPE")
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "future policy changes"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={},
                resources=[self.handlers, self.source, self.destination],
            )

    def test_refuses_unmapped_receiver_before_planning_changes(self) -> None:
        source = dedent("""\
            from handlers import h

            class Legacy:
                @h.handler(command=int)
                def execute(self, request):
                    return self.queue.execute(self.other, request)
        """)
        self.source.write(source)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "no declared port mapping"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={"queue": "queue_service.queue"},
                resources=[self.handlers, self.source, self.destination],
            )

    def test_refuses_external_method_references(self) -> None:
        source = dedent("""\
            from handlers import h

            class Legacy:
                @h.handler(command=int)
                def execute(self, request):
                    return self.queue.execute(request)

            operation = Legacy().execute(1)
        """)
        caller = testutils.create_module(self.project, "caller")
        caller.write("from source import Legacy\nvalue = Legacy().execute(1)\n")
        self.source.write(source)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "external method reference"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={"queue": "queue_service.queue"},
                resources=[
                    self.handlers,
                    self.source,
                    self.destination,
                    caller,
                ],
            )

    def test_refuses_decorator_binding_changed_by_destination_class(self) -> None:
        source = dedent("""\
            from handlers import h

            class Legacy:
                COMMAND = int

                @h.handler(command=COMMAND)
                def execute(self, request):
                    return self.queue.execute(request)
        """)
        self.destination.write(
            self.destination.read().replace(
                "class Target:\n    queue_service: object",
                "class Target:\n    COMMAND = str\n    queue_service: object",
            )
        )
        self.source.write(source)
        operation = move.create_move(
            self.project, self.source, source.index("execute(self") + 1
        )
        with self.assertRaisesRegex(
            exceptions.RefactoringError, "decorator binding changed"
        ):
            operation.get_instance_class_changes(
                self.project,
                [(self.source, source.index("execute(self") + 1, "execute")],
                self.destination,
                self.destination.read().index("Target") + 1,
                receiver_rewrites={"queue": "queue_service.queue"},
                resources=[self.handlers, self.source, self.destination],
            )


if __name__ == "__main__":
    unittest.main()
