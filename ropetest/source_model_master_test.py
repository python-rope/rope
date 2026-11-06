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


def runtime_observed(source):
    namespace = {}
    exec(compile(source, "source_contract.py", "exec", dont_inherit=True), namespace)
    return namespace["observed"]


@pytest.mark.parametrize(
    "factory",
    [
        "lambda supplied: (lambda *, option=None: supplied)",
        "lambda supplied: (lambda option=supplied: option)",
    ],
)
@pytest.mark.parametrize("renamed", ["first_field", "second_field"])
def test_lambda_creation_values_are_isolated_between_calls(
    model_project, factory, renamed
):
    source = (
        "class First:\n    first_field = 11\n"
        "class Second:\n    second_field = 22\n"
        f"factory = {factory}\n"
        "first = factory(First())\nsecond = factory(Second())\n"
        "observed = (first().first_field, second().second_field)\n"
    )
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    first = evaluate.eval_str(pymodule.get_scope(), "first")
    second = evaluate.eval_str(pymodule.get_scope(), "second")
    assert first.get_object().source_function is second.get_object().source_function
    assert first.get_object() is not second.get_object()
    for expression, expected in [("second()", "Second"), ("first()", "First")]:
        assert evaluate.eval_str(
            pymodule.get_scope(), expression
        ).get_object().get_type() is (pymodule[expected].get_object())
    inner = first.get_object().source_function
    assert inner.get_parameters()["option"].get_object() is pyobjects.get_unknown()
    model_project.pycore.module_cache.forget_all_data()
    assert inner.get_parameters()["option"].get_object() is pyobjects.get_unknown()
    before = runtime_observed(source)
    model_project.do(
        rename.Rename(
            model_project, resource, source.index(renamed + " =")
        ).get_changes("changed")
    )
    assert runtime_observed(resource.read()) == before == (11, 22)
    other = "second_field" if renamed == "first_field" else "first_field"
    assert f".{other}" in resource.read()


@pytest.mark.parametrize(
    "expression",
    [
        "[value for value in (item,)][0]",
        "[second for first, second in ((None, item),)][0]",
        "[second for first in (item,) for second in (first,)][0]",
        "{key: value for key, value in ((0, item),)}[0]",
    ],
)
@pytest.mark.parametrize("renamed_owner", ["Payload", "Other"])
def test_comprehension_call_overlay_drives_field_rename(
    model_project, expression, renamed_owner
):
    source = (
        "class Payload:\n    field = 42\n"
        "class Other:\n    field = 99\n"
        f"callback = lambda item: {expression}\n"
        "result = callback(Payload())\nobserved = result.field\n"
    )
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    callback = pymodule["callback"].get_object()
    parameter = callback.get_parameters()["item"]
    assert (
        pymodule["result"].get_object().get_type() is pymodule["Payload"].get_object()
    )
    assert parameter.get_object() is pyobjects.get_unknown()
    model_project.pycore.module_cache.forget_all_data()
    assert callback.get_parameters()["item"] is parameter
    assert parameter.get_object() is pyobjects.get_unknown()
    before = runtime_observed(source)
    declaration = "field = 42" if renamed_owner == "Payload" else "field = 99"
    model_project.do(
        rename.Rename(model_project, resource, source.index(declaration)).get_changes(
            "changed"
        )
    )
    assert runtime_observed(resource.read()) == before == 42
    assert ("observed = result.changed" in resource.read()) == (
        renamed_owner == "Payload"
    )


@pytest.mark.parametrize(
    "descriptor,body",
    [
        ("lambda self, item: self", "Owner"),
        ("staticmethod(lambda item: item)", "Other"),
        ("classmethod(lambda cls, item: item)", "Other"),
    ],
)
def test_saved_lambda_keyword_rename_keeps_descriptor_and_source_identity(
    model_project, descriptor, body
):
    source = (
        "class Owner:\n    field = 1\n"
        f"    callback = {descriptor}\n"
        "class Other:\n    field = 2\n"
        "saved = Owner().callback\nresult = saved(item=Other())\n"
        "observed = result.field\n"
    )
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    offset = source.index("item=Other()")
    function = pymodule["saved"].get_object()
    parameter = function.get_parameters()["item"]
    assert evaluate.eval_location(pymodule, offset) is parameter
    assert codeassist.get_definition_location(
        model_project, source, offset, resource
    ) == (resource, 3)
    assert pymodule["result"].get_object().get_type() is pymodule[body].get_object()
    assert parameter.get_object() is pyobjects.get_unknown()
    before = runtime_observed(source)
    model_project.do(
        rename.Rename(model_project, resource, offset).get_changes("changed")
    )
    assert "saved(changed=Other())" in resource.read()
    assert runtime_observed(resource.read()) == before


