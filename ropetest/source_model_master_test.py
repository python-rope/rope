"""Source identities on the unmodified ordinary-function argument protocol."""

import sys
import typing
from textwrap import indent

import pytest

from rope.base import ast, evaluate, exceptions, pyobjects
from rope.base.project import Project
from rope.contrib import codeassist, finderrors
from rope.refactor import introduce_parameter, rename


@pytest.fixture
def model_project(tmp_path):
    project = Project(
        str(tmp_path), save_objectdb=False, save_history=False, automatic_soa=False
    )
    yield project
    project.close()


def module(project, source):
    resource = project.root.create_file("subject.py")
    resource.write(source)
    return resource


def prefix(mode):
    if mode == "eager" and sys.version_info >= (3, 14):
        pytest.skip("eager function annotations require Python before 3.14")
    if mode == "lazy" and sys.version_info < (3, 14):
        pytest.skip("lazy function annotations require Python 3.14")
    return "from __future__ import annotations\n" if mode == "future" else ""


def observe(source):
    namespace = {"__name__": "fixture"}
    exec(compile(source, "fixture.py", "exec"), namespace)
    return namespace["drive"](), tuple(
        typing.get_type_hints(namespace["subject"]).values()
    )


@pytest.mark.parametrize("mode", ["eager", "future", "lazy"])
@pytest.mark.parametrize("owner", ["module", "class", "nested"])
@pytest.mark.parametrize("operation", ["outer", "formal"])
def test_existing_rename_api_keeps_runtime_annotation_contract(
    model_project, mode, owner, operation
):
    source = prefix(mode) + "target = int\n"
    definition = "def func(target: target) -> target:\n    return target\n"
    if owner == "module":
        source += definition + "subject = func\n"
        outer = source.index("target = int")
    elif owner == "class":
        source += "class Owner:\n" + indent("target = bytes\n" + definition, "    ")
        source += "subject = Owner.func\n"
        outer = source.index("target = bytes")
    else:
        source += "def owner():\n" + indent("target = bytes\n" + definition, "    ")
        source += "    return func\nsubject = owner()\n"
        outer = source.index("target = bytes")
    source += "def drive():\n    return subject(str)\n"
    before = observe(source)
    resource = module(model_project, source)
    offset = (
        outer
        if operation == "outer"
        else source.index("target", source.index("def func("))
    )
    changes = rename.Rename(model_project, resource, offset).get_changes("renamed")
    model_project.do(changes)
    assert observe(resource.read()) == before


@pytest.mark.parametrize(
    "signature,call",
    [("target", "str"), ("target, /", "str"), ("*, target", "target=str")],
)
def test_lambda_formal_rename_preserves_keyword_driver(model_project, signature, call):
    source = f"target = int\ncallback = lambda {signature}: target\nresult = callback({call})\n"
    namespace = {}
    exec(source, namespace)
    before = namespace["result"]
    resource = module(model_project, source)
    offset = source.index("target", source.index("lambda "))
    changes = rename.Rename(model_project, resource, offset).get_changes("renamed")
    model_project.do(changes)
    namespace = {}
    exec(resource.read(), namespace)
    assert namespace["result"] is before is str
    assert "target = int" in resource.read()


@pytest.mark.parametrize(
    "expression",
    [
        "[target for target in [str]]",
        "{target for target in [str]}",
        "{target: target for target in [str]}",
        "tuple(target for target in [str])",
    ],
)
def test_outer_rename_does_not_capture_comprehension_local(model_project, expression):
    source = f"target = int\nvalue = {expression}\nresult = (target, value)\n"
    before = {}
    exec(source, before)
    resource = module(model_project, source)
    changes = rename.Rename(model_project, resource, 0).get_changes("renamed")
    model_project.do(changes)
    after = {}
    exec(resource.read(), after)
    assert after["result"] == before["result"]
    assert "for target in" in resource.read()


