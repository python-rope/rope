"""Public signature refactoring preserves modern Python source contracts."""

import inspect
import os
import subprocess
import sys
from textwrap import dedent

import pytest

from rope.base.exceptions import RefactoringError
from rope.base.project import Project
from rope.refactor.change_signature import ArgumentAdder, ChangeSignature


@pytest.mark.parametrize("foreign", [False, True])
def test_sequence_hint_preserves_target_flow_to_unedited_consumer(tmp_path, foreign):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        dependency = project.root.create_file('signature_consumer.py')
        dependency.write('def invoke(items):\n    return items[0].run(7)\n')
        resource = project.root.create_file('sample.py')
        selected = 'Other' if foreign else 'Runner'
        resource.write(
            'from collections.abc import Sequence\n'
            'from signature_consumer import invoke\n'
            'class Runner:\n    def run(self, value: int):\n        return value\n'
            'class Other:\n    def run(self, value: int):\n        return value + 4\n'
            + f'def public_api(items: Sequence[{selected}]):\n    return invoke(items)\n'
            + f'print(public_api([{selected}()]))\n'
            + 'answer = Runner().run(3)\n'
        )
        before = resource.read()
        original = subprocess.run([sys.executable, resource.real_path], capture_output=True, text=True, check=True)
        assert original.stdout.strip() == ('11' if foreign else '7')
        operation = ChangeSignature(project, resource, before.index('run'))
        addition = ArgumentAdder(0, 'token', value="'received'", keyword_only=True)
        if foreign:
            project.do(operation.get_changes([addition], resources=[resource]))
            actual = subprocess.run([sys.executable, resource.real_path], capture_output=True, text=True, check=True)
            assert actual.stdout == original.stdout
        else:
            with pytest.raises(RefactoringError, match='Target namespace escapes'):
                operation.get_changes([addition], resources=[resource])
            assert resource.read() == before
        assert dependency.read() == 'def invoke(items):\n    return items[0].run(7)\n'
    finally:
        project.close()


@pytest.mark.parametrize(
    "source, entry",
    [
        (
            "import importlib\nanswer = importlib.import_module('target').run(7)\n",
            "consumer.answer",
        ),
        (
            "import importlib\ndef invoke():\n"
            "    return importlib.import_module('target').run(7)\nanswer = invoke()\n",
            "consumer.answer",
        ),
        (
            "answer = __import__('target').__dict__['run'](7)\n",
            "consumer.answer",
        ),
        (
            "def invoke(callback):\n    return callback(__import__('target'))\n",
            "consumer.invoke(lambda namespace: namespace.run(7))",
        ),
    ],
)
def test_required_keyword_retains_dynamic_consumers_outside_import_component(
    tmp_path, source, entry
):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        target = project.root.create_file("target.py")
        target.write("def run(value):\n    return value\n")
        consumer = project.root.create_file("consumer.py")
        consumer.write(source)
        executed = subprocess.run(
            [sys.executable, "-c", f"import consumer; print({entry})"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )
        assert executed.stdout.strip() == "7"
        before = target.read(), consumer.read()
        with pytest.raises(RefactoringError, match="Unresolved"):
            ChangeSignature(project, target, target.read().index("run")).get_changes(
                [ArgumentAdder(0, "token", value="'received'", keyword_only=True)],
                resources=[target, consumer],
            )
        assert (target.read(), consumer.read()) == before
    finally:
        project.close()


@pytest.mark.parametrize(
    "header,call",
    [
        ("def run(value: int, /, *, label: str = 'old') -> int:", "run(7, label='ok')"),
        ("def run(value: int, **options: str) -> int:", "run(7, label='ok')"),
        ("def run(value: int) -> int:", "run(\n    7,  # keep this comment\n)"),
        ("def run(value: int) -> int:", "int(f'{run(7)}')"),
        ("def run(value: int, /, *, café: str = 'ação', **options: str) -> int:", "run(7, café='résumé')"),
        ("def run(value: int, *rest: str, label: str = 'old') -> int:", "run(7, 'extra', label='ok')"),
        ("def run(\n    value: int,  # retained parameter comment\n    /,\n    *,\n    label: str = 'old',\n) -> int:", "run(7, label='ok')"),
    ],
)
def test_required_keyword_preserves_existing_runtime_contract(tmp_path, header, call):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(header + "\n    return value\n\nanswer = " + call + "\n")
        refactoring = ChangeSignature(project, resource, resource.read().index("run"))
        addition = ArgumentAdder(0, "token", value="'received'", keyword_only=True, annotation="str")
        project.do(refactoring.get_changes([addition]))
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["answer"] == 7
        signature = inspect.signature(namespace["run"])
        assert signature.parameters["token"].kind is inspect.Parameter.KEYWORD_ONLY
        assert signature.parameters["token"].annotation is str
        assert signature.parameters["value"].annotation is int
        assert signature.return_annotation is int
        with pytest.raises(TypeError, match="token"):
            namespace["run"](7)
        assert not ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]).changes
    finally:
        project.close()