@pytest.mark.parametrize("kind", ["closure", "saved-bound"])
@pytest.mark.parametrize("renamed_owner", ["Owner", "Other"])
def test_saved_bound_lambda_is_not_bound_again(model_project, kind, renamed_owner):
    source = (
        "class Owner:\n    field = 1\n"
        "    callback = lambda self, item: "
        + ("(lambda: self)\n" if kind == "closure" else "self\n")
        + "class Other:\n    field = 2\n"
    )
    source += (
        "saved = Owner().callback\nresult = saved(Other())()\n"
        if kind == "closure"
        else "class Saved:\n    callback = Owner().callback\nresult = Saved().callback(Other())\n"
    )
    source += "observed = result.field\n"
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    assert pymodule["result"].get_object().get_type() is pymodule["Owner"].get_object()
    before = runtime_observed(source)
    offset = source.index("field = " + ("1" if renamed_owner == "Owner" else "2"))
    model_project.do(
        rename.Rename(model_project, resource, offset).get_changes("changed")
    )
    assert runtime_observed(resource.read()) == before == 1
    assert ("observed = result.changed" in resource.read()) == (
        renamed_owner == "Owner"
    )


@pytest.mark.parametrize("owner", ["module", "class", "global", "nonlocal-parameter"])
def test_header_created_name_is_queryable_before_and_after_cache_reset(
    model_project, owner
):
    if owner == "module":
        source = "def inner(value=(target := str)):\n    return target\nobserved = inner() is str\n"
    elif owner == "class":
        source = "class Owner:\n    def inner(value=(target := str)):\n        return value\nobserved = Owner.target is str and Owner.inner() is str\n"
    elif owner == "global":
        source = "def owner():\n    global target\n    def inner(value=(target := str)):\n        return target\n    return inner\nobserved = owner()() is str and target is str\n"
    else:
        source = "def enclosing(target):\n    def owner():\n        nonlocal target\n        def inner(value=(target := str)):\n            return target\n        return inner\n    return owner()\nobserved = enclosing(int)() is str\n"
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    offset = source.index("target :=")
    binder = evaluate.eval_location(pymodule, offset)
    assert binder is not None
    location = codeassist.get_definition_location(
        model_project, source, offset, resource
    )
    assert location[0] == resource
    model_project.pycore.module_cache.forget_all_data()
    assert evaluate.eval_location(pymodule, offset) is binder
    assert (
        codeassist.get_definition_location(model_project, source, offset, resource)
        == location
    )
    before = runtime_observed(source)
    model_project.do(
        rename.Rename(model_project, resource, offset).get_changes("changed")
    )
    assert runtime_observed(resource.read()) == before is True
    assert "target" not in resource.read()


@pytest.mark.parametrize("selection", ["module", "lambda", "comprehension"])
def test_nested_lambda_comprehension_shadowing_rename_preserves_each_binding(
    model_project, selection
):
    source = (
        "target = int\n"
        "result = (lambda *, target: [target for target in target])(target=(str, bytes))\n"
        "observed = (target is int, result == [str, bytes])\n"
    )
    resource = module(model_project, source)
    markers = {
        "module": "target = int",
        "lambda": "target:",
        "comprehension": "for target",
    }
    offset = source.index(markers[selection]) + (
        4 if selection == "comprehension" else 0
    )
    before = runtime_observed(source)
    model_project.do(
        rename.Rename(model_project, resource, offset).get_changes("changed")
    )
    assert runtime_observed(resource.read()) == before == (True, True)
    if selection == "lambda":
        assert "[target for target in changed]" in resource.read()
        assert ")(changed=" in resource.read()
    elif selection == "comprehension":
        assert "[changed for changed in target]" in resource.read()
    else:
        assert "lambda *, target:" in resource.read()