@pytest.mark.parametrize(
    "signature,call", [("target, /", "str"), ("*, target", "target=str")]
)
def test_unsupported_ordinary_formals_have_readable_distinct_bindings(
    model_project, signature, call
):
    source = f"target = int\ndef func({signature}):\n    return target\nresult = (target, func({call}))\n"
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    function = pymodule["func"].get_object()
    formal_offset = source.index("target", source.index("def func("))
    binder = evaluate.eval_location(pymodule, formal_offset)
    assert binder is not None and binder is not pymodule["target"]
    assert not binder.is_refactoring_identity_safe
    assert binder.get_object() is pyobjects.get_unknown()
    assert (
        evaluate.eval_location(
            pymodule, source.index("target", source.index("return "))
        )
        is binder
    )
    assert function.get_parameters() == {}
    assert function.get_param_names() == []
    assert codeassist.get_definition_location(
        model_project, source, formal_offset, resource
    ) == (resource, 2)
    assert finderrors.find_errors(model_project, resource) == []
    for offset in (formal_offset, source.index("target", source.index("return "))):
        with pytest.raises(
            exceptions.RefactoringError, match="unresolved source binding"
        ):
            rename.Rename(model_project, resource, offset).get_changes("renamed")
        assert resource.read() == source
    changes = rename.Rename(model_project, resource, 0).get_changes("outer")
    model_project.do(changes)
    namespace = {}
    exec(resource.read(), namespace)
    assert namespace["result"] == (int, str)
    assert "return target" in resource.read()


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("(lambda target=str: target)()", "str"),
        ("(lambda *, target=str: target)()", "str"),
        ("(lambda target=int, /, **kw: target)(target=str)", "int"),
        ("(lambda target: target)(str)", "str"),
        ("(lambda *, target: target)(target=str)", "str"),
        ("(lambda target=int: target)(*[str])", None),
        ("(lambda target=int: target)(**{'target': str})", None),
        ("(lambda target: target)(str, target=int)", None),
        ("(lambda target: target)(str, **{'target': int})", None),
        ("(lambda target: target)(*[str], target=int)", None),
        ("(lambda target=int: target)(missing)", None),
    ],
)
def test_lambda_private_matching_does_not_use_ordinary_function_api(
    model_project, expression, expected
):
    source = "result = " + expression + "\n"
    pymodule = model_project.get_pymodule(module(model_project, source))
    result = pymodule["result"].get_object()
    if expected is None:
        assert result is pyobjects.get_unknown()
    else:
        from rope.base import builtins

        assert result is builtins.builtins[expected].get_object()
    node = next(n for n in ast.walk(pymodule.get_ast()) if isinstance(n, ast.Lambda))
    function = pymodule.get_source_binding_index().callable_for_node(node)
    canonical = function.get_parameters()["target"]
    assert canonical.get_object() is pyobjects.get_unknown()
    model_project.pycore.module_cache.forget_all_data()
    assert function.get_parameters()["target"] is canonical


@pytest.mark.parametrize(
    "expression",
    [
        "Owner().callback(item=Other()).field",
        "Owner.callback(Other(), item=Owner()).field",
        "Owner().callback(Other()).field",
    ],
)
def test_lambda_descriptor_field_rename_keeps_receiver(model_project, expression):
    source = (
        "class Other:\n    field = 2\nclass Owner:\n    field = 1\n    callback = lambda self, item: self\nresult = "
        + expression
        + "\n"
    )
    before = {}
    exec(source, before)
    resource = module(model_project, source)
    changes = rename.Rename(
        model_project, resource, source.index("field = 1")
    ).get_changes("renamed")
    model_project.do(changes)
    after = {}
    exec(resource.read(), after)
    assert after["result"] == before["result"]
    assert "field = 2" in resource.read()