@pytest.mark.parametrize(
    "value", ["'received'", "dict(label='received')['label']", "'re' + 'ceived'"]
)
def test_required_keyword_value_inside_fstring_is_written_legally(tmp_path, value):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "def run(value):\n    return value, token\n\nanswer = f'{run(7)}'\n"
        )
        addition = ArgumentAdder(0, "token", value=value, keyword_only=True)
        project.do(
            ChangeSignature(project, resource, resource.read().index("run")).get_changes(
                [addition]
            )
        )
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["answer"] == "(7, 'received')"
    finally:
        project.close()


def test_required_keyword_value_is_resolved_for_each_native_caller(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            dedent(
                '''\
                def run(value: int) -> tuple[int, str]:
                    return value, token

                class Calls:
                    def direct(self):
                        dblink = "direct"
                        return run(7)

                    def planned(self):
                        return run(8)

                    def link(self):
                        return "planned"

                direct = Calls().direct()
                planned = Calls().planned()
                '''
            )
        )
        values = {"direct": "dblink", "planned": "self.link()"}
        callers = []

        def call_value(pymodule, occurrence):
            scope = pymodule.get_scope().get_inner_scope_for_line(occurrence.lineno)
            while scope.parent is not None:
                name = scope.pyobject.get_name()
                if name in values:
                    callers.append(name)
                    return values[name]
                scope = scope.parent
            raise AssertionError("No declared caller for keyword addition")

        addition = ArgumentAdder(
            0, "token", value=call_value, keyword_only=True, annotation="str"
        )
        project.do(
            ChangeSignature(project, resource, resource.read().index("run")).get_changes(
                [addition]
            )
        )
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["direct"] == (7, "direct")
        assert namespace["planned"] == (8, "planned")
        assert sorted(callers) == ["direct", "planned"]
        assert not ChangeSignature(
            project, resource, resource.read().index("run")
        ).get_changes([addition]).changes
    finally:
        project.close()


def test_ambiguous_keyword_expansion_refuses_the_unpublished_change(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("def run(*, value: int) -> int:\n    return value\n\nrun(**options)\n")
        before = resource.read()
        with pytest.raises(RefactoringError, match="expansion"):
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(0, "token", value="'received'", keyword_only=True, annotation="str")
            ])
        assert resource.read() == before
    finally:
        project.close()


@pytest.mark.parametrize(
    "usage",
    ["callback = run", "from functools import partial\ncallback = partial(run, 7)"],
)
def test_escaped_function_refuses_the_unpublished_change(tmp_path, usage):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("def run(value: int) -> int:\n    return value\n\n" + usage + "\n")
        before = resource.read()
        with pytest.raises(RefactoringError, match="non-call"):
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(0, "token", value="'received'", keyword_only=True, annotation="str")
            ])
        assert resource.read() == before
    finally:
        project.close()


@pytest.mark.parametrize("name", ["'run'", "selected_name"])
@pytest.mark.parametrize("getter", ["getattr", "resolve"])
def test_reflective_method_refuses_the_unpublished_change(tmp_path, name, getter):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            ("from builtins import getattr as resolve\n" if getter == "resolve" else "")
            + "class Runner:\n    @staticmethod\n    def run(value: int) -> int:\n        return value\n\n"
            + "answer = " + getter + "(Runner, " + name + ")(7)\n"
        )
        before = resource.read()
        with pytest.raises(RefactoringError, match="signature consumer") as failure:
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(0, "token", value="'received'", keyword_only=True, annotation="str")
            ])
        assert isinstance(failure.value.__cause__, RefactoringError)
        assert ".py:" in str(failure.value)
        assert resource.read() == before
    finally:
        project.close()


def test_decorated_method_and_foreign_binding_keep_their_runtime_contract(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "class Runner:\n    @classmethod\n    def run(cls, value: int, /, *, label: str = 'old') -> int:\n"
            "        return value\n\n"
            "def foreign():\n    def run(value: int) -> int:\n        return value + 1\n    return run(3)\n\n"
            "answer = Runner.run(7)\nother = foreign()\n"
        )
        project.do(ChangeSignature(project, resource, resource.read().index("run")).get_changes([
            ArgumentAdder(0, "token", value="'received'", keyword_only=True, annotation="str")
        ]))
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["answer"] == 7
        assert namespace["other"] == 4
        assert inspect.signature(namespace["Runner"].run).parameters["token"].kind is inspect.Parameter.KEYWORD_ONLY
    finally:
        project.close()


def test_required_constructor_keyword_preserves_native_instantiation(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "class Builder:\n"
            "    def __init__(self, value: int):\n"
            "        self.value = value\n"
            "        self.token = token\n\n"
            "answer = Builder(7)\n"
        )
        addition = ArgumentAdder(
            0, "token", value="'received'", keyword_only=True, annotation="str"
        )
        project.do(
            ChangeSignature(
                project, resource, resource.read().index("Builder")
            ).get_changes([addition])
        )
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["answer"].value == 7
        assert namespace["answer"].token == "received"
        assert not ChangeSignature(
            project, resource, resource.read().index("Builder")
        ).get_changes([addition]).changes
    finally:
        project.close()