@pytest.mark.parametrize(
    "expression",
    ["lambda: (target := str)", "lambda: [(target := value) for value in [str]][0]"],
)
@pytest.mark.parametrize("operation", ["local", "outer", "occurrences"])
def test_lambda_walrus_source_binding_does_not_escape_to_module(
    model_project, expression, operation
):
    source = f"target = int\ncallback = {expression}\nobserved = (target is int, callback() is str)\n"
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    local_offset = source.index("target :=")
    local = evaluate.eval_location(pymodule, local_offset)
    outer = pymodule["target"]
    assert local is not outer
    assert local.get_definition_location() == (pymodule, 2)
    before = runtime_observed(source)
    if operation == "occurrences":
        changes = rename.ChangeOccurrences(
            model_project, resource, local_offset
        ).get_changes("changed")
    else:
        offset = local_offset if operation == "local" else 0
        changes = rename.Rename(model_project, resource, offset).get_changes("changed")
    model_project.do(changes)
    assert runtime_observed(resource.read()) == before == (True, True)
    assert ("target = int" in resource.read()) == (operation != "outer")
    assert ("target :=" in resource.read()) == (operation == "outer")


@pytest.mark.parametrize("mode", ["eager", "future", "lazy"])
@pytest.mark.parametrize(
    "class_body,selected",
    [
        ("target = bytes\n", "class"),
        ("target: object = bytes\n", "class"),
        ("target: object\n", "module"),
        ("target = bytes\ndel target\n", "module"),
        ("pass\n", "module"),
    ],
)
def test_annotation_query_completion_and_rename_follow_class_namespace(
    model_project, mode, class_body, selected
):
    source = prefix(mode) + "target = int\nclass Owner:\n"
    source += indent(
        class_body + "def func(value: target) -> target:\n    return value\n", "    "
    )
    source += "subject = Owner.func\ndef drive():\n    return subject(str)\n"
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    offset = source.index("target", source.index("value: "))
    # Future-string get_type_hints uses the module namespace by its default contract.
    expected = pymodule["target"]
    if mode != "future" and selected == "class":
        expected = pymodule["Owner"].get_object()["target"]
    context = pymodule.get_source_binding_index().context_at(offset)
    assert evaluate.eval_location(pymodule, offset) is expected
    assert context.structural_scope.get_kind() == "Function"
    assert context.environment.get_kind() == "Annotation"
    assert (
        context.annotation_policy.mode
        == {"eager": "eager", "future": "future-string", "lazy": "lazy"}[mode]
    )
    assert codeassist.get_definition_location(
        model_project, source, offset, resource
    ) == (resource, expected.get_definition_location()[1])
    proposals = codeassist.code_assist(
        model_project, source, offset + 3, resource=resource, later_locals=False
    )
    assert "target" in {proposal.name for proposal in proposals}
    model_project.pycore.module_cache.forget_all_data()
    assert evaluate.eval_location(pymodule, offset) is expected
    before = observe(source)
    model_project.do(
        rename.Rename(model_project, resource, offset).get_changes("changed")
    )
    assert observe(resource.read()) == before


@pytest.mark.skipif(
    sys.version_info < (3, 12), reason="type aliases require Python 3.12"
)
@pytest.mark.parametrize("owner", ["module", "class", "class-fallback", "nested"])
def test_type_alias_outer_reference_rename_preserves_lazy_value(model_project, owner):
    if owner == "module":
        source = "target = int\ntype Alias = tuple[target, target]\nsubject = Alias\n"
    elif owner == "class":
        source = "target = int\nclass Owner:\n    target = bytes\n    type Alias = tuple[target, target]\nsubject = Owner.Alias\n"
    elif owner == "class-fallback":
        source = "target = int\nclass Owner:\n    type Alias = tuple[target, target]\nsubject = Owner.Alias\n"
    else:
        source = "target = int\ndef factory():\n    target = bytes\n    type Alias = tuple[target, target]\n    return Alias\nsubject = factory()\n"
    source += "observed = tuple(item.__name__ for item in subject.__value__.__args__)\n"
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    offset = source.index("target", source.index("tuple["))
    binding = evaluate.eval_location(pymodule, offset)
    assert binding is not None and getattr(
        binding, "is_refactoring_identity_safe", True
    )
    assert (
        codeassist.get_definition_location(model_project, source, offset, resource)[0]
        == resource
    )
    before = runtime_observed(source)
    model_project.do(
        rename.Rename(model_project, resource, offset).get_changes("changed")
    )
    assert runtime_observed(resource.read()) == before