@pytest.mark.parametrize(
    "source",
    [
        "target = str\ndef func(target=target):\n    return target\n",
        "target = str\ndef func(target: target):\n    return target\n",
    ],
)
def test_first_function_names_do_not_visit_header_into_local_scope(
    model_project, source
):
    pymodule = model_project.get_pymodule(module(model_project, source))
    scope = pymodule["func"].get_object().get_scope()
    formal = scope.pyobject.get_parameters()["target"]
    assert scope.get_names()["target"] is formal
    assert scope.lookup("target") is formal
    assert (
        evaluate.eval_location(
            pymodule, source.index("target", source.index("return "))
        )
        is formal
    )
    assert (
        evaluate.eval_location(
            pymodule,
            (
                source.index("target", source.index("target=") + 7)
                if "target=" in source
                else source.index("target", source.index(": target"))
            ),
        )
        is pymodule["target"]
    )


def test_introduce_parameter_keeps_structural_body_and_refuses_lambda(model_project):
    source = (
        "value = 1\ndef func():\n    callback = lambda item: value\n    return value\n"
    )
    resource = module(model_project, source)
    with pytest.raises(exceptions.RefactoringError, match="inside functions"):
        introduce_parameter.IntroduceParameter(
            model_project, resource, source.index("item", source.index("lambda"))
        )
    capture = introduce_parameter.IntroduceParameter(
        model_project, resource, source.index("value", source.index("lambda"))
    )
    model_project.do(capture.get_changes("captured"))
    assert "def func(captured=value)" in resource.read()
    assert "lambda item: captured" in resource.read()
    resource.write(source)
    operation = introduce_parameter.IntroduceParameter(
        model_project, resource, source.index("value", source.index("return"))
    )
    model_project.do(operation.get_changes("provided"))
    assert "def func(provided=value)" in resource.read()
    assert "lambda item: provided" in resource.read()


@pytest.mark.parametrize(
    "signature", ["target", "target, /", "*, target", "*target", "**target"]
)
def test_source_lambda_index_keeps_all_formal_identities_across_cache_reset(
    model_project, signature
):
    source = f"target = int\ncallback = lambda {signature}: target\n"
    pymodule = model_project.get_pymodule(module(model_project, source))
    index = pymodule.get_source_binding_index()
    node = next(n for n in ast.walk(pymodule.get_ast()) if isinstance(n, ast.Lambda))
    callable_ = index.callable_for_node(node)
    binder = callable_.get_parameters()["target"]
    offset = source.index("target", source.index("lambda"))
    assert index.binding_for_token(offset) is binder
    assert evaluate.eval_location(pymodule, offset) is binder
    body_offset = source.rindex("target")
    assert evaluate.eval_location(pymodule, body_offset) is binder
    assert binder is not pymodule["target"]
    assert index.context_at(body_offset).structural_scope is pymodule.get_scope()
    model_project.pycore.module_cache.forget_all_data()
    assert pymodule.get_source_binding_index() is index
    assert callable_.get_parameters()["target"] is binder
    assert evaluate.eval_location(pymodule, body_offset) is binder


@pytest.mark.parametrize(
    "source,offset_text",
    [
        ("target = int\ndef func(target: target):\n    return target\n", ": target"),
        ("target = int\ndef func(target=target):\n    return target\n", "=target"),
        ("target = int\ncallback = lambda target=target: target\n", "=target"),
    ],
)
def test_change_occurrences_uses_structure_or_canonical_expression_scope(
    model_project, source, offset_text
):
    resource = module(model_project, source)
    offset = source.index(offset_text) + 1
    if source[offset] == " ":
        offset += 1
    operation = rename.ChangeOccurrences(model_project, resource, offset)
    model_project.do(operation.get_changes("changed"))
    if "def func" in source:
        assert "target = int" in resource.read()
        assert (
            "target: changed" in resource.read() or "target=changed" in resource.read()
        )
    else:
        assert "changed = int" in resource.read()
    assert "return target" in resource.read() or ": target" in resource.read()