@pytest.mark.parametrize(
    "usage",
    [
        "Factory = Builder\nanswer = Factory(7)",
        "def create(factory):\n    return factory(7)\nanswer = create(Builder)",
        "class Child(Builder):\n    pass\nanswer = Child(7)",
    ],
)
def test_required_constructor_keyword_refuses_escaped_class(tmp_path, usage):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "class Builder:\n    def __init__(self, value):\n        self.value = value\n\n"
            + usage
            + "\n"
        )
        before = resource.read()
        with pytest.raises(RefactoringError, match="non-call"):
            ChangeSignature(project, resource, before.index("Builder")).get_changes([
                ArgumentAdder(
                    0, "token", value="'received'", keyword_only=True, annotation="str"
                )
            ])
        assert resource.read() == before
    finally:
        project.close()


def test_required_constructor_keyword_refuses_aliased_import(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "class Builder:\n    def __init__(self, value):\n        self.value = value\n"
        )
        consumer = project.root.create_file("consumer.py")
        consumer.write("from sample import Builder as Factory\nanswer = Factory(7)\n")
        before = resource.read(), consumer.read()
        with pytest.raises(RefactoringError, match="import alias"):
            ChangeSignature(
                project, resource, resource.read().index("Builder")
            ).get_changes([
                ArgumentAdder(
                    0, "token", value="'received'", keyword_only=True, annotation="str"
                )
            ])
        assert (resource.read(), consumer.read()) == before
    finally:
        project.close()


@pytest.mark.parametrize(
    "call",
    [
        "run(value for value in produce())",
        "run((value for value in produce()))",
        "run(\n    value for value in produce()\n    # retained generator comment\n)",
    ],
)
def test_required_keyword_preserves_generator_argument_evaluation(tmp_path, call):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "produced = []\n"
            "def produce():\n    produced.append('once')\n    return (1, 2)\n\n"
            "def run(values):\n    return tuple(values), token\n\n"
            "answer = " + call + "\n"
        )
        addition = ArgumentAdder(
            0, "token", value="'received'", keyword_only=True, annotation="str"
        )
        project.do(
            ChangeSignature(project, resource, resource.read().index("run")).get_changes(
                [addition]
            )
        )
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["answer"] == ((1, 2), "received")
        assert namespace["produced"] == ["once"]
        if "# retained generator comment" in call:
            assert "# retained generator comment" in resource.read()
        assert not ChangeSignature(
            project, resource, resource.read().index("run")
        ).get_changes([addition]).changes
    finally:
        project.close()


@pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 requires Python 3.12")
@pytest.mark.parametrize(
    "header",
    [
        "def run[T: (int, str)](value: T) -> T:",
        "def run[\n    T: (int, str),  # retained bound comment\n](value: T) -> T:",
    ],
)
def test_required_keyword_uses_parameter_region_after_type_bounds(tmp_path, header):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(header + "\n    return value\n\nanswer = run(7)\n")
        addition = ArgumentAdder(
            0, "token", value="'received'", keyword_only=True, annotation="str"
        )
        project.do(
            ChangeSignature(project, resource, resource.read().index("run")).get_changes(
                [addition]
            )
        )
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["answer"] == 7
        assert namespace["run"].__type_params__[0].__constraints__ == (int, str)
        assert inspect.signature(namespace["run"]).parameters["token"].kind is (
            inspect.Parameter.KEYWORD_ONLY
        )
        assert not ChangeSignature(
            project, resource, resource.read().index("run")
        ).get_changes([addition]).changes
    finally:
        project.close()


@pytest.mark.parametrize("decorator", ["decorate", "decorate()"])
def test_required_keyword_refuses_unproven_decorator(tmp_path, decorator):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "def decorate(function=None):\n"
            "    def apply(function):\n"
            "        def wrapper(value):\n            return function(value)\n"
            "        return wrapper\n"
            "    return apply if function is None else apply(function)\n\n"
            f"@{decorator}\ndef run(value):\n    return value\n\nanswer = run(7)\n"
        )
        before = resource.read()
        with pytest.raises(RefactoringError, match="decorator"):
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(
                    0, "token", value="'received'", keyword_only=True, annotation="str"
                )
            ])
        assert resource.read() == before
    finally:
        project.close()


@pytest.mark.parametrize("name", ["class", "await", "False"])
def test_required_keyword_refuses_reserved_parameter_name(name):
    with pytest.raises(RefactoringError, match="identifier"):
        ArgumentAdder(0, name, value="'received'", keyword_only=True, annotation="str")