@pytest.mark.skipif(
    sys.version_info < (3, 12), reason="generic classes require Python 3.12"
)
@pytest.mark.parametrize("query_first", [False, True])
def test_generic_alias_queries_remain_readable_and_refusal_is_project_atomic(
    model_project, query_first
):
    source = "target = int\nclass Risk[target]:\n    target = str\n    type Alias = tuple[target, target]\n"
    resource = module(model_project, source)
    client = model_project.root.create_file("client.py")
    client.write("from subject import target\nobserved = target is int\n")
    pymodule = model_project.get_pymodule(resource)
    offset = source.index("target", source.index("tuple["))
    before = {file: file.read() for file in (resource, client)}
    if query_first:
        assert codeassist.get_definition_location(
            model_project, source, offset, resource
        ) == (resource, 4)
        assert finderrors.find_errors(model_project, resource) == []
        proposals = codeassist.code_assist(
            model_project, source, offset + 3, resource=resource
        )
        assert "target" in {proposal.name for proposal in proposals}
    opaque = evaluate.eval_location(pymodule, offset)
    assert opaque.get_object() is pyobjects.get_unknown()
    assert not opaque.is_refactoring_identity_safe
    for selected in [
        offset,
        source.index("[target]") + 1,
        source.index("target = str"),
    ]:
        with pytest.raises(exceptions.RefactoringError, match="unresolved"):
            rename.Rename(model_project, resource, selected).get_changes("changed")
        assert {file: file.read() for file in before} == before
    # The same module's unrelated exported source name remains independently editable.
    model_project.do(rename.Rename(model_project, resource, 0).get_changes("changed"))
    assert "from subject import changed" in client.read()
    assert "type Alias = tuple[target, target]" in resource.read()


def test_change_occurrences_checks_only_the_selected_structural_region(model_project):
    source = (
        "target = int\nenabled = True\nclass Risk:\n    if enabled:\n        target = str\n"
        "    def method(value: target):\n        return value\n"
        "def allowed():\n    return target\nobserved = allowed() is int\n"
    )
    resource = module(model_project, source)
    before = runtime_observed(source)
    offset = source.index("target", source.index("return "))
    model_project.do(
        rename.ChangeOccurrences(model_project, resource, offset).get_changes("int")
    )
    assert runtime_observed(resource.read()) == before is True
    assert "return int" in resource.read()
    assert "value: target" in resource.read()
    resource.write(source)
    with pytest.raises(exceptions.RefactoringError, match="unresolved"):
        rename.ChangeOccurrences(model_project, resource, 0).get_changes("changed")
    assert resource.read() == source


@pytest.mark.parametrize(
    "source,entry_marker,body_marker",
    [
        (
            "lex_outer = int\ncallback = lambda lex_item=lex_outer: lex_item\n",
            "=lex_outer",
            ": lex_item",
        ),
        (
            "lex_outer = [int]\nvalues = [lex_item for lex_item in lex_outer]\n",
            "in lex_outer",
            "[lex_item",
        ),
    ],
)
def test_completion_separates_expression_entry_from_local_body(
    model_project, source, entry_marker, body_marker
):
    resource = module(model_project, source)
    for marker, body in [(entry_marker, False), (body_marker, True)]:
        start = source.index("lex_", source.index(marker))
        proposals = {
            item.name: item.scope
            for item in codeassist.code_assist(
                model_project, source, start + 4, resource=resource, later_locals=False
            )
        }
        assert proposals["lex_outer"] == "global"
        if body:
            assert proposals["lex_item"] == "local"
        else:
            assert "lex_item" not in proposals


@pytest.mark.parametrize(
    "source,expected",
    [
        ("callback = lambda item: item\n", []),
        ("values = [item for item in [int]]\n", []),
        (
            "callback = lambda item: (item, absent)\n",
            [(1, "Unresolved variable absent")],
        ),
        (
            "values = [item for item in [int] if absent]\n",
            [(1, "Unresolved variable absent")],
        ),
        ("result = later\nlater = int\n", [(1, "Defined later later")]),
    ],
)
def test_find_errors_preserves_real_diagnostics_without_expression_false_positives(
    model_project, source, expected
):
    resource = module(model_project, source)
    assert [
        (error.lineno, error.error)
        for error in finderrors.find_errors(model_project, resource)
    ] == expected


def test_introduce_parameter_rewrites_outer_capture_in_comprehension(model_project):
    source = "value = int\ndef subject():\n    return [value for item in [str]]\nobserved = subject() == [int]\n"
    resource = module(model_project, source)
    before = runtime_observed(source)
    operation = introduce_parameter.IntroduceParameter(
        model_project, resource, source.index("value", source.index("return "))
    )
    model_project.do(operation.get_changes("provided"))
    assert runtime_observed(resource.read()) == before is True
    assert "def subject(provided=value)" in resource.read()
    assert "[provided for item" in resource.read()
    assert (
        runtime_observed(resource.read() + "observed = subject(str) == [str]\n") is True
    )
    resource.write(source)
    with pytest.raises(exceptions.RefactoringError):
        introduce_parameter.IntroduceParameter(
            model_project, resource, source.index("item in")
        )
    assert resource.read() == source


