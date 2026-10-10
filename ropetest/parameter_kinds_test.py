import subprocess
import sys
from textwrap import dedent

import pytest

from rope.base import arguments, builtins, evaluate, exceptions, pynames
from rope.base.project import Project
from rope.contrib.codeassist import code_assist, get_calltip, get_doc
from rope.refactor import change_signature, inline, rename


@pytest.fixture
def project(tmp_path):
    project = Project(
        str(tmp_path), save_objectdb=False, save_history=False, automatic_soa=False
    )
    yield project
    project.close()


def module(project, code, name="source"):
    source = project.root.create_file(name + ".py")
    source.write(dedent(code))
    return source


def execute(project, source):
    result = subprocess.run(
        [sys.executable, source.real_path],
        cwd=project.address,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.parametrize("definition", ["def", "async def"])
@pytest.mark.parametrize(
    "parameters,call", [("target, /", "int"), ("*, target", "target=int")]
)
def test_outer_inline_preserves_parameter_binding(
    project, definition, parameters, call
):
    invocation = f"func({call})"
    if definition == "async def":
        invocation = f"asyncio.run({invocation})"
    source = module(
        project,
        dedent(f"""\
            import asyncio
            target = 42
            {definition} func({parameters}):
                return target
            print({invocation} is int)
            print(target)
        """),
    )
    before = source.read()
    assert execute(project, source) == "True\n42\n"
    project.do(
        inline.create_inline(
            project, source, before.index("target =") + 1
        ).get_changes()
    )
    assert source.read() != before
    assert f"func({parameters})" in source.read()
    assert "return target" in source.read()
    assert execute(project, source) == "True\n42\n"


@pytest.mark.parametrize(
    "parameters,call", [("target, /", "int"), ("*, target", "target=int")]
)
def test_parameter_identity_is_independent_of_outer_assignment(
    project, parameters, call
):
    source = module(
        project,
        dedent(f"""\
            target = 42
            def func({parameters}):
                return target
            print(func({call}) is int)
        """),
    )
    code = source.read()
    pymodule = project.get_pymodule(source)
    formal = evaluate.eval_location(
        pymodule, code.index(parameters) + parameters.index("target") + 1
    )
    body = evaluate.eval_location(
        pymodule, code.index("return target") + len("return ") + 1
    )
    assert isinstance(formal, pynames.ParameterName)
    assert formal is body
    assert formal is not pymodule["target"]
    assert formal.get_definition_location() == (pymodule, 2)
    assert execute(project, source) == "True\n"
    with pytest.raises(exceptions.RefactoringError):
        inline.InlineVariable(
            project, source, code.index("return target") + len("return ") + 1
        )
    assert source.read() == code
    assert execute(project, source) == "True\n"


def test_all_parameter_slots_keep_distinct_objects(project):
    source = module(
        project,
        dedent("""\
            class Pos:
                pass
            class Normal:
                pass
            class Key:
                pass
            class Default:
                pass
            def func(pos, /, normal, *rest, key, default, **extras):
                return pos
            result = func(Pos(), Normal(), 42, default=Default(), key=Key(), extra="value")
            print(isinstance(result, Pos))
        """),
    )
    assert execute(project, source) == "True\n"
    pymodule = project.get_pymodule(source)
    assert pymodule["result"].get_object().get_type() is pymodule["Pos"].get_object()
    function = pymodule["func"].get_object()
    assert function.get_param_names(False) == ["pos", "normal", "key", "default"]
    assert function.get_param_names() == [
        "pos",
        "normal",
        "key",
        "default",
        "rest",
        "extras",
    ]
    parameters = function.get_parameters()
    for index, (name, class_name) in enumerate(
        [("pos", "Pos"), ("normal", "Normal"), ("key", "Key"), ("default", "Default")]
    ):
        assert parameters[name].index == index
        assert (
            parameters[name].get_object().get_type()
            is pymodule[class_name].get_object()
        )
    assert parameters["rest"].index == 4
    assert isinstance(parameters["rest"].get_object().get_type(), builtins.List)
    assert parameters["extras"].index == 5
    assert isinstance(parameters["extras"].get_object().get_type(), builtins.Dict)


def test_positional_only_keyword_does_not_replace_position_slot(project):
    source = module(
        project,
        dedent("""\
            class Pos:
                pass
            class Extra:
                pass
            def func(target, /, **extras):
                return target
            result = func(Pos(), target=Extra())
            print(isinstance(result, Pos))
        """),
    )
    assert execute(project, source) == "True\n"
    pymodule = project.get_pymodule(source)
    assert pymodule["result"].get_object().get_type() is pymodule["Pos"].get_object()
    offset = source.read().index("target=Extra") + 1
    assert evaluate.eval_location(pymodule, offset) is None


def test_keyword_only_call_infers_actual_object(project):
    source = module(
        project,
        dedent("""\
            class Value:
                pass
            def func(*, target):
                return target
            result = func(target=Value())
            print(isinstance(result, Value))
        """),
    )
    assert execute(project, source) == "True\n"
    pymodule = project.get_pymodule(source)
    assert pymodule["result"].get_object().get_type() is pymodule["Value"].get_object()


@pytest.mark.parametrize("parameters", ["target=target, /", "*, target=target"])
def test_default_reference_keeps_outer_identity_and_evaluation_time(
    project, parameters
):
    override = "func(target=int)" if parameters.startswith("*") else "func(int)"
    source = module(
        project,
        dedent(f"""\
            events = []
            def make():
                events.append("created")
                return 42
            target = make()
            def func({parameters}):
                return target
            print(func(), func(), {override} is int, target, len(events))
        """),
    )
    before = source.read()
    assert execute(project, source) == "42 42 True 42 1\n"
    pymodule = project.get_pymodule(source)
    default_offset = before.index("target=target") + len("target=") + 1
    assert evaluate.eval_location(pymodule, default_offset) is pymodule["target"]
    project.do(
        rename.Rename(project, source, before.index("target =") + 1).get_changes(
            "outer"
        )
    )
    assert execute(project, source) == "42 42 True 42 1\n"
    assert "target=outer" in source.read()
    assert "return target" in source.read()


def test_parameter_rename_preserves_positional_only_kwargs_key(project):
    source = module(
        project,
        dedent("""\
            target = 42
            def func(target, /, **extras):
                return target, extras["target"]
            result = func(int, target=str)
            print(result[0] is int, result[1] is str, target)
        """),
    )
    before = source.read()
    assert execute(project, source) == "True True 42\n"
    project.do(
        rename.Rename(
            project, source, before.index("func(target") + len("func(") + 1
        ).get_changes("value")
    )
    assert "target = 42" in source.read()
    assert "target=str" in source.read()
    assert 'extras["target"]' in source.read()
    assert execute(project, source) == "True True 42\n"


def test_parameter_rename_updates_keyword_only_call(project):
    source = module(
        project,
        dedent("""\
            target = 42
            def func(*, target):
                return target
            print(func(target=int) is int, target)
        """),
    )
    before = source.read()
    assert execute(project, source) == "True 42\n"
    project.do(
        rename.Rename(
            project, source, before.index("*, target") + len("*, ") + 1
        ).get_changes("value")
    )
    assert "target = 42" in source.read()
    assert "func(value=int)" in source.read()
    assert execute(project, source) == "True 42\n"


def test_keyword_completion_uses_keyword_capable_parameters(project):
    source = module(
        project,
        dedent("""\
            def func(pos, /, normal, *rest, key, **extras):
                pass
            func(
        """),
    )
    proposals = {
        proposal.name
        for proposal in code_assist(
            project, source.read(), len(source.read()), resource=source
        )
    }
    assert {"normal=", "key="} <= proposals
    assert not {"pos=", "rest=", "extras="} & proposals


@pytest.mark.parametrize("parameters,call", [("target=1, /", ""), ("*, target=1", "")])
def test_unsupported_signature_rewrite_is_atomic(project, parameters, call):
    source = module(
        project,
        dedent(f"""\
            def func({parameters}):
                return target
            print(func({call}))
        """),
    )
    before = source.read()
    assert execute(project, source) == "1\n"
    with pytest.raises(exceptions.RefactoringError):
        changes = change_signature.ChangeSignature(
            project, source, before.index("func") + 1
        ).get_changes([change_signature.ArgumentDefaultInliner(0)])
        project.do(changes)
    assert source.read() == before
    assert execute(project, source) == "1\n"


@pytest.mark.parametrize(
    "decorator,parameters,call,receiver_name,receiver_is_class",
    [
        (
            "",
            "self, /, value, *, key",
            "Child().func(Value(), key=Key())",
            "self",
            False,
        ),
        (
            "",
            "self, /, value, *, key",
            "Child.func(Child(), Value(), key=Key())",
            "self",
            False,
        ),
        (
            "@staticmethod",
            "value, *, key",
            "Child.func(Value(), key=Key())",
            None,
            False,
        ),
        (
            "@staticmethod",
            "value, *, key",
            "Child().func(Value(), key=Key())",
            None,
            False,
        ),
        (
            "@classmethod",
            "cls, value, *, key",
            "Child.func(Value(), key=Key())",
            "cls",
            True,
        ),
        (
            "@classmethod",
            "cls, value, *, key",
            "Child().func(Value(), key=Key())",
            "cls",
            True,
        ),
    ],
)
def test_method_call_slots_use_actual_receiver(
    project, decorator, parameters, call, receiver_name, receiver_is_class
):
    source = module(
        project,
        dedent(f"""\
            class Value:
                pass
            class Key:
                pass
            class Base:
                {decorator}
                def func({parameters}):
                    return value
            class Child(Base):
                pass
            result = {call}
            print(isinstance(result, Value))
        """),
    )
    assert execute(project, source) == "True\n"
    pymodule = project.get_pymodule(source)
    assert pymodule["result"].get_object().get_type() is pymodule["Value"].get_object()
    project.pycore.analyze_module(source)
    function = pymodule["Base"].get_object()["func"].get_object()
    bindings = function.get_parameters()
    for name, expected in [("value", "Value"), ("key", "Key")]:
        assert bindings[name].get_object().get_type() is pymodule[expected].get_object()
        assert all(
            value.get_type() is pymodule[expected].get_object()
            for value in bindings[name].get_objects()
        )
    if receiver_name is not None:
        expected = pymodule["Child"].get_object()
        receiver = bindings[receiver_name].get_object()
        assert (receiver if receiver_is_class else receiver.get_type()) is expected
        assert all(
            (value if receiver_is_class else value.get_type()) is expected
            for value in bindings[receiver_name].get_objects()
        )


def test_callable_attribute_adds_its_receiver_once(project):
    source = module(
        project,
        dedent("""\
            class Value:
                pass
            class Key:
                pass
            class Callable:
                def __call__(self, value, *, key):
                    return value
            class Holder:
                callback = Callable()
            result = Holder().callback(Value(), key=Key())
            print(isinstance(result, Value))
        """),
    )
    assert execute(project, source) == "True\n"
    pymodule = project.get_pymodule(source)
    assert pymodule["result"].get_object().get_type() is pymodule["Value"].get_object()
    project.pycore.analyze_module(source)
    function = pymodule["Callable"].get_object()["__call__"].get_object()
    for name, expected in [("self", "Callable"), ("value", "Value"), ("key", "Key")]:
        binding = function.get_parameters()[name]
        assert binding.get_object().get_type() is pymodule[expected].get_object()
        assert all(
            value.get_type() is pymodule[expected].get_object()
            for value in binding.get_objects()
        )


def test_defaults_follow_positional_tail_and_keyword_names(project):
    source = module(
        project,
        dedent("""\
            class Pos:
                pass
            class Normal:
                pass
            class Key:
                pass
            def func(pos=Pos(), /, normal=Normal(), *rest, key=Key(), **extras):
                return normal
            result = func()
            print(isinstance(result, Normal))
        """),
    )
    assert execute(project, source) == "True\n"
    pymodule = project.get_pymodule(source)
    assert pymodule["result"].get_object().get_type() is pymodule["Normal"].get_object()
    project.pycore.analyze_module(source)
    for name, expected in [("pos", "Pos"), ("normal", "Normal"), ("key", "Key")]:
        binding = pymodule["func"].get_object().get_parameters()[name]
        assert binding.get_object().get_type() is pymodule[expected].get_object()


def test_keyword_completion_distinguishes_required_and_none_default(project):
    source = module(
        project,
        dedent("""\
            def func(*, required, optional=None):
                return required
            print(func(required=int) is int)
        """),
    )
    assert execute(project, source) == "True\n"
    code = source.read() + "func("
    proposals = {
        proposal.name: proposal
        for proposal in code_assist(project, code, len(code), resource=source)
    }
    assert proposals["required="].get_default() is None
    assert proposals["optional="].get_default() == "None"


@pytest.mark.parametrize("unpacking", ["*supply()", "**supply()"])
def test_unknown_unpacking_does_not_invent_default_bindings(project, unpacking):
    source = module(
        project,
        dedent(f"""\
            class Pos:
                pass
            class Key:
                pass
            def supply():
                return eval("{'[]' if unpacking.startswith('*s') else '{}'}")
            def func(pos=Pos(), /, *, key=Key()):
                return pos
            result = func({unpacking})
            print(isinstance(result, Pos))
        """),
    )
    assert execute(project, source) == "True\n"
    pymodule = project.get_pymodule(source)
    function = pymodule["func"].get_object()
    call = pymodule.get_ast().body[-2].value
    actual = arguments.create_arguments(None, function, call, pymodule.get_scope())
    objects = actual.get_arguments(function.get_param_names(False))
    if unpacking.startswith("*s"):
        assert objects[0] is None
        assert objects[1].get_type() is pymodule["Key"].get_object()
    else:
        assert objects[0].get_type() is pymodule["Pos"].get_object()
        assert objects[1] is None


def test_variadic_receiver_does_not_occupy_keyword_only_slot(project):
    source = module(
        project,
        dedent("""\
            class Key:
                pass
            class Owner:
                def func(*items, key):
                    return key
            result = Owner().func(key=Key())
            print(isinstance(result, Key))
        """),
    )
    assert execute(project, source) == "True\n"
    pymodule = project.get_pymodule(source)
    assert pymodule["result"].get_object().get_type() is pymodule["Key"].get_object()
    project.pycore.analyze_module(source)
    function = pymodule["Owner"].get_object()["func"].get_object()
    assert (
        function.get_parameters()["key"].get_object().get_type()
        is pymodule["Key"].get_object()
    )
    assert isinstance(
        function.get_parameters()["items"].get_object().get_type(), builtins.List
    )


@pytest.mark.parametrize(
    "parameters,call",
    [("target, /, **extras", "Value(), target=int"), ("*, target", "target=Value()")],
)
def test_dynamic_calls_record_ordinary_parameter_slots(project, parameters, call):
    source = module(
        project,
        dedent(f"""\
            class Value:
                pass
            def func({parameters}):
                return eval("target")
            result = func({call})
            print(isinstance(result, Value))
        """),
    )
    assert execute(project, source) == "True\n"
    project.pycore.run_module(source).wait_process()
    pymodule = project.get_pymodule(source)
    function = pymodule["func"].get_object()
    expected = pymodule["Value"].get_object()
    assert function.get_parameters()["target"].get_object().get_type() is expected
    assert function.get_parameters()["target"].get_objects()
    assert all(
        value.get_type() is expected
        for value in function.get_parameters()["target"].get_objects()
    )
    assert pymodule["result"].get_object().get_type() is expected
    manager = project.pycore.object_info
    path, key = manager._get_call_scope(function)
    calls = list(manager.objectdb.get_callinfos(path, key))
    assert calls
    for call_info in calls:
        recorded = call_info.get_parameters()
        assert len(recorded) == 1
        assert manager.to_pyobject(recorded[0]).get_type() is expected


def test_default_offsets_count_characters_after_non_ascii_prefix(project):
    source = module(
        project,
        dedent("""\
            target = int
            def func(
                *, 中文="字",
                value=("字", target)[1],
            ):
                return value
            print(func() is int, func(value=str) is str)
        """),
    )
    before = source.read()
    assert execute(project, source) == "True True\n"
    pymodule = project.get_pymodule(source)
    default_offset = before.index('"字", target') + len('"字", ') + 1
    assert evaluate.eval_location(pymodule, default_offset) is pymodule["target"]
    project.do(
        rename.Rename(project, source, before.index("target") + 1).get_changes("outer")
    )
    assert execute(project, source) == "True True\n"
    assert 'value=("字", outer)' in source.read()


@pytest.mark.parametrize("legacy", ["same_length", "short"])
def test_changed_layout_isolates_legacy_calls_and_preserves_name_data(tmp_path, legacy):
    folder = str(tmp_path)
    project = Project(
        folder, save_objectdb=True, save_history=False, automatic_soa=False
    )
    source = module(
        project,
        dedent("""\
            class B:
                pass
            class Q:
                pass
            class K:
                pass
            def func(b, q, k):
                return q
            result = func(B(), Q(), K())
            print(isinstance(result, Q))
        """),
    )
    if legacy == "short":
        source.write(
            source.read()
            .replace("func(b, q, k)", "func(b)")
            .replace("return q", "return b")
            .replace("func(B(), Q(), K())", "func(B())")
            .replace("result, Q", "result, B")
        )
    assert execute(project, source) == "True\n"
    pymodule = project.get_pymodule(source)
    function = pymodule["func"].get_object()
    previous_class = "Q" if legacy == "same_length" else "B"
    assert (
        pymodule["result"].get_object().get_type()
        is pymodule[previous_class].get_object()
    )
    project.pycore.analyze_module(source)
    manager = project.pycore.object_info
    raw_scope = manager._get_scope(function)
    assert manager._get_call_scope(function) == raw_scope
    assert (
        manager.get_returned(function, None).get_type()
        is pymodule[previous_class].get_object()
    )
    manager.save_per_name(
        function.get_scope(), "remembered", pymodule["B"].get_object()
    )
    if legacy == "same_length":
        replacement = (
            source.read()
            .replace("func(b, q, k)", "func(b, *rest, k, q, **extras)")
            .replace("return q", "return k")
            .replace("func(B(), Q(), K())", "func(B(), q=Q(), k=K())")
            .replace("result, Q", "result, K")
        )
    else:
        replacement = (
            source.read()
            .replace("func(b)", "func(b, /, *, k)")
            .replace("return b", "return k")
            .replace("func(B())", "func(B(), k=K())")
            .replace("result, B", "result, K")
        )
    source.write(replacement)
    assert execute(project, source) == "True\n"
    pymodule = project.get_pymodule(source)
    function = pymodule["func"].get_object()
    assert manager.get_parameter_objects(function) is None
    assert manager.get_returned(function, None) is None
    assert (
        manager.get_per_name(function.get_scope(), "remembered")
        is pymodule["B"].get_object()
    )
    assert pymodule["result"].get_object().get_type() is pymodule["K"].get_object()
    project.pycore.analyze_module(source)
    manager.objectdb.validate_file(raw_scope[0])
    project.close()
    reopened = Project(
        folder, save_objectdb=True, save_history=False, automatic_soa=False
    )
    try:
        pymodule = reopened.get_pymodule(reopened.get_file("source.py"))
        function = pymodule["func"].get_object()
        manager = reopened.pycore.object_info
        assert manager._get_call_scope(function) != manager._get_scope(function)
        assert (
            manager.get_returned(function, None).get_type()
            is pymodule["K"].get_object()
        )
        assert (
            manager.get_per_name(function.get_scope(), "remembered")
            is pymodule["B"].get_object()
        )
        expected_parameters = [("b", "B"), ("k", "K")]
        if legacy == "same_length":
            expected_parameters.append(("q", "Q"))
        for name, expected in expected_parameters:
            assert (
                function.get_parameters()[name].get_object().get_type()
                is pymodule[expected].get_object()
            )
    finally:
        reopened.close()


def test_nested_default_uses_enclosing_parameter_identity(project):
    source = module(
        project,
        dedent("""\
            def outer(target, /):
                def inner(*, target=target):
                    return target
                return inner()
            print(outer(int) is int, outer(str) is str)
        """),
    )
    before = source.read()
    assert execute(project, source) == "True True\n"
    pymodule = project.get_pymodule(source)
    outer = pymodule["outer"].get_object()
    default_offset = before.index("target=target") + len("target=") + 1
    assert (
        evaluate.eval_location(pymodule, default_offset)
        is outer.get_parameters()["target"]
    )
    project.do(
        rename.Rename(project, source, before.index("target") + 1).get_changes("value")
    )
    assert execute(project, source) == "True True\n"
    assert "target=value" in source.read()
    assert "return target" in source.read()


def test_positional_only_self_registers_instance_attributes(project):
    source = module(
        project,
        dedent("""\
            class Value:
                pass
            class Owner:
                def __init__(self, /, value):
                    self.value = value
            result = Owner(Value()).value
            print(isinstance(result, Value))
        """),
    )
    assert execute(project, source) == "True\n"
    project.pycore.analyze_module(source)
    pymodule = project.get_pymodule(source)
    assert pymodule["result"].get_object().get_type() is pymodule["Value"].get_object()
    assert "value" in pymodule["Owner"].get_object()


def test_persisted_malformed_call_scopes_are_discarded(tmp_path):
    folder = str(tmp_path)
    project = Project(
        folder, save_objectdb=True, save_history=False, automatic_soa=False
    )
    source = module(
        project,
        dedent("""\
            class Value:
                pass
            def func(*, value):
                return value
            result = func(value=Value)
            print(result is Value)
        """),
    )
    assert execute(project, source) == "True\n"
    pymodule = project.get_pymodule(source)
    assert pymodule["result"].get_object() is pymodule["Value"].get_object()
    manager = project.pycore.object_info
    function = pymodule["func"].get_object()
    path, valid_key = manager._get_call_scope(function)
    invalid_keys = [
        "!parameter-layout-v1:",
        "!parameter-layout-v1:{broken",
        "!parameter-layout-v1:[]",
        '!parameter-layout-v1:["func","invalid",[]]',
        '!parameter-layout-v1:["func","function",[["kwonly","previous"]]]',
    ]
    for key in invalid_keys:
        manager.objectdb.add_pername(
            path, key, "discarded", manager.to_textual(pymodule["Value"].get_object())
        )
    manager.save_per_name(
        function.get_scope(), "remembered", pymodule["Value"].get_object()
    )
    project.close()
    reopened = Project(
        folder, save_objectdb=True, save_history=False, automatic_soa=False
    )
    try:
        manager = reopened.pycore.object_info
        assert set(invalid_keys) <= set(manager.objectdb.files[path])
        manager.objectdb.validate_file(path)
        assert not set(invalid_keys) & set(manager.objectdb.files[path])
        assert valid_key in manager.objectdb.files[path]
        pymodule = reopened.get_pymodule(reopened.get_file("source.py"))
        function = pymodule["func"].get_object()
        assert manager.get_returned(function, None) is pymodule["Value"].get_object()
        assert (
            manager.get_per_name(function.get_scope(), "remembered")
            is pymodule["Value"].get_object()
        )
    finally:
        reopened.close()


def test_ordinary_method_kinds_and_callable_use_correct_receivers(project):
    source = module(
        project,
        dedent("""\
            class Value:
                pass
            class Base:
                def normal(self, value):
                    return value
                @staticmethod
                def static(value):
                    return value
                @classmethod
                def class_method(cls, value):
                    return cls
            class Child(Base):
                pass
            class Callable:
                def __call__(self, value):
                    return value
            class Holder:
                callback = Callable()
            normal_result = Child().normal(Value())
            static_result = Child().static(Value())
            class_result = Child.class_method(Value())
            callable_result = Holder().callback(Value())
            print(isinstance(normal_result, Value), isinstance(static_result, Value), class_result is Child, isinstance(callable_result, Value))
        """),
    )
    assert execute(project, source) == "True True True True\n"
    pymodule = project.get_pymodule(source)
    for result in ["normal_result", "static_result", "callable_result"]:
        assert (
            pymodule[result].get_object().get_type() is pymodule["Value"].get_object()
        )
    assert pymodule["class_result"].get_object() is pymodule["Child"].get_object()
    project.pycore.analyze_module(source)
    manager = project.pycore.object_info
    for class_name, method, receiver, receiver_type in [
        ("Base", "normal", "self", "Child"),
        ("Base", "static", None, None),
        ("Base", "class_method", "cls", "Child"),
        ("Callable", "__call__", "self", "Callable"),
    ]:
        function = pymodule[class_name].get_object()[method].get_object()
        assert manager._get_call_scope(function) != manager._get_scope(function)
        for passed in function.get_parameters()["value"].get_objects():
            assert passed.get_type() is pymodule["Value"].get_object()
        if receiver is not None:
            for passed in function.get_parameters()[receiver].get_objects():
                actual = passed if receiver == "cls" else passed.get_type()
                assert actual is pymodule[receiver_type].get_object()


@pytest.mark.parametrize("selected", ["formal", "body"])
def test_defaulted_positional_parameter_rename_keeps_its_declaration(project, selected):
    source = module(
        project,
        dedent("""\
            target = int
            def func(target=target, /, **extras):
                return target, extras["target"]
            result = func(str, target=bytes)
            print(result[0] is str, result[1] is bytes, target is int)
        """),
    )
    before = source.read()
    assert execute(project, source) == "True True True\n"
    pymodule = project.get_pymodule(source)
    function = pymodule["func"].get_object()
    parameter = function.get_parameters()["target"]
    formal_offset = before.index("target=target")
    for delta in [0, 1, 5]:
        assert evaluate.eval_location(pymodule, formal_offset + delta) is parameter
    body_offset = before.index("return target") + len("return ") + 1
    assert evaluate.eval_location(pymodule, body_offset) is parameter
    assert (
        evaluate.eval_location(pymodule, formal_offset + len("target=") + 1)
        is pymodule["target"]
    )
    assert evaluate.eval_location(pymodule, before.index("target=bytes") + 1) is None
    offset = formal_offset if selected == "formal" else body_offset
    project.do(rename.Rename(project, source, offset).get_changes("local"))
    assert execute(project, source) == "True True True\n"
    assert "func(local=target, /, **extras)" in source.read()
    assert "target=bytes" in source.read()


def test_default_and_same_line_body_call_keywords_keep_callee_identity(project):
    source = module(
        project,
        dedent("""\
            def build(*, target):
                return target
            def func(target=build(target=int), /): return build(target=target)
            print(func() is int, func(str) is str)
        """),
    )
    before = source.read()
    assert execute(project, source) == "True True\n"
    pymodule = project.get_pymodule(source)
    parameter = pymodule["build"].get_object().get_parameters()["target"]
    for keyword in ["target=int", "target=target)"]:
        assert evaluate.eval_location(pymodule, before.index(keyword) + 1) is parameter
    project.do(
        rename.Rename(
            project, source, before.index("*, target") + len("*, ") + 1
        ).get_changes("value")
    )
    assert execute(project, source) == "True True\n"
    assert (
        "func(target=build(value=int), /): return build(value=target)" in source.read()
    )


@pytest.mark.parametrize(
    "parameters,display,without_self",
    [
        ('self: "C", value: int = 1', "self, value=1", "value=1"),
        ('self: "C", /', 'self: "C", /', ""),
        (
            'self: "C", /, value: int = 1',
            'self: "C", /, value: int = 1',
            "value: int = 1",
        ),
        (
            'self: "C", value: int = 1, /, *, key: str = "ok"',
            'self: "C", value: int = 1, /, *, key: str = "ok"',
            'value: int = 1, /, *, key: str = "ok"',
        ),
        (
            'self: "C", *, value: int = 1',
            'self: "C", *, value: int = 1',
            "*, value: int = 1",
        ),
    ],
)
def test_calltip_preserves_ordinary_display_and_parameter_separators(
    project, parameters, display, without_self
):
    result = "value" if "value" in parameters else "1"
    source = module(
        project,
        dedent(f'''\
            class C:
                def f({parameters}):
                    """Details."""
                    return {result}
            print(C().f())
        '''),
    )
    code = source.read()
    assert execute(project, source) == "1\n"
    offset = code.rindex(".f(") + 1
    assert (
        get_calltip(project, code, offset, resource=source) == f"source.C.f({display})"
    )
    assert (
        get_calltip(project, code, offset, resource=source, remove_self=True)
        == f"source.C.f({without_self})"
    )
    doc = get_doc(project, code, offset, resource=source)
    assert doc.splitlines()[0] == f"C.f({display}):"


@pytest.mark.parametrize(
    "parameters",
    [
        'self: "C"=((None)), /, *, payload=2',
        'self: ("C")=((lambda a, b: None)(None, None)), /, *, payload=2',
    ],
)
def test_calltip_removes_complete_parenthesized_receiver(project, parameters):
    source = module(
        project,
        dedent(f'''\
            class C:
                def f({parameters}):
                    """Details."""
                    return payload
            print(C().f())
        '''),
    )
    code = source.read()
    assert execute(project, source) == "2\n"
    offset = code.rindex(".f(") + 1
    assert (
        get_calltip(project, code, offset, resource=source)
        == f"source.C.f({parameters})"
    )
    assert (
        get_calltip(project, code, offset, resource=source, remove_self=True)
        == "source.C.f(*, payload=2)"
    )
    assert (
        get_doc(project, code, offset, resource=source).splitlines()[0]
        == f"C.f({parameters}):"
    )


@pytest.mark.parametrize(
    "declaration,decorator,parameters",
    [
        ("", "staticmethod", "value, /"),
        ("", "staticmethod", "value"),
        ("static = staticmethod", "static", "value, /"),
        ("from builtins import staticmethod as static", "static", "value, /"),
        ("first = staticmethod; static = first", "static", "value, /"),
        ("import builtins as namespace", "namespace.staticmethod", "value, /"),
    ],
)
def test_static_parameter_attributes_do_not_belong_to_owner(
    project, declaration, decorator, parameters
):
    source = module(
        project,
        dedent(f"""\
            class Value:
                pass
            class Owner:
                {declaration}
                @{decorator}
                def assign({parameters}):
                    value.field = 42
                    pass
            value = Value()
            Owner.assign(value)
            print(value.field)
            try:
                print(Owner.field)
            except AttributeError:
                print("absent")
        """),
    )
    before = source.read()
    assert execute(project, source) == "42\nabsent\n"
    owner = project.get_pymodule(source)["Owner"].get_object()
    owner.get_scope().get_defined_names()
    assert owner["assign"].get_object().get_kind() == "staticmethod"
    assert "field" not in owner.get_attributes()
    offset = before.index("print(Owner.field)") + len("print(Owner.") + 1
    with pytest.raises(exceptions.RefactoringError):
        inline.create_inline(project, source, offset).get_changes()
    assert source.read() == before
    assert execute(project, source) == "42\nabsent\n"


@pytest.mark.parametrize(
    "declaration,decorator,receiver,call,kind",
    [
        ("", "", "self", "owner.assign()", "method"),
        ("", "@classmethod", "cls", "Owner.assign()", "classmethod"),
        (
            "class_method = classmethod",
            "@class_method",
            "cls",
            "Owner.assign()",
            "classmethod",
        ),
        (
            "import builtins as namespace",
            "@namespace.classmethod",
            "cls",
            "Owner.assign()",
            "classmethod",
        ),
        (
            "def staticmethod(func): return func",
            "@staticmethod",
            "self",
            "owner.assign()",
            "method",
        ),
    ],
)
def test_receiver_attributes_survive_kind_resolution_and_early_scope_access(
    project, declaration, decorator, receiver, call, kind
):
    inspected = "Owner" if receiver == "cls" else "owner"
    source = module(
        project,
        dedent(f"""\
            class Owner:
                {declaration}
                {decorator}
                def assign({receiver}, /):
                    {receiver}.field = 42
            owner = Owner()
            {call}
            print({inspected}.field)
        """),
    )
    assert execute(project, source) == "42\n"
    owner = project.get_pymodule(source)["Owner"].get_object()
    owner.get_scope().get_defined_names()
    assert owner["assign"].get_object().get_kind() == kind
    assert "field" in owner.get_attributes()
    assert (
        owner["field"].get_object().get_type() is builtins.builtins["int"].get_object()
    )
    assert execute(project, source) == "42\n"


def test_explicit_unknown_argument_does_not_use_default(project):
    source = module(
        project,
        dedent("""\
            def supply():
                return eval("str")
            def func(*, value=int):
                return value
            result = func(value=supply())
            print(result is str, func() is int)
        """),
    )
    assert execute(project, source) == "True True\n"
    pymodule = project.get_pymodule(source)
    function = pymodule["func"].get_object()
    call = pymodule.get_ast().body[-2].value
    actual = arguments.create_arguments(None, function, call, pymodule.get_scope())
    value = actual.get_arguments(function.get_param_names(False))[0]
    assert value is None or value is not builtins.builtins["int"].get_object()
    assert pymodule["result"].get_object() is not builtins.builtins["int"].get_object()


def test_variadic_method_with_no_ordinary_slots_keeps_receiver_in_items(project):
    source = module(
        project,
        dedent("""\
            class Owner:
                def func(*items):
                    return items[0]
            owner = Owner()
            result = owner.func()
            print(result is owner)
        """),
    )
    assert execute(project, source) == "True\n"
    pymodule = project.get_pymodule(source)
    function = pymodule["Owner"].get_object()["func"].get_object()
    actual = arguments.create_arguments(
        pymodule["owner"],
        function,
        pymodule.get_ast().body[-2].value,
        pymodule.get_scope(),
    )
    assert function.get_param_names(False) == []
    assert actual.get_arguments(function.get_param_names(False)) == []
    assert isinstance(
        function.get_parameters()["items"].get_object().get_type(), builtins.List
    )
    assert execute(project, source) == "True\n"


@pytest.mark.parametrize("record_size", [1, 3])
def test_persisted_wrong_size_calls_do_not_poison_readers_or_fallback(
    tmp_path, record_size
):
    folder = str(tmp_path)
    project = Project(
        folder, save_objectdb=True, save_history=False, automatic_soa=False
    )
    source = module(
        project,
        dedent("""\
            class Pos:
                pass
            class Key:
                pass
            class Wrong:
                pass
            def func(pos, /, *, key):
                return key
            print(func(Pos, key=Key) is Key)
        """),
    )
    assert execute(project, source) == "True\n"
    pymodule = project.get_pymodule(source)
    function = pymodule["func"].get_object()
    manager = project.pycore.object_info
    path, key = manager._get_call_scope(function)
    wrong = manager.to_textual(pymodule["Wrong"].get_object())
    manager.objectdb.add_callinfo(path, key, (wrong,) * record_size, wrong)
    project.close()
    reopened = Project(
        folder, save_objectdb=True, save_history=False, automatic_soa=False
    )
    try:
        source = reopened.get_file("source.py")
        pymodule = reopened.get_pymodule(source)
        function = pymodule["func"].get_object()
        manager = reopened.pycore.object_info
        call = pymodule.get_ast().body[-1].value.args[0].left
        actual = arguments.create_arguments(None, function, call, pymodule.get_scope())
        assert manager.get_parameter_objects(function) is None
        assert manager.get_passed_objects(function, 0) == []
        assert manager.get_passed_objects(function, 1) == []
        assert manager.get_returned(function, None) is None
        assert manager.get_exact_returned(function, actual) is None
        pos, expected = pymodule["Pos"].get_object(), pymodule["Key"].get_object()
        manager.function_called(function, [pos], expected)
        assert manager.get_returned(function, None) is None
        manager.function_called(function, [pos, expected], expected)
        assert manager.get_parameter_objects(function) == [pos, expected]
        assert manager.get_passed_objects(function, 1) == [expected]
        assert manager.get_passed_objects(function, 2) == []
        assert manager.get_returned(function, None) is expected
        assert manager.get_exact_returned(function, actual) is expected
        assert execute(reopened, source) == "True\n"
    finally:
        reopened.close()


def test_calltip_without_positional_receiver_keeps_keyword_only_parameter(project):
    source = module(
        project,
        dedent("""\
            class Owner:
                def func(*, value: int = 2):
                    return value
            print(Owner.func(value=2))
        """),
    )
    code = source.read()
    assert execute(project, source) == "2\n"
    offset = code.rindex(".func(") + 1
    assert get_calltip(project, code, offset, resource=source, remove_self=True) == (
        "source.Owner.func(*, value: int = 2)"
    )


def test_direct_inline_parameter_on_assignment_preserves_runtime(project):
    source = module(project, "target = int\nprint(target is int)\n")
    before = source.read()
    assert execute(project, source) == "True\n"
    with pytest.raises(exceptions.RefactoringError):
        inline.InlineParameter(project, source, before.index("target") + 1)
    assert source.read() == before
    assert execute(project, source) == "True\n"