@pytest.mark.parametrize("name", ["'Builder'", "selected_name"])
def test_required_constructor_keyword_refuses_reflective_factory(tmp_path, name):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "class Builder:\n    def __init__(self, value):\n        self.value = value\n"
        )
        consumer = project.root.create_file("consumer.py")
        consumer.write(
            "import sample\nanswer = getattr(sample, " + name + ")(7)\n"
        )
        before = resource.read(), consumer.read()
        with pytest.raises(RefactoringError, match="signature consumer") as failure:
            ChangeSignature(
                project, resource, resource.read().index("Builder")
            ).get_changes([
                ArgumentAdder(
                    0, "token", value="'received'", keyword_only=True, annotation="str"
                )
            ])
        assert isinstance(failure.value.__cause__, RefactoringError)
        assert ".py:" in str(failure.value)
        assert (resource.read(), consumer.read()) == before
    finally:
        project.close()


def test_optional_keyword_keeps_canonical_calls_and_escaped_references(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("def run(value: int) -> int:\n    return value\n\ncallback = run\nanswer = callback(7)\n")
        addition = ArgumentAdder(0, "environment", default="None", keyword_only=True, annotation="str | None")
        project.do(ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]))
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["answer"] == 7
        assert inspect.signature(namespace["run"]).parameters["environment"].default is None
        assert not ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]).changes
    finally:
        project.close()


def test_optional_keyword_injects_only_declared_caller_override(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("def run(value: int) -> int:\n    return value\n\ndef selected():\n    return run(7)\n\ndef normal():\n    return run(9)\n")
        def value(module, occurrence):
            scope = module.get_scope().get_inner_scope_for_line(occurrence.lineno)
            return "'prepared'" if scope.pyobject.get_name() == "selected" else None
        addition = ArgumentAdder(0, "environment", default="None", value=value, keyword_only=True, annotation="str | None")
        project.do(ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]))
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["selected"]() == 7
        assert namespace["normal"]() == 9
        assert not ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]).changes
    finally:
        project.close()


@pytest.mark.parametrize(
    "declarations",
    [
        "class Builder:\n    def __new__(cls, value):\n        return super().__new__(cls)\n",
        "class Base:\n    def __new__(cls, value):\n        return super().__new__(cls)\n\nclass Builder(Base):\n",
        "class Meta(type):\n    def __call__(cls, value):\n        return super().__call__(value)\n\nclass Builder(metaclass=Meta):\n",
        "class Meta(type):\n    pass\n\nclass Base(metaclass=Meta):\n    pass\n\nclass Builder(Base):\n",
        "class Builder(UnknownBase):\n",
    ],
)
def test_constructor_keyword_refuses_unproven_allocation(tmp_path, declarations):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            declarations
            + "    def __init__(self, value):\n        self.value = value\n\nanswer = Builder(7)\n"
        )
        before = resource.read()
        with pytest.raises(RefactoringError, match="allocation"):
            ChangeSignature(
                project, resource, before.index("class Builder") + len("class ")
            ).get_changes([
                ArgumentAdder(0, "token", value="'received'", keyword_only=True)
            ])
        assert resource.read() == before
    finally:
        project.close()


@pytest.mark.parametrize("default", [None, "1, 2"])
@pytest.mark.parametrize("value", ["1, 2", "(1, 2)", "1, 2  # retained expression"])
def test_keyword_tuple_expressions_preserve_grouping_and_idempotence(tmp_path, default, value):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("def run(value):\n    return token\n\nanswer = run(7)\n")
        addition = ArgumentAdder(
            0, "token", default=default, value=value, keyword_only=True,
            annotation="tuple[int, int]",
        )
        project.do(ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]))
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["answer"] == (1, 2)
        assert inspect.signature(namespace["run"]).parameters["token"].annotation == tuple[int, int]
        if default is not None:
            assert namespace["run"](7) == (1, 2)
        assert not ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]).changes
    finally:
        project.close()


@pytest.mark.parametrize("field", ["value", "annotation", "default"])
def test_keyword_expression_refuses_argument_injection(field):
    with pytest.raises(RefactoringError, match="expression"):
        ArgumentAdder(
            0, "token", keyword_only=True,
            **{"value": "'received'", field: "'received', other='injected'"},
        )


def test_keyword_callback_refuses_invalid_expression_without_publication(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("def run(value):\n    return value\n\nanswer = run(7)\n")
        before = resource.read()
        with pytest.raises(RefactoringError, match="expression"):
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(
                    0, "token", value=lambda module, occurrence: "'received', other='injected'",
                    keyword_only=True,
                )
            ])
        assert resource.read() == before
    finally:
        project.close()


def test_optional_constructor_override_refuses_class_decorator(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "def decorate(cls):\n    def build(value):\n        return cls(value)\n    return build\n\n"
            "@decorate\nclass Builder:\n    def __init__(self, value):\n        self.value = value\n\nanswer = Builder(7)\n"
        )
        before = resource.read()
        with pytest.raises(RefactoringError, match="decorator"):
            ChangeSignature(project, resource, before.index("class Builder") + len("class ")).get_changes([
                ArgumentAdder(0, "token", default="None", value="'received'", keyword_only=True)
            ])
        assert resource.read() == before
    finally:
        project.close()