@pytest.mark.parametrize("future", [False, True])
def test_introduce_parameter_refuses_annotation_environment_atomically(
    model_project, future
):
    source = "from __future__ import annotations\n" if future else ""
    source += "value = int\ndef subject(item: value):\n    return item\n"
    resource = module(model_project, source)
    offset = source.index("value", source.index("item:"))
    with pytest.raises(exceptions.RefactoringError, match="inside functions"):
        introduce_parameter.IntroduceParameter(model_project, resource, offset)
    assert resource.read() == source


@pytest.mark.parametrize("renamed_owner", ["Owner", "Other"])
def test_callable_instance_lambda_drives_field_rename(model_project, renamed_owner):
    source = "class Owner:\n    field = 1\n    __call__ = lambda self, item: self\nclass Other:\n    field = 2\nresult = Owner()(Other())\nobserved = result.field\n"
    resource = module(model_project, source)
    before = runtime_observed(source)
    offset = source.index("field = " + ("1" if renamed_owner == "Owner" else "2"))
    model_project.do(
        rename.Rename(model_project, resource, offset).get_changes("changed")
    )
    assert runtime_observed(resource.read()) == before == 1
    assert ("observed = result.changed" in resource.read()) == (
        renamed_owner == "Owner"
    )


def test_callable_instance_lambda_keyword_has_canonical_formal_identity(model_project):
    source = "class Owner:\n    __call__ = lambda self, item: item\nresult = Owner()(item=str)\nobserved = result is str\n"
    resource = module(model_project, source)
    offset = source.index("item=str")
    pymodule = model_project.get_pymodule(resource)
    binder = (
        pymodule["Owner"].get_object()["__call__"].get_object().get_parameters()["item"]
    )
    assert evaluate.eval_location(pymodule, offset) is binder
    model_project.do(
        rename.Rename(model_project, resource, offset).get_changes("changed")
    )
    assert runtime_observed(resource.read()) is True
    assert "Owner()(changed=str)" in resource.read()


@pytest.mark.skipif(
    sys.version_info < (3, 12), reason="type aliases require Python 3.12"
)
def test_class_type_alias_captures_generic_owner_without_capturing_class_values(
    model_project,
):
    source = "T = int\nclass Owner[T]:\n    unrelated = bytes\n    type Alias = tuple[T, T]\nobserved = Owner.Alias.__value__.__args__ == (Owner.__type_params__[0],) * 2\n"
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    offset = source.index("T", source.index("type Alias"))
    binder = evaluate.eval_location(pymodule, offset)
    own = evaluate.eval_location(pymodule, source.index("[T]") + 1)
    assert binder is own and binder is not pymodule["T"]
    proposals = codeassist.code_assist(
        model_project, source, offset + 1, resource=resource
    )
    assert "T" in {proposal.name for proposal in proposals}
    before = runtime_observed(source)
    model_project.do(
        rename.Rename(model_project, resource, source.index("[T]") + 1).get_changes("V")
    )
    assert runtime_observed(resource.read()) == before is True
    assert "T = int" in resource.read()


@pytest.mark.skipif(
    sys.version_info < (3, 12), reason="generic functions require Python 3.12"
)
@pytest.mark.parametrize("expression", ["T", "(lambda: T)()"])
def test_generic_annotation_query_remains_opaque_through_nested_lambda(
    model_project, expression
):
    source = f"T = int\ndef subject[T](value: {expression}):\n    return value\nobserved = subject(str) is str\n"
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    offset = source.index("T", source.index("value: "))
    binder = evaluate.eval_location(pymodule, offset)
    assert not binder.is_refactoring_identity_safe
    assert binder.get_object() is pyobjects.get_unknown()
    assert (
        codeassist.get_definition_location(model_project, source, offset, resource)[0]
        == resource
    )
    proposals = codeassist.code_assist(
        model_project, source, offset + 1, resource=resource
    )
    assert "T" in {proposal.name for proposal in proposals}
    assert runtime_observed(source) is True
    for selected in [offset, source.index("[T]") + 1]:
        with pytest.raises(exceptions.RefactoringError, match="unresolved"):
            rename.Rename(model_project, resource, selected).get_changes("V")
        assert resource.read() == source


