import subprocess
import sys
from textwrap import dedent

import pytest

from rope.base.exceptions import RefactoringError
from rope.base.project import Project
from rope.refactor.inline import create_inline

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 12), reason="type parameter syntax requires Python 3.12+"
)


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


@pytest.mark.parametrize(
    "declaration,owner",
    [
        ("def func[T: target]():", "func"),
        ("async def func[T: target]():", "func"),
        ("class Owner[T: target]:", "Owner"),
        ("def func[T: (target, float)]():", "func"),
        ("class Owner[T: (target, float)]:", "Owner"),
    ],
)
@pytest.mark.parametrize("remove", [True, False])
def test_refuses_changing_bound_or_constraint_binding(
    project, declaration, owner, remove
):
    attribute = "__constraints__" if "float" in declaration else "__bound__"
    expected = "(int, float)" if "float" in declaration else "int"
    source = module(
        project,
        "source",
        dedent(f"""\
        original = int
        target = original
        {declaration}
            pass
        original = str
        print({owner}.__type_params__[0].{attribute} == {expected})
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target") + 1).get_changes(
            remove=remove
        )
    assert source.read() == before
    assert execute(project, source) == output


@pytest.mark.skipif(
    sys.version_info < (3, 13), reason="type defaults require Python 3.13+"
)
@pytest.mark.parametrize(
    "declaration,owner,initial,expected,rebound",
    [
        ("def func[T = target]():", "func", "int", "int", "str"),
        ("class Owner[T = target]:", "Owner", "int", "int", "str"),
        ("def func[**P = target]():", "func", "[int]", "[int]", "[str]"),
        (
            "def func[*Ts = *target]():",
            "func",
            "tuple[int, float]",
            "next(iter(tuple[int, float]))",
            "tuple[str, float]",
        ),
    ],
)
def test_refuses_changing_default_binding(
    project, declaration, owner, initial, expected, rebound
):
    source = module(
        project,
        "source",
        dedent(f"""\
        original = {initial}
        target = original
        {declaration}
            pass
        original = {rebound}
        print({owner}.__type_params__[0].__default__ == {expected})
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == output


def test_refuses_deferring_initializer_side_effect(project):
    source = module(
        project,
        "source",
        dedent("""\
        events = []
        def make():
            events.append("called")
            return int
        target = make()
        def func[T: target]():
            pass
        print(events)
        print(func.__type_params__[0].__bound__ is int)
        print(events)
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "['called']\nTrue\n['called']\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == output


@pytest.mark.parametrize("selection", ["definition", "reference"])
def test_refuses_removing_binding_outside_selected_write_scope(project, selection):
    source = module(project, "source", "target = int\n")
    annotation = module(
        project,
        "annotation",
        dedent("""\
        import source
        class Owner[T: source.target]:
            pass
    """),
    )
    entry = module(
        project,
        "entry",
        dedent("""\
        import source
        import annotation
        result = source.target
        print(result is int, annotation.Owner.__type_params__[0].__bound__ is int)
    """),
    )
    files = (source, annotation, entry)
    before = [resource.read() for resource in files]
    output = execute(project, entry)
    assert output == "True True\n"
    resource = source if selection == "definition" else entry
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(
            project, resource, resource.read().index("target") + 1
        ).get_changes(only_current=selection == "reference", resources=(entry,))
    assert [resource.read() for resource in files] == before
    assert execute(project, entry) == output


def test_allows_partial_eager_inline_with_type_parameter_binding_retained(project):
    source = module(
        project,
        "source",
        dedent("""\
        original = int
        target = original
        def func[T: target]():
            pass
        result = target
        original = str
        print(result is int, func.__type_params__[0].__bound__ is int)
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "True True\n"
    project.do(
        create_inline(
            project, source, before.index("result = target") + len("result = t")
        ).get_changes(only_current=True, remove=False)
    )
    assert "target = original" in source.read()
    assert "result = original" in source.read()
    assert execute(project, source) == output


def test_allows_eager_reference_in_generic_function_body(project):
    source = module(
        project,
        "source",
        dedent("""\
        target = 42
        def func[T: int]():
            return target
        print(func(), func.__type_params__[0].__bound__ is int)
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "42 True\n"
    project.do(create_inline(project, source, before.index("target") + 1).get_changes())
    assert "return 42" in source.read()
    assert execute(project, source) == output


def test_refuses_removing_captured_local_binding(project):
    source = module(
        project,
        "source",
        dedent("""\
        def outer():
            target = int
            def func[T: target]():
                pass
            return func
        print(outer().__type_params__[0].__bound__ is int)
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == output


def test_allows_unrelated_shadowed_type_parameter_reference(project):
    source = module(
        project,
        "source",
        dedent("""\
        target = 42
        def outer():
            target = int
            def func[T: target]():
                pass
            return func
        result = target
        print(result, outer().__type_params__[0].__bound__ is int)
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "42 True\n"
    project.do(create_inline(project, source, before.index("target") + 1).get_changes())
    assert "result = 42" in source.read()
    assert execute(project, source) == output


@pytest.mark.parametrize(
    "definition,owner",
    [
        (
            dedent("""\
        def func[T: target](target):
            pass
    """),
            "func",
        ),
        (
            dedent("""\
        async def func[T: target](target):
            pass
    """),
            "func",
        ),
        (
            dedent("""\
        def func[T: target]():
            target = str
    """),
            "func",
        ),
        (
            dedent("""\
        class Owner[T: target]:
            target = str
    """),
            "Owner",
        ),
    ],
)
def test_refuses_dependency_hidden_by_function_or_class_body(
    project, definition, owner
):
    source = module(
        project,
        "source",
        dedent("original = int\ntarget = original\n") + definition + dedent(f"""\
        original = str
        print({owner}.__type_params__[0].__bound__ is int)
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == output


@pytest.mark.parametrize(
    "definition,owner",
    [
        (
            dedent("""\
        def func[T: target](target):
            pass
    """),
            "Outer.func",
        ),
        (
            dedent("""\
        class Owner[T: target]:
            target = str
    """),
            "Outer.Owner",
        ),
    ],
)
def test_refuses_removing_enclosing_class_namespace_binding(project, definition, owner):
    code = dedent("class Outer:\n    target = int\n") + "".join(
        "    " + line for line in definition.splitlines(True)
    )
    code += f"print({owner}.__type_params__[0].__bound__ is int)\n"
    source = module(project, "source", code)
    before = source.read()
    output = execute(project, source)
    assert output == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == output


@pytest.mark.parametrize(
    "declaration,expected",
    [
        ("def func[target: target]():", "func.__type_params__[0]"),
        ("def func[target, T: target]():", "func.__type_params__[0]"),
    ],
)
def test_allows_removing_binding_shadowed_by_type_parameter(
    project, declaration, expected
):
    index = 1 if ", T" in declaration else 0
    source = module(
        project,
        "source",
        dedent(f"""\
        target = int
        {declaration}
            pass
        result = target
        print(result is int, func.__type_params__[{index}].__bound__ is {expected})
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "True True\n"
    project.do(
        create_inline(
            project, source, before.index("result = target") + len("result = t")
        ).get_changes(only_current=True)
    )
    assert "result = int" in source.read()
    assert execute(project, source) == output


@pytest.mark.skipif(
    sys.version_info < (3, 13), reason="type defaults require Python 3.13+"
)
@pytest.mark.parametrize(
    "definition,owner",
    [
        (
            dedent("""\
        def func[T = target](target):
            pass
    """),
            "func",
        ),
        (
            dedent("""\
        class Owner[T = target]:
            target = str
    """),
            "Owner",
        ),
    ],
)
def test_refuses_default_dependency_hidden_by_declared_scope(
    project, definition, owner
):
    source = module(
        project,
        "source",
        dedent("original = int\ntarget = original\n") + definition + dedent(f"""\
        original = str
        print({owner}.__type_params__[0].__default__ is int)
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == output


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="nested annotation scopes in classes require Python 3.14+",
)
@pytest.mark.parametrize(
    "expression",
    [
        "(lambda: target)()",
        "[target for unused in [0]][0]",
        "next(target for unused in [0])",
        "{unused: target for unused in [0]}[0]",
        "{target for unused in [0]}.pop()",
    ],
)
def test_refuses_inner_expression_resolving_module_namespace(project, expression):
    source = module(
        project,
        "source",
        dedent(f"""\
        original = int
        target = original
        class Outer:
            target = bytes
            def func[T: {expression}](target):
                pass
        original = str
        print(Outer.func.__type_params__[0].__bound__ is int)
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == output


@pytest.mark.parametrize(
    "expression",
    [
        "(lambda target: target)(int)",
        "[target for target in [int]][0]",
        "next(target for target in [int])",
        "{target: target for target in [int]}[int]",
        "{target for target in [int]}.pop()",
    ],
)
def test_allows_removing_binding_shadowed_by_inner_expression(project, expression):
    source = module(
        project,
        "source",
        dedent(f"""\
        target = 42
        def func[T: {expression}]():
            pass
        result = target
        print(result, func.__type_params__[0].__bound__ is int)
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "42 True\n"
    project.do(
        create_inline(
            project, source, before.index("result = target") + len("result = t")
        ).get_changes(only_current=True)
    )
    assert "result = 42" in source.read()
    assert execute(project, source) == output


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="nested annotation scopes in classes require Python 3.14+",
)
@pytest.mark.parametrize(
    "expression",
    [
        "(lambda value=target: value)()",
        "[value for value in [target]][0]",
    ],
)
def test_refuses_inner_expression_outer_class_namespace_dependency(project, expression):
    source = module(
        project,
        "source",
        dedent(f"""\
        class Outer:
            target = int
            def func[T: {expression}](target):
                pass
        print(Outer.func.__type_params__[0].__bound__ is int)
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == output


@pytest.mark.parametrize(
    "definition,comparison",
    [
        (
            dedent("""\
        def outer[target]():
            def func[T: target]():
                pass
            return func.__type_params__[0].__bound__ is outer.__type_params__[0]
    """),
            "outer()",
        ),
        (
            dedent("""\
        class Outer[target]:
            def func[T: target]():
                pass
    """),
            "Outer.func.__type_params__[0].__bound__ is Outer.__type_params__[0]",
        ),
        (
            dedent("""\
        class Outer[target]:
            target = bytes
            def method(self):
                def func[T: target]():
                    pass
                return func.__type_params__[0].__bound__ is Outer.__type_params__[0]
    """),
            "Outer().method()",
        ),
    ],
)
def test_allows_removing_binding_shadowed_by_enclosing_type_parameter(
    project, definition, comparison
):
    source = module(
        project,
        "source",
        "target = 42\n" + definition + dedent(f"""\
        result = target
        print(result, {comparison})
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "42 True\n"
    project.do(
        create_inline(
            project, source, before.index("result = target") + len("result = t")
        ).get_changes(only_current=True)
    )
    assert "result = 42" in source.read()
    assert execute(project, source) == output


def test_refuses_local_binding_inside_enclosing_generic_function(project):
    source = module(
        project,
        "source",
        dedent("""\
        def outer[target]():
            def inner():
                target = int
                def func[T: target]():
                    pass
                return func
            return inner()
        print(outer().__type_params__[0].__bound__ is int)
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target = int") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == output


@pytest.mark.parametrize(
    "initializer,assignment",
    [
        ("Box()", "target.attr"),
        ("{}", "target[0]"),
    ],
)
def test_refuses_object_dependency_in_comprehension_assignment_target(
    project, initializer, assignment
):
    source = module(
        project,
        "source",
        dedent(f"""\
        class Box:
            pass
        target = {initializer}
        def func[T: [int for {assignment} in [int]][0]](target):
            pass
        print(func.__type_params__[0].__bound__ is int)
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == output


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="nested annotation scopes in classes require Python 3.14+",
)
@pytest.mark.parametrize(
    "expression",
    [
        "(lambda: target)()",
        "[target for unused in [0]][0]",
    ],
)
def test_allows_inner_expression_capturing_enclosing_class_type_parameter(
    project, expression
):
    source = module(
        project,
        "source",
        dedent(f"""\
        target = 42
        class Owner[target]:
            target = bytes
            def func[T: {expression}]():
                pass
        result = target
        print(result, Owner.func.__type_params__[0].__bound__ is Owner.__type_params__[0])
    """),
    )
    before = source.read()
    output = execute(project, source)
    assert output == "42 True\n"
    project.do(
        create_inline(
            project, source, before.index("result = target") + len("result = t")
        ).get_changes(only_current=True)
    )
    assert "result = 42" in source.read()
    assert execute(project, source) == output