def test_keyword_expression_refuses_invalid_context_before_publication(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("def run(value):\n    return value\n\nanswer = run(7)\n")
        before = resource.read()
        with pytest.raises(RefactoringError, match="source context"):
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(0, "token", value="(yield 1)", keyword_only=True)
            ])
        assert resource.read() == before
    finally:
        project.close()


@pytest.mark.parametrize(
    "setup, usage",
    [
        ("", 'globals()["run"](7)'),
        ("", """int(f"{globals()['run'](7)}")"""),
        ("", 'locals()["run"](7)'),
        ("", 'vars()["run"](7)'),
        ("from builtins import globals as namespace\n", 'namespace()["run"](7)'),
        ('namespace = globals()\n', 'namespace["run"](7)'),
        ('import builtins\n', 'getattr(builtins, "globals")()["run"](7)'),
        ('import builtins\n', 'builtins.globals()["run"](7)'),
        ('import builtins\n', 'builtins.getattr(builtins, "globals")()["run"](7)'),
        ('import builtins\ndef factory():\n    return builtins\n', 'getattr(factory(), "globals")()["run"](7)'),
        ('import builtins\n', 'getattr(builtins, "glo" + "bals")()["run"](7)'),
        ('import builtins\nnamespace = getattr(builtins, "globals")\n', 'namespace()["run"](7)'),
        ('import builtins\n', 'builtins.__dict__["globals"]()["run"](7)'),
        ('import builtins\n', 'getattr(builtins, "__dict__")["globals"]()["run"](7)'),
    ],
)
def test_required_keyword_refuses_exposed_module_namespace(tmp_path, setup, usage):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("def run(value):\n    return value\n\n" + setup + "answer = " + usage + "\n")
        before = resource.read()
        namespace = {}
        exec(before, namespace)
        assert namespace["answer"] == 7
        with pytest.raises(RefactoringError, match="signature consumer") as failure:
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(0, "token", value="'received'", keyword_only=True)
            ])
        assert isinstance(failure.value.__cause__, RefactoringError)
        assert ".py:" in str(failure.value)
        assert resource.read() == before
    finally:
        project.close()


@pytest.mark.parametrize(
    "setup, usage",
    [
        ("", 'Runner.__dict__["run"](Runner(), 7)'),
        ("", 'vars(Runner)["run"](Runner(), 7)'),
        ("", 'getattr(Runner, "__dict__")["run"](Runner(), 7)'),
        ('namespace = Runner.__dict__\n', 'namespace["run"](Runner(), 7)'),
    ],
)
def test_required_keyword_refuses_exposed_class_namespace(tmp_path, setup, usage):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("class Runner:\n    def run(self, value):\n        return value\n\n" + setup + "answer = " + usage + "\n")
        before = resource.read()
        namespace = {}
        exec(before, namespace)
        assert namespace["answer"] == 7
        with pytest.raises(RefactoringError, match="signature consumer") as failure:
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(0, "token", value="'received'", keyword_only=True)
            ])
        assert isinstance(failure.value.__cause__, RefactoringError)
        assert ".py:" in str(failure.value)
        assert resource.read() == before
    finally:
        project.close()


@pytest.mark.parametrize("callee", ["(run)", "((run))"])
@pytest.mark.parametrize("default", [None, "'default'"])
def test_parenthesized_native_call_receives_declared_keyword_override(tmp_path, callee, default):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("def run(value):\n    return value, token\n\nanswer = " + callee + "(7)\n")
        addition = ArgumentAdder(0, "token", default=default, value="'override'", keyword_only=True)
        project.do(ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]))
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["answer"] == (7, "override")
        assert not ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]).changes
    finally:
        project.close()


@pytest.mark.parametrize(
    "setup",
    [
        "class Other:\n    label = 'foreign'\nnamespace = Other.__dict__\n",
        "def globals():\n    return {'label': 'foreign'}\nnamespace = globals()\n",
        "import operator\nclass Other:\n    def label(self):\n        return 'foreign'\nnamespace = {'label': operator.methodcaller('label')(Other())}\n",
        "class methodcaller:\n    def __init__(self, value):\n        self.label = value\nnamespace = methodcaller('foreign').__dict__\n",
    ],
)
def test_required_keyword_preserves_unrelated_namespace_bindings(tmp_path, setup):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("def run(value):\n    return value, token\n\n" + setup + "answer = run(7)\n")
        addition = ArgumentAdder(0, "token", value="'received'", keyword_only=True)
        project.do(ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]))
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["answer"] == (7, "received")
        assert namespace["namespace"]["label"] == "foreign"
    finally:
        project.close()