@pytest.mark.skipif(
    sys.version_info >= (3, 14), reason="annotation walrus requires eager annotations"
)
@pytest.mark.parametrize("owner", ["module", "class"])
def test_eager_annotation_walrus_installs_its_declaration_binding(model_project, owner):
    if owner == "module":
        source = "def subject(value: (target := str)):\n    return value\nobserved = subject(int) is int and target is str\n"
    else:
        source = "target = int\nclass Owner:\n    def subject(value: (target := str)):\n        return value\nobserved = Owner.subject(int) is int and Owner.target is str and target is int\n"
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    offset = source.index("target :=")
    binding = evaluate.eval_location(pymodule, offset)
    if owner == "class":
        assert binding is pymodule["Owner"].get_object()["target"]
        assert binding is not pymodule["target"]
    else:
        assert binding is pymodule["target"]
    assert binding.get_definition_location()[0] is pymodule
    before = runtime_observed(source)
    model_project.do(
        rename.Rename(model_project, resource, offset).get_changes("changed")
    )
    assert runtime_observed(resource.read()) == before is True


@pytest.mark.parametrize("selection", ["outer", "class"])
def test_class_lambda_default_walrus_does_not_change_outer_source_binding(
    model_project, selection
):
    source = "target = int\nclass Owner:\n    callback = staticmethod(lambda value=(target := str): value)\nobserved = Owner.callback() is str and Owner.target is str and target is int\n"
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    offset = source.index("target :=") if selection == "class" else 0
    selected = evaluate.eval_location(pymodule, offset)
    class_binding = evaluate.eval_location(pymodule, source.index("target :="))
    assert class_binding is not pymodule["target"]
    assert selected is (class_binding if selection == "class" else pymodule["target"])
    before = runtime_observed(source)
    model_project.do(
        rename.Rename(model_project, resource, offset).get_changes("changed")
    )
    assert runtime_observed(resource.read()) == before is True


@pytest.mark.parametrize("mode", ["eager", "future", "lazy"])
@pytest.mark.parametrize("declaration", ["import", "function", "class", "late"])
def test_class_annotation_namespace_obeys_declaration_order_and_name_shadowing(
    model_project, mode, declaration
):
    source = prefix(mode) + "import typing\ntarget = int\nclass Owner:\n"
    if declaration == "import":
        body = "from builtins import str as target\n"
        expression = "typing.get_type_hints(Owner.subject)['value'] is str"
    elif declaration == "function":
        body = "def target():\n    return bytes\n"
        expression = "typing.get_type_hints(Owner.subject)['value']() is bytes"
    elif declaration == "class":
        body = "class target:\n    marker = 7\n"
        expression = "typing.get_type_hints(Owner.subject)['value'].marker == 7"
    else:
        body = ""
        expression = (
            "typing.get_type_hints(Owner.subject)['value'] is bytes"
            if mode == "lazy"
            else "typing.get_type_hints(Owner.subject)['value'] is int"
        )
    body += "def subject(value: target):\n    return value\n"
    if declaration == "late":
        body += "target = bytes\n"
    if mode == "future":
        expression = "typing.get_type_hints(Owner.subject)['value'] is int"
    source += indent(body, "    ")
    source += f"observed = (Owner.subject(str) is str, {expression}, target is int)\n"
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    offset = source.index("target", source.index("value: "))
    expected = pymodule["target"]
    class_resolver = mode != "future" and (declaration != "late" or mode == "lazy")
    if class_resolver:
        expected = pymodule["Owner"].get_object()["target"]
    assert evaluate.eval_location(pymodule, offset) is expected
    proposals = codeassist.code_assist(
        model_project, source, offset + 3, resource=resource, later_locals=False
    )
    assert "target" in {proposal.name for proposal in proposals}
    before = runtime_observed(source)
    # Renaming the outer source must leave independently declared class names intact.
    model_project.do(
        rename.Rename(
            model_project, resource, source.index("target = int")
        ).get_changes("changed")
    )
    assert runtime_observed(resource.read()) == before == (True, True, True)
    assert ("value: target" in resource.read()) == class_resolver


