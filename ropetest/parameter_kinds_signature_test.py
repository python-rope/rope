"""Runtime and atomicity checks for parameter-kind signature consumers."""

import contextlib
import io
from textwrap import dedent

import pytest

from rope.base import exceptions
from rope.base.project import Project
from rope.refactor import change_signature, introduce_parameter, move, usefunction
from rope.refactor.inline import InlineVariable, create_inline
from rope.refactor.localtofield import LocalToField
from rope.refactor.method_object import MethodObject


@pytest.fixture
def project(tmp_path):
    result = Project(
        str(tmp_path), save_objectdb=False, save_history=False, automatic_soa=False
    )
    yield result
    result.close()


def module(project, source, name="case"):
    result = project.root.create_file(name + ".py")
    result.write(source)
    return result


def execute(source):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(compile(source, "<parameter-kind-fixture>", "exec"), {})
    return output.getvalue()


def refused(resources, operation):
    sources = [resource.read() for resource in resources]
    outputs = [execute(source) for source in sources]
    try:
        with pytest.raises(exceptions.RefactoringError):
            operation()
    finally:
        assert [resource.read() for resource in resources] == sources
        assert [execute(resource.read()) for resource in resources] == outputs


@pytest.mark.parametrize(
    "parameters", ["value, /", "*, value", "value=1, *, required=2"]
)
@pytest.mark.parametrize(
    "api", ["get_changes", "normalize", "remove", "add", "inline_default", "reorder"]
)
def test_signature_writers_refuse_new_kinds_atomically(project, parameters, api):
    source = dedent(f"""\
        def f({parameters}):
            return value
    """)
    resource = module(project, source)
    other = module(project, "print('unrelated')\n", "other")
    signature = change_signature.ChangeSignature(project, resource, source.index("f("))
    operations = {
        "get_changes": lambda: signature.get_changes(
            [change_signature.ArgumentNormalizer()]
        ),
        "normalize": signature.normalize,
        "remove": lambda: signature.remove(0),
        "add": lambda: signature.add(0, "added", "0", "0"),
        "inline_default": lambda: signature.inline_default(0),
        "reorder": lambda: signature.reorder([0]),
    }
    refused([resource, other], operations[api])


@pytest.mark.parametrize("kind", ["posonly", "kwonly"])
def test_signature_hierarchy_checks_actual_override(project, kind):
    parameters = "self, value, /" if kind == "posonly" else "self, *, value"
    source = (
        dedent("""\
        class Base:
            def f(self, value):
                return value
    """)
        + dedent(f"""\
        class Child(Base):
            def f({parameters}):
                return value + 1
    """)
    )
    source += (
        "print(Child().f(value=3))\n" if kind == "kwonly" else "print(Child().f(3))\n"
    )
    resource = module(project, source)
    other = module(project, "print('unrelated')\n", "other")
    signature = change_signature.ChangeSignature(project, resource, source.index("f("))
    refused(
        [resource, other],
        lambda: signature.get_changes(
            [change_signature.ArgumentNormalizer()], in_hierarchy=True
        ),
    )


@pytest.mark.parametrize("selection", ["class", "initializer", "call"])
def test_constructor_signature_refuses_posonly(project, selection):
    source = dedent("""\
        class C:
            def __init__(self, /, value):
                self.value = value
        item = C(3)
        print(item.value)
    """)
    resource = module(project, source)
    offsets = {
        "class": source.index("C:"),
        "initializer": source.index("__init__"),
        "call": source.index("C(3)"),
    }
    signature = change_signature.ChangeSignature(project, resource, offsets[selection])
    refused(
        [resource],
        lambda: signature.get_changes([change_signature.ArgumentNormalizer()]),
    )


@pytest.mark.parametrize(
    "header", ["def f(value, /)", "def f(*, value)", "async def f(value, /)"]
)
def test_introduce_parameter_refuses_header_rewrite(project, header):
    source = dedent(f"""\
        base = 3
        {header}:
            return value + base
    """)
    resource = module(project, source)
    operation = introduce_parameter.IntroduceParameter(
        project, resource, source.rindex("base") + 1
    )
    refused([resource], lambda: operation.get_changes("added"))


@pytest.mark.parametrize(
    "parameters", ["value=1, *, required", "value=1, /", "*values", "**values"]
)
def test_parameter_inline_refuses_unsupported_whole_signature(project, parameters):
    source = dedent(f"""\
        def f({parameters}):
            pass
    """)
    resource = module(project, source)
    name = "values" if "values" in parameters else "value"
    refused(
        [resource],
        lambda: create_inline(project, resource, source.index(name) + 1).get_changes(),
    )


def test_direct_variable_inliner_refuses_parameter(project):
    source = dedent("""\
        def f(value):
            return value
        print(f(3))
    """)
    resource = module(project, source)
    refused(
        [resource], lambda: InlineVariable(project, resource, source.index("value") + 1)
    )