@pytest.mark.parametrize("kind", ["global", "nonlocal"])
def test_header_named_expression_uses_declared_owner_before_first_lookup(
    model_project, kind
):
    if kind == "global":
        source = "target = int\ndef owner():\n    global target\n    def inner(value=(target := str)):\n        return target\n    return inner\nresult = owner()()\n"
        owner_offset = source.index("target = int")
    else:
        source = "def enclosing():\n    target = int\n    def owner():\n        nonlocal target\n        def inner(value=(target := str)):\n            return target\n        return inner\n    return owner()\nresult = enclosing()()\n"
        owner_offset = source.index("target = int")
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    binder = evaluate.eval_location(pymodule, owner_offset)
    walrus = source.index("target :=")
    assert evaluate.eval_location(pymodule, walrus) is binder
    model_project.do(
        rename.Rename(model_project, resource, owner_offset).get_changes("renamed")
    )
    namespace = {}
    exec(resource.read(), namespace)
    assert namespace["result"] is str
    assert "target" not in resource.read()


@pytest.mark.skipif(
    sys.version_info < (3, 12), reason="type aliases require Python 3.12"
)
def test_alias_own_parameter_is_distinct_and_rename_keeps_runtime_value(model_project):
    source = "T = int\ntype Alias[T] = tuple[T, T]\nresult = Alias.__value__\n"
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    own_offset = source.index("[T]") + 1
    binder = evaluate.eval_location(pymodule, own_offset)
    assert binder is not pymodule["T"]
    assert evaluate.eval_location(pymodule, source.index("[T, T]") + 1) is binder
    model_project.do(
        rename.Rename(model_project, resource, own_offset).get_changes("V")
    )
    namespace = {}
    exec(resource.read(), namespace)
    alias = namespace["Alias"]
    assert namespace["T"] is int
    assert alias.__value__.__args__ == (
        alias.__type_params__[0],
        alias.__type_params__[0],
    )


@pytest.mark.skipif(
    sys.version_info < (3, 12), reason="type parameters require Python 3.12"
)
def test_generic_class_collision_uses_opaque_source_and_refuses_atomically(
    model_project,
):
    source = "T = int\nclass Owner[T]:\n    T = str\n    def method(self, value: T):\n        return value\n"
    resource = module(model_project, source)
    for offset in (source.index("[T]") + 1, source.index("T = str")):
        with pytest.raises(exceptions.RefactoringError, match="unresolved"):
            rename.Rename(model_project, resource, offset).get_changes("V")
        assert resource.read() == source


@pytest.mark.parametrize("signature", ["target, /", "*, target"])
def test_introduce_parameter_refuses_unsupported_ordinary_signature_atomically(
    model_project, signature
):
    source = f"value = int\ndef func({signature}):\n    return value\n"
    resource = module(model_project, source)
    operation = introduce_parameter.IntroduceParameter(
        model_project, resource, source.index("value", source.index("return"))
    )
    with pytest.raises(
        exceptions.RefactoringError, match="unsupported parameter categories"
    ):
        operation.get_changes("provided")
    assert resource.read() == source


@pytest.mark.parametrize(
    "source",
    [
        "target = int\ncallback = lambda target: target\n",
        "target = int\nresult = [target for target in [str]]\n",
    ],
)
def test_completion_follows_canonical_expression_environment(model_project, source):
    resource = module(model_project, source)
    offset = (
        source.index("target", source.index(": target") + 2) + 3
        if "lambda" in source
        else source.index("target", source.index("result")) + 3
    )
    proposals = codeassist.code_assist(
        model_project, source, offset, resource=resource, later_locals=False
    )
    assert "target" in {proposal.name for proposal in proposals}
    assert finderrors.find_errors(model_project, resource) == []