@pytest.mark.parametrize(
    "expression", ["lambda item: item", "[item for item in [str]]"]
)
def test_change_occurrences_limits_edits_to_expression_binding(
    model_project, expression
):
    if "lambda" in expression:
        source = f"item = int\ncallback = {expression}\nobserved = (callback(str) is str, item is int)\n"
        offset = source.index("item:")
    else:
        source = f"item = int\nresult = {expression}\nobserved = (result == [str], item is int)\n"
        offset = source.index("item", source.index("for "))
    resource = module(model_project, source)
    before = runtime_observed(source)
    model_project.do(
        rename.ChangeOccurrences(model_project, resource, offset).get_changes("changed")
    )
    assert runtime_observed(resource.read()) == before == (True, True)
    assert "item = int" in resource.read()
    assert "item is int" in resource.read()


@pytest.mark.parametrize(
    "expression",
    [
        "[item for item in owners][0]",
        "{0: item for item in owners}[0]",
        "{item for item in owners}.pop()",
        "tuple(item for item in owners)[0]",
        "[right for left, right in ((other, owner),)][0]",
        "(lambda ignored: owner)(other)",
    ],
)
def test_independently_parsed_expression_queries_keep_legacy_value_scope(
    model_project, expression
):
    source = (
        "class Owner:\n    field = 1\nclass Other:\n    field = 2\n"
        "owner = Owner()\nother = Other()\nitem = other\nowners = [owner]\n"
    )
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    namespace = {}
    exec(compile(source, "query_source.py", "exec", dont_inherit=True), namespace)
    result = eval(expression, namespace)
    assert type(result) is namespace["Owner"] and result.field == 1
    item_offset = source.index("item = other")
    source_binding = evaluate.eval_location(pymodule, item_offset)
    assert source_binding.get_object().get_type() is pymodule["Other"].get_object()
    for cold in (False, True):
        if cold:
            model_project.pycore.module_cache.forget_all_data()
        inferred = evaluate.eval_str(pymodule.get_scope(), expression)
        _, inferred_pair = evaluate.eval_str2(pymodule.get_scope(), expression)
        assert inferred.get_object().get_type() is pymodule["Owner"].get_object()
        assert inferred_pair.get_object().get_type() is pymodule["Owner"].get_object()
        assert evaluate.eval_location(pymodule, item_offset) is source_binding
        assert source_binding.get_object().get_type() is pymodule["Other"].get_object()
    assert resource.read() == source
    assert namespace["item"] is namespace["other"]


def test_public_binding_tree_locates_local_region_and_preserves_rename_driver(
    model_project,
):
    source = (
        "item = int\nouter_only = bytes\ncallback = (\n"
        "    lambda item: [\n        item\n        for item in item\n    ]\n)\n"
        "observed = (callback([str, bytes]) == [str, bytes], item is int)\n"
    )
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)

    def locate(module_, code, name):
        # A client traverses binding environments separately from structural scopes.
        (lambda_scope,) = module_.get_scope().get_binding_scopes()
        (comp_scope,) = lambda_scope.get_binding_scopes()
        assert lambda_scope.get_kind() == "Lambda"
        assert comp_scope.get_kind() == "Comprehension"
        assert "outer_only" not in lambda_scope.get_names()
        assert "outer_only" not in comp_scope.get_names()
        formal = lambda_scope["item"]
        local = comp_scope[name]
        assert local is not formal and formal is not module_["item"]
        lambda_start, lambda_end = lambda_scope.get_region()
        comp_start, comp_end = comp_scope.get_region()
        assert lambda_start < comp_start < comp_end <= lambda_end
        assert code[lambda_start:lambda_end].startswith("lambda item:")
        assert code[comp_start:comp_end].startswith("[")
        declaration = code.index(name, code.index("for "))
        body = code.index(name, comp_start)
        iterable = code.index("item", code.index("in item"))
        assert evaluate.eval_location(module_, declaration) is local
        assert evaluate.eval_location(module_, body) is local
        assert evaluate.eval_location(module_, iterable) is formal
        assert local.get_definition_location() == (module_, 6)
        assert codeassist.get_definition_location(
            model_project, code, body, resource
        ) == (resource, 6)
        return lambda_scope, comp_scope, local, declaration

    lambda_scope, comp_scope, binding, declaration = locate(pymodule, source, "item")
    model_project.pycore.module_cache.forget_all_data()
    cold_lambda, cold_comp, cold_binding, _ = locate(pymodule, source, "item")
    assert cold_lambda is lambda_scope and cold_comp is comp_scope
    assert cold_binding is binding
    before = runtime_observed(source)
    model_project.do(
        rename.Rename(model_project, resource, declaration).get_changes("changed")
    )
    after = resource.read()
    assert runtime_observed(after) == before == (True, True)
    assert "for changed in item" in after
    assert "lambda item:" in after and "item = int" in after
    updated = model_project.get_pymodule(resource)
    _, _, renamed_binding, _ = locate(updated, after, "changed")
    assert renamed_binding is not updated["item"]


