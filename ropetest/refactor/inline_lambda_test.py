import subprocess
import sys
from textwrap import dedent

import pytest

from rope.base.exceptions import RefactoringError
from rope.base.project import Project
from rope.refactor.inline import InlineParameter, InlineVariable, create_inline


@pytest.fixture
def project(tmp_path):
    project = Project(
        str(tmp_path), save_objectdb=False, save_history=False, automatic_soa=False
    )
    yield project
    project.close()


def module(project, name, code):
    resource = project.root.create_file(name + ".py")
    resource.write(dedent(code))
    return resource


def execute(project, resource):
    result = subprocess.run(
        [sys.executable, resource.real_path],
        cwd=project.address,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


SHADOW = dedent("""\
    target = 42
    value = (lambda target: target)(int)
    print(value is int)
""")
NAMED_EXPR = dedent("""\
    target = 42
    value = (lambda: ((target := int), target)[1])()
    print(value is int)
    print(target)
""")


@pytest.mark.parametrize(
    "code,expected",
    [
        (SHADOW, "True\n"),
        (
            dedent("""\
                def outer():
                    target = 42
                    return (lambda target: target)(int)
                print(outer() is int)
            """),
            "True\n",
        ),
        (
            dedent("""\
                target = 42
                def func(value=(lambda target: target)(int)):
                    return value
                print(func() is int)
            """),
            "True\n",
        ),
        (
            dedent("""\
                target = 42
                f = lambda target=target: target
                print(f(), f(int) is int)
            """),
            "42 True\n",
        ),
        (
            dedent("""\
                target = 42
                value = (lambda target: (lambda value=target: value)())(int)
                print(value is int)
            """),
            "True\n",
        ),
        (NAMED_EXPR, "True\n42\n"),
        (
            dedent("""\
                def make_target():
                    print("initialized")
                    return 42
                target = make_target()
                value = (lambda target: target)(int)
                print(value is int)
            """),
            "initialized\nTrue\n",
        ),
    ],
)
def test_refuses_replacing_lambda_local_bindings(project, code, expected):
    source = module(project, "source", code)
    before = source.read()
    assert execute(project, source) == expected
    with pytest.raises(RefactoringError, match="lambda-local"):
        create_inline(project, source, before.index("target =") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == expected


@pytest.mark.parametrize(
    "expression",
    [
        "(lambda target, /: target)(int)",
        "(lambda *, target: target)(target=int)",
        "(lambda *target: target[0])(int)",
        "(lambda **target: target['item'])(item=int)",
    ],
)
def test_covers_parameter_kinds(project, expression):
    source = module(
        project,
        "source",
        dedent(f"""\
            target = 42
            value = {expression}
            print(value is int)
        """),
    )
    before = source.read()
    assert execute(project, source) == "True\n"
    with pytest.raises(RefactoringError, match="lambda-local"):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == "True\n"


@pytest.mark.parametrize("constructor", [create_inline, InlineVariable])
@pytest.mark.parametrize("remove", [True, False])
@pytest.mark.parametrize(
    "code,fragment,expected",
    [
        (SHADOW, "target: target", "True\n"),
        (SHADOW, "target)(int)", "True\n"),
        (NAMED_EXPR, "target :=", "True\n42\n"),
        (NAMED_EXPR, "target)[1]", "True\n42\n"),
    ],
)
def test_refuses_selecting_lambda_local_binding(
    project, constructor, remove, code, fragment, expected
):
    source = module(project, "source", code)
    before = source.read()
    assert execute(project, source) == expected
    with pytest.raises(RefactoringError, match="lambda-local"):
        constructor(project, source, before.index(fragment) + 1).get_changes(
            only_current=True, remove=remove
        )
    assert source.read() == before
    assert execute(project, source) == expected


@pytest.mark.parametrize("constructor", [create_inline, InlineParameter])
@pytest.mark.parametrize("fragment", ["target: target", "target)(int)"])
def test_does_not_mistake_lambda_binding_for_outer_parameter(
    project, constructor, fragment
):
    source = module(
        project,
        "source",
        dedent("""\
            def outer(target=42):
                return (lambda target: target)(int)
            print(outer() is int)
        """),
    )
    before = source.read()
    assert execute(project, source) == "True\n"
    with pytest.raises(RefactoringError, match="lambda-local"):
        constructor(project, source, before.index(fragment) + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == "True\n"


def test_refuses_other_module_false_occurrences_atomically(project):
    source = module(project, "source", "target = 42\n")
    caller = module(
        project,
        "caller",
        dedent("""\
            from source import target
            value = (lambda target: target)(int)
            print(value is int)
        """),
    )
    originals = source.read(), caller.read()
    assert execute(project, caller) == "True\n"
    with pytest.raises(RefactoringError, match="lambda-local"):
        create_inline(project, source, 1).get_changes()
    assert (source.read(), caller.read()) == originals
    assert execute(project, caller) == "True\n"


@pytest.mark.parametrize(
    "code,fragment,expected",
    [
        (
            SHADOW.replace("value =", "value = ('中文',").replace("(int)", "(int))[1]"),
            "target)(int)",
            "True\n",
        ),
        (SHADOW.replace("target", "目标"), "目标)(int)", "True\n"),
        (
            dedent("""\
                target = 42
                class Box:
                    value = int
                value = (lambda target: target.value)(Box)
                print(value is int)
            """),
            "target.value",
            "True\n",
        ),
    ],
)
def test_local_selection_uses_name_ranges(project, code, fragment, expected):
    source = module(project, "source", code)
    before = source.read()
    assert execute(project, source) == expected
    with pytest.raises(RefactoringError, match="lambda-local"):
        create_inline(project, source, before.index(fragment) + 1).get_changes(
            only_current=True, remove=False
        )
    assert source.read() == before
    assert execute(project, source) == expected


@pytest.mark.parametrize("remove", [True, False])
def test_partial_eager_reference_does_not_touch_lambda_binding(project, remove):
    source = module(project, "source", SHADOW + "print(target)\n")
    before = source.read()
    assert execute(project, source) == "True\n42\n"
    project.do(
        create_inline(project, source, before.rindex("target") + 1).get_changes(
            only_current=True, remove=remove
        )
    )
    assert "lambda target: target" in source.read()
    assert execute(project, source) == "True\n42\n"


@pytest.mark.parametrize(
    "code,fragment,expected,partial",
    [
        (
            dedent("""\
                target = 42
                value = (lambda: target)()
                print(value)
            """),
            "target =",
            "42\n",
            False,
        ),
        (
            dedent("""\
                target = 42
                value = (lambda other: (lambda value=target: value)())(0)
                print(value)
            """),
            "target =",
            "42\n",
            False,
        ),
        (
            dedent("""\
                target = 42
                f = lambda target=target: target
                print(f(), f(int) is int)
            """),
            "target: target",
            "42 True\n",
            True,
        ),
        (
            dedent("""\
                target = int
                def consume(**kwargs):
                    return kwargs['target']
                value = (lambda other: consume(target=target))(0)
                print(value is int)
            """),
            "target =",
            "True\n",
            False,
        ),
        (
            dedent("""\
                class Box:
                    target = int
                    pass
                value = (lambda target: Box.target)(str)
                print(value is int)
            """),
            "target =",
            "True\n",
            False,
        ),
        (
            dedent("""\
                target = 42
                value = (lambda: ((lambda: (target := int))(), target)[1])()
                print(value)
            """),
            "target)[1]",
            "42\n",
            True,
        ),
        (
            dedent("""\
                target = 42
                value = (lambda: (target := int))()
                print(value is int)
            """),
            "target =",
            "True\n",
            False,
        ),
    ],
)
def test_preserves_real_external_references_and_independent_names(
    project, code, fragment, expected, partial
):
    source = module(project, "source", code)
    before = source.read()
    assert execute(project, source) == expected
    project.do(
        create_inline(project, source, before.index(fragment) + 1).get_changes(
            only_current=partial
        )
    )
    assert source.read() != before
    assert execute(project, source) == expected


@pytest.mark.parametrize(
    "expression",
    [
        "(lambda target: target.value)(Inner())",
        "(lambda target: target)(Inner()).value",
    ],
)
def test_refuses_attribute_lookup_through_lambda_local_receiver(project, expression):
    source = module(
        project,
        "source",
        dedent(f"""\
            class Outer:
                value = 42
                pass
            class Inner:
                value = int
            target = Outer()
            result = {expression}
            print(result is int)
        """),
    )
    before = source.read()
    assert execute(project, source) == "True\n"
    with pytest.raises(RefactoringError, match="lambda-local"):
        create_inline(project, source, before.index("value = 42") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == "True\n"


def test_refuses_selecting_attribute_of_lambda_local_receiver(project):
    source = module(
        project,
        "source",
        dedent("""\
        class Outer:
            value = 42
            pass
        class Inner:
            value = int
        target = Outer()
        result = (lambda target: target.value)(Inner())
        print(result is int)
    """),
    )
    before = source.read()
    assert execute(project, source) == "True\n"
    offset = before.index("target.value") + len("target.") + 1
    with pytest.raises(RefactoringError, match="lambda-local"):
        create_inline(project, source, offset).get_changes(only_current=True)
    assert source.read() == before
    assert execute(project, source) == "True\n"


@pytest.mark.parametrize(
    "expression",
    ["(lambda target: Box)(str).value", "make_box(lambda target=target: target).value"],
)
def test_attribute_receiver_ignores_unrelated_lambda_bindings(project, expression):
    source = module(
        project,
        "source",
        dedent(f"""\
        target = 42
        class Box:
            value = int
            pass
        def make_box(callback):
            return Box()
        result = {expression}
        print(result is int)
        print(target)
    """),
    )
    before = source.read()
    assert execute(project, source) == "True\n42\n"
    project.do(
        create_inline(project, source, before.index("value = int") + 1).get_changes()
    )
    assert source.read() != before
    assert execute(project, source) == "True\n42\n"