def test_old_offset_scope_remains_structural_while_index_resolves_comp_identity(
    model_project,
):
    source = "target = int\nresult = [target for target in [str]]\n"
    pymodule = model_project.get_pymodule(module(model_project, source))
    scope = pymodule.get_scope()
    offset = source.index("target", source.index("result"))
    assert scope.get_inner_scope_for_offset(offset) is scope.get_scopes()[0]
    assert scope.get_structural_scope_for_offset(offset) is scope.get_scopes()[0]
    canonical = pymodule.get_source_binding_index().context_at(offset).environment
    assert canonical is not scope.get_scopes()[0]
    assert evaluate.eval_location(pymodule, offset) is canonical.lookup("target")
    assert evaluate.eval_location(pymodule, offset) is not pymodule["target"]


@pytest.mark.parametrize("class_first", [False, True])
@pytest.mark.parametrize("class_return", ["self", "item", "static"])
@pytest.mark.parametrize("access", ["direct", "saved", "class", "class-saved"])
@pytest.mark.parametrize("renamed_owner", ["Owner", "Other"])
def test_lambda_storage_view_selects_instance_and_class_values_independently(
    model_project, class_first, class_return, access, renamed_owner
):
    initializer = (
        "    def __init__(self):\n"
        "        self.field = 1\n"
        "        self.callback = lambda item: item\n"
    )
    class_value = (
        "    callback = staticmethod(lambda item: item)\n"
        if class_return == "static"
        else f"    callback = lambda self, item: {class_return}\n"
    )
    source = "class Owner:\n" + (
        class_value + initializer if class_first else initializer + class_value
    )
    source += "class Other:\n    def __init__(self):\n        self.field = 2\n"
    if access == "direct":
        source += "result = Owner().callback(Other())\n"
    elif access == "saved":
        source += "saved = Owner().callback\nresult = saved(Other())\n"
    elif access == "class":
        source += (
            "result = Owner.callback(Other())\n"
            if class_return == "static"
            else "result = Owner.callback(Owner(), Other())\n"
        )
    else:
        source += "saved = Owner.callback\n"
        source += (
            "result = saved(Other())\n"
            if class_return == "static"
            else "result = saved(Owner(), Other())\n"
        )
    source += "observed = result.field\n"
    before = {}
    exec(compile(source, "storage_fixture.py", "exec"), before)
    expected_owner = (
        "Owner"
        if access in {"class", "class-saved"} and class_return == "self"
        else "Other"
    )
    assert before["observed"] == (1 if expected_owner == "Owner" else 2)
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    # Reading either namespace first must not change the other value view.
    first = "Owner.callback" if class_first else "Owner().callback"
    second = "Owner().callback" if class_first else "Owner.callback"
    first_view = evaluate.eval_str(pymodule.get_scope(), first)
    first_function = first_view.get_object()
    first_parameters = first_function.get_parameters()
    second_view = evaluate.eval_str(pymodule.get_scope(), second)
    second_function = second_view.get_object()
    assert first_function.source_function is not second_function.source_function
    assert first_view.get_object() is first_function
    assert first_function.get_parameters() == first_parameters
    assert (
        evaluate.eval_str(pymodule.get_scope(), first).get_object().source_function
        is first_function.source_function
    )
    # Repeat in the opposite order on the same module and keep both views alive.
    reversed_second = evaluate.eval_str(pymodule.get_scope(), second)
    reversed_first = evaluate.eval_str(pymodule.get_scope(), first)
    assert (
        reversed_second.get_object().source_function is second_function.source_function
    )
    assert reversed_first.get_object().source_function is first_function.source_function
    assert second_view.get_object() is second_function
    field_value = "1" if renamed_owner == "Owner" else "2"
    offset = source.index("self.field = " + field_value) + len("self.")
    model_project.do(
        rename.Rename(model_project, resource, offset).get_changes("changed")
    )
    after = {}
    exec(compile(resource.read(), "storage_fixture.py", "exec"), after)
    assert after["observed"] == before["observed"]
    assert ("observed = result.changed" in resource.read()) == (
        renamed_owner == expected_owner
    )