@pytest.mark.parametrize(
    "imports, usage",
    [
        ("import operator\n", "operator.methodcaller('run', 7)(Runner())"),
        ("from operator import methodcaller as invoke\n", "invoke('run', 7)(Runner())"),
        ("import _operator\n", "_operator.methodcaller('run', 7)(Runner())"),
        ("import operator\n", "operator.attrgetter('run')(Runner())(7)"),
        ("from operator import attrgetter as resolve\n", "resolve('run')(Runner())(7)"),
        ("import operator\nclass Holder:\n    child = None\nholder = Holder()\nholder.child = Runner()\n", "operator.attrgetter('child.run')(holder)(7)"),
        ("import operator\nselected_name = 'run'\n", "operator.methodcaller(selected_name, 7)(Runner())"),
        ("import operator\n", "getattr(operator, 'methodcaller')('run', 7)(Runner())"),
        ("import operator\n", "operator.__dict__['attrgetter']('run')(Runner())(7)"),
    ],
)
def test_required_keyword_refuses_native_attribute_adapters(tmp_path, imports, usage):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("class Runner:\n    def run(self, value):\n        return value\n\n" + imports + "answer = " + usage + "\n")
        before = resource.read()
        namespace = {}
        exec(before, namespace)
        assert namespace["answer"] == 7
        with pytest.raises(RefactoringError, match="signature consumer") as failure:
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(0, "token", value="'received'", keyword_only=True)
            ])
        assert isinstance(failure.value.__cause__, RefactoringError)
        assert ".py:" in str(failure.value)
        assert resource.read() == before
    finally:
        project.close()


@pytest.mark.parametrize(
    "imports, usage",
    [
        ("from functools import partial\nfrom operator import methodcaller\n", "partial(methodcaller, 'run', 7)()(Runner())"),
        ("from functools import partial\n", "partial(getattr, Runner(), 'run')()(7)"),
        ("", "object.__getattribute__(Runner(), 'run')(7)"),
        ("", "type.__getattribute__(Runner, 'run')(Runner(), 7)"),
        ("import inspect\n", "dict(inspect.getmembers(Runner()))['run'](7)"),
        ("from inspect import getmembers as members\n", "dict(members(Runner))['run'](Runner(), 7)"),
    ],
)
def test_required_keyword_refuses_opaque_target_consumers(tmp_path, imports, usage):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("class Runner:\n    def run(self, value):\n        return value\n\n" + imports + "answer = " + usage + "\n")
        before = resource.read()
        namespace = {}
        exec(before, namespace)
        assert namespace["answer"] == 7
        with pytest.raises(RefactoringError, match="opaque signature consumer"):
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(0, "token", value="'received'", keyword_only=True)
            ])
        assert resource.read() == before
    finally:
        project.close()


@pytest.mark.parametrize(
    "imports, usage",
    [
        ("", "object.__getattribute__(Other(), 'run')()"),
        ("", "type.__getattribute__(Other, 'run')(Other())"),
        ("import inspect\n", "dict(inspect.getmembers(Other()))['run']()"),
    ],
)
def test_required_keyword_preserves_opaque_consumers_of_other_bindings(tmp_path, imports, usage):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "class Runner:\n    def run(self, value):\n        return value, token\n\n"
            "class Other:\n    def run(self):\n        return 'foreign'\n\n"
            + imports + "foreign = " + usage + "\nanswer = Runner().run(7)\n"
        )
        addition = ArgumentAdder(0, "token", value="'received'", keyword_only=True)
        project.do(ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]))
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["answer"] == (7, "received")
        assert namespace["foreign"] == "foreign"
    finally:
        project.close()


def test_required_keyword_preserves_analyzed_internal_owner_consumer(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "class Runner:\n    def run(self, value):\n        return value, token\n\n"
            "def consume(owner):\n    return owner.run(7)\n\nanswer = consume(Runner())\n"
        )
        addition = ArgumentAdder(0, "token", value="'received'", keyword_only=True)
        project.do(ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]))
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["answer"] == (7, "received")
        assert not ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]).changes
    finally:
        project.close()


@pytest.mark.parametrize(
    "setup, usage",
    [
        ("", 'eval("Runner().run(7)")'),
        ("", 'exec("answer = Runner().run(7)")'),
        ('source = "Runner().run(7)"\n', 'eval(source)'),
        ('from builtins import eval as evaluate\n', 'evaluate("Runner().run(7)")'),
    ],
)
def test_required_keyword_refuses_unproven_dynamic_code(tmp_path, setup, usage):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("class Runner:\n    def run(self, value):\n        return value\n\n" + setup + "answer = " + usage + "\n")
        before = resource.read()
        namespace = {}
        exec(before, namespace)
        if not usage.startswith("exec("):
            assert namespace["answer"] == 7
        with pytest.raises(RefactoringError, match="Dynamic code"):
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(0, "token", value="'received'", keyword_only=True)
            ])
        assert resource.read() == before
    finally:
        project.close()