def test_calltip_reads_simple_source_lambda_without_changing_its_binding(model_project):
    source = "callback = lambda item: item\nobserved = callback(str) is str\n"
    resource = module(model_project, source)
    offset = source.index("callback(str)") + 1
    assert (
        codeassist.get_calltip(model_project, source, offset, resource=resource)
        == "lambda(item)"
    )
    assert runtime_observed(source) is True
    assert resource.read() == source


@pytest.mark.parametrize("renamed_owner", ["Owner", "Other"])
def test_lambda_walrus_local_value_keeps_outer_value_and_field_rename_independent(
    model_project, renamed_owner
):
    source = (
        "class Owner:\n    field = 1\nclass Other:\n    field = 2\n"
        "local = Other()\nresult = (lambda: ((local := Owner()), local)[1])()\n"
        "observed = (result.field, local.field)\n"
    )
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    local = evaluate.eval_location(pymodule, source.index("local :="))
    assert local is not pymodule["local"]
    assert local.get_object().get_type() is pymodule["Owner"].get_object()
    assert pymodule["local"].get_object().get_type() is pymodule["Other"].get_object()
    assert pymodule["result"].get_object().get_type() is pymodule["Owner"].get_object()
    before = runtime_observed(source)
    offset = source.index("field = " + ("1" if renamed_owner == "Owner" else "2"))
    model_project.do(
        rename.Rename(model_project, resource, offset).get_changes("changed")
    )
    assert runtime_observed(resource.read()) == before == (1, 2)
    assert ("result.changed" in resource.read()) == (renamed_owner == "Owner")
    assert ("local.changed" in resource.read()) == (renamed_owner == "Other")


@pytest.mark.skipif(
    sys.version_info < (3, 12), reason="type aliases require Python 3.12"
)
@pytest.mark.parametrize("enabled", [False, True])
def test_conditional_class_alias_queries_are_readable_and_candidate_edits_are_atomic(
    model_project, enabled
):
    source = (
        f"target = int\nenabled = {enabled}\nclass Owner:\n"
        "    if enabled:\n        target = bytes\n"
        "    type Alias = tuple[target, target]\n"
        "unrelated = 42\nobserved = unrelated\n"
    )
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    offset = source.index("target", source.index("tuple["))
    assert (
        evaluate.eval_location(pymodule, offset).get_object() is pyobjects.get_unknown()
    )
    assert codeassist.get_definition_location(
        model_project, source, offset, resource
    ) == (resource, 6)
    assert finderrors.find_errors(model_project, resource) == []
    before = {}
    exec(compile(source, "conditional_alias.py", "exec", dont_inherit=True), before)
    expected = bytes if enabled else int
    assert before["Owner"].Alias.__value__.__args__ == (expected, expected)
    for selection in (offset, 0, source.index("target = bytes")):
        with pytest.raises(exceptions.RefactoringError, match="unresolved"):
            rename.Rename(model_project, resource, selection).get_changes("changed")
        assert resource.read() == source
    model_project.do(
        rename.Rename(model_project, resource, source.index("unrelated =")).get_changes(
            "safe"
        )
    )
    after = {}
    exec(
        compile(resource.read(), "conditional_alias.py", "exec", dont_inherit=True),
        after,
    )
    assert after["Owner"].Alias.__value__.__args__ == (expected, expected)
    assert after["observed"] == before["observed"] == 42


@pytest.mark.skipif(
    sys.version_info < (3, 12), reason="type parameters require Python 3.12"
)
def test_generic_class_bound_query_and_outer_rename_keep_runtime_bound(model_project):
    source = "target = int\nclass Owner[T: target]:\n    pass\nobserved = Owner.__type_params__[0].__bound__ is int\n"
    resource = module(model_project, source)
    pymodule = model_project.get_pymodule(resource)
    offset = source.index("target", source.index("[T:"))
    assert evaluate.eval_location(pymodule, offset) is pymodule["target"]
    assert codeassist.get_definition_location(
        model_project, source, offset, resource
    ) == (resource, 1)
    before = runtime_observed(source)
    model_project.do(rename.Rename(model_project, resource, 0).get_changes("changed"))
    assert runtime_observed(resource.read()) == before is True
    assert "class Owner[T: changed]" in resource.read()