@pytest.mark.parametrize("parameters", ["self, value, /", "self, *, value"])
@pytest.mark.parametrize("direct", [False, True])
def test_move_method_refuses_unsupported_header(project, parameters, direct):
    source = dedent(f"""\
        class Target:
            pass
        class Owner:
            def __init__(self):
                self.dest = Target()
            def act({parameters}):
                return value + 1
    """)
    resource = module(project, source)
    operation = move.MoveMethod(project, resource, source.index("act("))
    refused(
        [resource],
        lambda: (
            operation.get_new_method("act") if direct else operation.get_changes("dest")
        ),
    )


def test_use_function_refuses_kwonly_generated_calls(project):
    source = dedent("""\
        def f(*, value):
            return value + 1
        answer = 3 + 1
        print(answer)
    """)
    resource = module(project, source)
    operation = usefunction.UseFunction(project, resource, source.index("f("))
    refused([resource], operation.get_changes)


def test_ordinary_signature_normalization_keeps_runtime(project):
    source = dedent("""\
        def f(value):
            return value + 1
        print(f(value=3))
    """)
    resource = module(project, source)
    signature = change_signature.ChangeSignature(project, resource, source.index("f("))
    project.do(signature.get_changes([change_signature.ArgumentNormalizer()]))
    assert execute(source) == execute(resource.read()) == "4\n"


def test_ordinary_parameter_default_inline_keeps_runtime(project):
    source = dedent("""\
        def f(value=1):
            return value + 1
        print(f())
    """)
    resource = module(project, source)
    project.do(
        create_inline(project, resource, source.index("value") + 1).get_changes()
    )
    assert "f(1)" in resource.read()
    assert execute(source) == execute(resource.read()) == "2\n"


def test_posonly_method_inline_keeps_existing_success(project):
    source = dedent("""\
        def f(value, /, other):
            return value + other + 1
        answer = f(1, 2)
        print(answer)
    """)
    resource = module(project, source)
    project.do(create_inline(project, resource, source.index("f(")).get_changes())
    assert execute(source) == execute(resource.read()) == "4\n"


def test_posonly_method_inline_refuses_invalid_keyword_call(project):
    source = dedent("""\
        def f(value, /):
            return value
        try:
            print(f(value=3))
        except TypeError:
            print("keyword rejected")
    """)
    resource = module(project, source)
    refused(
        [resource],
        lambda: create_inline(project, resource, source.index("f(")).get_changes(),
    )


def test_kwonly_method_inline_keeps_existing_refusal(project):
    source = dedent("""\
        def f(value, *, other):
            return value + other
        print(f(1, other=2))
    """)
    resource = module(project, source)
    refused(
        [resource],
        lambda: create_inline(project, resource, source.index("f(")).get_changes(),
    )


@pytest.mark.parametrize(
    "parameters, call", [("value, /", "3"), ("*, value", "value=3")]
)
def test_method_object_preserves_original_parameter_contract(project, parameters, call):
    source = dedent(f"""\
        def f({parameters}):
            return value + 1
        print(f({call}))
    """)
    resource = module(project, source)
    operation = MethodObject(project, resource, source.index("f("))
    project.do(operation.get_changes(classname="Callable"))
    assert f"def f({parameters}):" in resource.read()
    assert execute(source) == execute(resource.read()) == "4\n"


def test_local_to_field_preserves_posonly_receiver(project):
    source = dedent("""\
        class C:
            def f(self, /, *, value):
                local = value + 1
                return local
        print(C().f(value=3))
    """)
    resource = module(project, source)
    project.do(LocalToField(project, resource, source.index("local") + 1).get_changes())
    assert "self.local" in resource.read()
    assert execute(source) == execute(resource.read()) == "4\n"


@pytest.mark.parametrize(
    "staticmethod, parameters",
    [(False, "*, value"), (True, "value"), (True, "*, value")],
)
def test_local_to_field_refuses_missing_receiver(project, staticmethod, parameters):
    decorator = "@staticmethod" if staticmethod else ""
    source = dedent(f"""\
        class Value:
            number = 3
        obj = Value()
        class C:
            {decorator}
            def f({parameters}):
                local = value.number + 1
                return local
        print(C.f(value=obj))
        print(hasattr(obj, 'local'))
    """)
    resource = module(project, source)
    assert execute(source) == "4\nFalse\n"
    refused(
        [resource],
        lambda: LocalToField(
            project, resource, source.index("local") + 1
        ).get_changes(),
    )


@pytest.mark.parametrize("parameters", ["cls, *, value", "cls, /, *, value"])
def test_local_to_field_preserves_classmethod_receiver(project, parameters):
    source = dedent(f"""\
        class Value:
            number = 3
        obj = Value()
        class C:
            @classmethod
            def f({parameters}):
                local = value.number + 1
                return local
        print(C.f(value=obj))
        print(hasattr(obj, 'local'))
        print(hasattr(C, 'local'))
    """)
    resource = module(project, source)
    project.do(LocalToField(project, resource, source.index("local") + 1).get_changes())
    assert "cls.local" in resource.read()
    assert execute(source) == "4\nFalse\nFalse\n"
    assert execute(resource.read()) == "4\nFalse\nTrue\n"