@pytest.mark.parametrize(
    "setup, collection",
    [
        ("", "[Runner()]"),
        ("", "(Runner(),)"),
        ("", "{'one': Runner()}.values()"),
        ('owners = [Runner()]\n', "owners"),
        ('class Other:\n    def run(self):\n        return "foreign"\nowners = [Other(), Runner()]\n', "owners[1:]"),
    ],
)
def test_required_keyword_refuses_nested_namespaces_in_opaque_collections(tmp_path, setup, collection):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "import inspect\nclass Runner:\n    def run(self, value):\n        return value\n\n"
            + setup + "answer = dict(next(map(inspect.getmembers, " + collection + ")))['run'](7)\n"
        )
        before = resource.read()
        namespace = {}
        exec(before, namespace)
        assert namespace["answer"] == 7
        with pytest.raises(RefactoringError, match="opaque signature consumer"):
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(0, "token", value="'received'", keyword_only=True)
            ])
        assert resource.read() == before
    finally:
        project.close()


def test_required_keyword_preserves_literal_dynamic_code_and_foreign_collection(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "import inspect\nclass Runner:\n    def run(self, value):\n        return value, token\n\n"
            "class Other:\n    def run(self):\n        return 'foreign'\n\n"
            "exec('pass')\nliteral = eval('(1, 2)')\nowners = [Other()]\n"
            "foreign = dict(next(map(inspect.getmembers, owners)))['run']()\nanswer = Runner().run(7)\n"
        )
        addition = ArgumentAdder(0, "token", value="'received'", keyword_only=True)
        project.do(ChangeSignature(project, resource, resource.read().index("run")).get_changes([addition]))
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["answer"] == (7, "received")
        assert namespace["foreign"] == "foreign"
        assert namespace["literal"] == (1, 2)
    finally:
        project.close()


@pytest.mark.parametrize(
    "setup, usage",
    [
        ('enabled = True\nexecute = eval if enabled else str\n', "execute('Runner().run(7)')"),
        ("", "__builtins__['eval']('Runner().run(7)')"),
        ('from inspect import getmembers\nclass Holder:\n    pass\nHolder.child = Runner()\n', "dict(getmembers(dict(getmembers(Holder()))['child']))['run'](7)"),
    ],
)
def test_required_keyword_refuses_unproven_callable_or_transitive_namespace(tmp_path, setup, usage):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write("class Runner:\n    def run(self, value):\n        return value\n\n" + setup + "answer = " + usage + "\n")
        before = resource.read()
        namespace = {}
        exec(before, namespace)
        assert namespace["answer"] == 7
        with pytest.raises(RefactoringError):
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(0, "token", value="'received'", keyword_only=True)
            ])
        assert resource.read() == before
    finally:
        project.close()


@pytest.mark.parametrize("foreign,inert", [(False, True), (True, True), (False, False), (True, False)])
@pytest.mark.parametrize("operation,statement", [
    ("__setitem__", "sink[0] = {value}"),
    ("__setattr__", "sink.target = {value}"),
    ("__iadd__", "sink += {value}"),
    ("__add__", "sink += {value}"),
    ("__radd__", "operand = {value}\noperand += sink"),
    ("__add__", "sink + {value}"),
    ("__radd__", "{value} + sink"),
    ("__contains__", "{value} in sink"),
    ("__contains__", "{value} not in sink"),
    ("__eq__", "sink == {value}"),
    ("__gt__", "{value} < sink"),
])
def test_signature_effect_boundary_covers_external_store(tmp_path, foreign, inert, operation, statement):
    root = tmp_path / 'project'
    dependency = tmp_path / 'dependency'
    root.mkdir()
    dependency.mkdir()
    (dependency / 'signature_sink.py').write_text(
        "class Sink:\n    def " + operation + "(self, "
        + ("key, value" if operation in ("__setitem__", "__setattr__") else "value")
        + "):\n        object.__setattr__(self, 'result', value.run(7))\n        return self\n",
        encoding='utf-8',
    )
    project = Project(str(root), ropefolder=None, python_path=[str(dependency)])
    try:
        resource = project.root.create_file('sample.py')
        value = 'Other()' if foreign else 'Runner()'
        resource.write(
            "from signature_sink import Sink\nclass Runner:\n    def run(self, value):\n        return value\n\n"
            "class Other:\n    def run(self, value):\n        return "
            + ("11" if inert else "value + 4") + "\n\n"
            + "sink = Sink()\n"
            + statement.format(value=value) + "\nprint(sink.result)\n"
            + "answer = Runner().run(3)\n"
        )
        before = resource.read()
        environment = dict(os.environ, PYTHONPATH=str(dependency))
        original = subprocess.run([sys.executable, resource.real_path], env=environment, capture_output=True, text=True, check=True)
        assert original.stdout.strip() == ('11' if foreign else '7')
        refactoring = ChangeSignature(project, resource, before.index('run'))
        addition = ArgumentAdder(0, 'token', value="'received'", keyword_only=True)
        if foreign:
            project.do(refactoring.get_changes([addition]))
            actual = subprocess.run([sys.executable, resource.real_path], env=environment, capture_output=True, text=True, check=True)
            assert actual.stdout.strip() == '11'
        else:
            with pytest.raises(RefactoringError, match="effect " + operation) as failure:
                refactoring.get_changes([addition])
            assert "Target namespace escapes" in str(failure.value)
            assert isinstance(failure.value.__cause__, RefactoringError)
            assert "sample.py:" in str(failure.value)
            assert resource.read() == before
    finally:
        project.close()


def test_signature_boundary_does_not_analyze_unimported_unknown_callback(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file('sample.py')
        resource.write("def run(value):\n    return value\n\nanswer = run(7)\n")
        unrelated = project.root.create_file('unrelated.py')
        unrelated.write("def invoke(callback):\n    return callback()\n")
        unrelated_before = unrelated.read()
        addition = ArgumentAdder(0, 'token', value="'received'", keyword_only=True)
        project.do(ChangeSignature(project, resource, resource.read().index('run')).get_changes([addition]))
        namespace = {}
        exec(resource.read(), namespace)
        assert namespace['answer'] == 7
        assert unrelated.read() == unrelated_before
    finally:
        project.close()


@pytest.mark.parametrize("invoke", [False, True])
def test_signature_boundary_refuses_opaque_callback_with_or_without_local_call(tmp_path, invoke):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "def run(value):\n    return value\n"
            "def invoke(callback):\n    return callback('run(7)')\n"
            "answer = run(7)\n"
            + ("invoke(eval)\n" if invoke else "")
        )
        before = resource.read()
        namespace = {}
        exec(before, namespace)
        assert namespace["answer"] == 7
        assert namespace["invoke"](eval) == 7
        addition = ArgumentAdder(0, "token", value="'received'", keyword_only=True)
        refactoring = ChangeSignature(project, resource, before.index("run"))
        with pytest.raises(RefactoringError):
            refactoring.get_changes([addition])
        assert resource.read() == before
        current = {}
        exec(resource.read(), current)
        assert current["answer"] == 7
        assert current["invoke"](eval) == 7
    finally:
        project.close()


@pytest.mark.parametrize("foreign", [False, True])
@pytest.mark.parametrize("opaque", [False, True])
def test_signature_boundary_covers_public_api_without_local_call(tmp_path, foreign, opaque):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "class Runner:\n    def run(self, value):\n        return value\n"
            "class Other:\n    def run(self, value):\n        return "
            + ("value + 4" if opaque else "11") + "\n"
            "def public_api():\n    return getattr("
            + ("Other" if foreign else "Runner")
            + "(), 'run')(7)\n"
            + ("def invoke(callback):\n    return callback()\n" if opaque else "")
            + "answer = Runner().run(3)\n"
        )
        before = resource.read()
        namespace = {}
        exec(before, namespace)
        expected = 11 if foreign else 7
        assert namespace["public_api"]() == expected
        if opaque:
            assert namespace["invoke"](lambda: namespace["Runner"]().run(7)) == 7
        addition = ArgumentAdder(0, "token", value="'received'", keyword_only=True)
        refactoring = ChangeSignature(project, resource, before.index("run"))
        if foreign and not opaque:
            project.do(refactoring.get_changes([addition]))
            namespace = {}
            exec(resource.read(), namespace)
            assert namespace["public_api"]() == expected
        else:
            with pytest.raises(RefactoringError) as failure:
                refactoring.get_changes([addition])
            assert "sample.py:" in str(failure.value)
            assert isinstance(failure.value.__cause__, RefactoringError)
            assert resource.read() == before
    finally:
        project.close()


@pytest.mark.parametrize("arguments", ["", "'Runner().run(7)'"])
def test_signature_boundary_refuses_public_callback_without_effect_contract(tmp_path, arguments):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "class Runner:\n    def run(self, value):\n        return value\n"
            "def public_api(callback):\n    return callback(" + arguments + ")\n"
            "answer = Runner().run(3)\n"
        )
        before = resource.read()
        namespace = {}
        exec(before, namespace)
        callback = (lambda: namespace['Runner']().run(7)) if not arguments else lambda source: eval(source, namespace)
        assert namespace['public_api'](callback) == 7
        with pytest.raises(RefactoringError, match="call") as failure:
            ChangeSignature(project, resource, before.index("run")).get_changes([
                ArgumentAdder(0, 'token', value="'received'", keyword_only=True)
            ])
        assert isinstance(failure.value.__cause__, RefactoringError)
        assert 'sample.py:' in str(failure.value)
        assert resource.read() == before
    finally:
        project.close()


def test_yield_from_does_not_hide_signature_before_nested_import(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("sample.py")
        resource.write(
            "def earlier():\n    yield from ()\n"
            "def target(value):\n    return value\n"
            "def later():\n    from math import floor\n    return floor(1)\n"
        )
        refactoring = ChangeSignature(
            project, resource, resource.read().index("def target") + 4
        )
        changes = refactoring.get_changes(
            [ArgumentAdder(0, "selected", default="None", keyword_only=True)]
        )
        assert len(changes.changes) == 1
        project.do(changes)
        namespace = {}
        exec(compile(resource.read(), resource.path, "exec"), namespace)
        assert namespace["target"](7) == 7
        parameter = inspect.signature(namespace["target"]).parameters["selected"]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is None
        assert namespace["later"]() == 1
    finally:
        project.close()
