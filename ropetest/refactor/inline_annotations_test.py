import subprocess
import sys
from textwrap import dedent

import pytest

from rope.base.exceptions import RefactoringError
from rope.base.project import Project
from rope.refactor.inline import create_inline


@pytest.fixture
def project(tmp_path):
    project = Project(
        str(tmp_path), save_objectdb=False, save_history=False, automatic_soa=False
    )
    yield project
    project.close()


def module(project, name, source):
    resource = project.root.create_file(name + ".py")
    resource.write(dedent(source))
    return resource


def execute(project, resource):
    result = subprocess.run(
        [sys.executable, str(resource.real_path)],
        cwd=project.address,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.fixture(params=[True, False], ids=["future", "default"])
def deferred_prefix(request):
    if not request.param and sys.version_info < (3, 14):
        pytest.skip("default annotations are deferred on Python 3.14+")
    return "from __future__ import annotations\n" if request.param else ""


@pytest.mark.parametrize("remove", [True, False])
def test_refuses_changing_annotation_name_binding(project, deferred_prefix, remove):
    source = module(project, "source", deferred_prefix + dedent('''\
        original = int
        target = original
        def func(x: target):
            pass
        original = str
        import typing
        print(typing.get_type_hints(func)["x"] is int)
    '''))
    before = source.read()
    output = execute(project, source)
    assert output == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target") + 1).get_changes(remove=remove)
    assert source.read() == before
    assert execute(project, source) == output


def test_refuses_moving_side_effect_into_annotation(project, deferred_prefix):
    source = module(project, "source", deferred_prefix + dedent('''\
        events = []
        def make():
            events.append("called")
            return int
        target = make()
        def func() -> target:
            pass
        print(events)
        import typing
        print(typing.get_type_hints(func)["return"] is int)
        print(events)
    '''))
    before = source.read()
    output = execute(project, source)
    assert output == "['called']\nTrue\n['called']\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == output


@pytest.mark.parametrize("definition,owner,key", [
    ("async def func(x: target):\n    pass\n", "func", "x"),
    ("def func(x: target, /):\n    pass\n", "func", "x"),
    ("def func(*, x: target):\n    pass\n", "func", "x"),
    ("def func(*x: target):\n    pass\n", "func", "x"),
    ("def func(**x: target):\n    pass\n", "func", "x"),
    ("def func() -> target:\n    pass\n", "func", "return"),
    ("class Owner:\n    x: target\n", "Owner", "x"),
    ("x: target\nimport sys\n", "sys.modules[__name__]", "x"),
    ("def 函数(x: (\n    list[target]\n)):\n    pass\n", "函数", "x"),
])
def test_refuses_annotation_kinds(project, deferred_prefix, definition, owner, key):
    comparison = "list[int]" if "list[target]" in definition else "int"
    code = deferred_prefix + "original = int\ntarget = original\n" + definition
    code += "original = str\nimport typing\n"
    code += f'print(typing.get_type_hints({owner})["{key}"] == {comparison})\n'
    source = module(project, "source", code)
    assert execute(project, source) == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, code.index("target") + 1).get_changes()
    assert source.read() == code
    assert execute(project, source) == "True\n"


@pytest.mark.parametrize("qualified", [True, False])
def test_cross_module_annotation_is_refused(project, deferred_prefix, qualified):
    source = module(project, "source", "original = int\ntarget = original\n")
    imported = "source.target" if qualified else "target"
    import_line = "import source\n" if qualified else "from source import target\n"
    code = deferred_prefix + import_line
    code += f"def func(x: {imported}):\n    pass\n"
    code += 'import typing\nprint(typing.get_type_hints(func)["x"] is int)\n'
    entry = module(project, "entry", code)
    before = {source: source.read(), entry: entry.read()}
    assert execute(project, entry) == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, entry, code.index("target", code.index("def func")) + 1).get_changes(only_current=True, remove=False)
    assert {r: r.read() for r in before} == before
    assert execute(project, entry) == "True\n"


@pytest.mark.parametrize("remove", [False, True])
def test_only_current_eager_reference(project, deferred_prefix, remove):
    source = module(project, "source", deferred_prefix + dedent('''\
        target = int
        def func(x: target):
            pass
        result = target
        import typing
        print(result is typing.get_type_hints(func)["x"])
    '''))
    before = source.read()
    output = execute(project, source)
    inline = create_inline(project, source, before.rindex("target") + 1)
    if remove:
        with pytest.raises(RefactoringError, match="deferred annotation"):
            inline.get_changes(only_current=True)
        assert source.read() == before
    else:
        project.do(inline.get_changes(only_current=True, remove=False))
        assert "result = int" in source.read()
        assert "target = int" in source.read()
    assert execute(project, source) == output == "True\n"


def test_eager_annotations_allow_inline(project):
    if sys.version_info >= (3, 14):
        pytest.skip("default annotations are deferred on Python 3.14+")
    source = module(project, "source", '''\
        original = int
        target = original
        def func(x: target):
            pass
        original = str
        import typing
        print(typing.get_type_hints(func)["x"] is int)
    ''')
    before = execute(project, source)
    project.do(create_inline(project, source, source.read().index("target") + 1).get_changes())
    assert "target" not in source.read()
    assert execute(project, source) == before == "True\n"


def test_function_default_is_eager(project, deferred_prefix):
    source = module(project, "source", deferred_prefix + dedent('''\
        original = int
        target = original
        def func(x: str = target):
            return x
        original = str
        print(func() is int)
    '''))
    before = execute(project, source)
    project.do(create_inline(project, source, source.read().index("target") + 1).get_changes())
    assert "x: str = original" in source.read()
    assert execute(project, source) == before == "True\n"


def test_shadowed_function_annotation_checks_runtime_namespace(project, deferred_prefix):
    source = module(project, "source", deferred_prefix + dedent('''\
        target = int
        def func(target: str):
            def inner(x: target):
                pass
            return inner
        result = target
        import typing
        print(result is int, typing.get_type_hints(func(str))["x"] is int)
    '''))
    before = execute(project, source)
    inline = create_inline(project, source, source.read().index("target") + 1)
    if deferred_prefix:
        code = source.read()
        with pytest.raises(RefactoringError, match="deferred annotation"):
            inline.get_changes()
        assert source.read() == code
        assert execute(project, source) == before == "True True\n"
    else:
        project.do(inline.get_changes())
        assert "result = int" in source.read()
        assert "x: target" in source.read()
        assert execute(project, source) == before == "True False\n"


def test_local_variable_annotation_is_not_evaluated(project, deferred_prefix):
    source = module(project, "source", deferred_prefix + dedent('''\
        target = int
        def func():
            x: target = 1
            return x
        print(func())
    '''))
    before = execute(project, source)
    project.do(create_inline(project, source, source.read().index("target") + 1).get_changes())
    assert "target = int" not in source.read()
    assert execute(project, source) == before == "1\n"


@pytest.mark.parametrize("annotation", ["holder.x: target = 1", "holder[0]: target = 1", "(result): target = 1"])
def test_non_simple_annotation_is_not_deferred(project, deferred_prefix, annotation):
    if annotation.startswith("(result)"):
        setup, access = "", "result"
    elif "[0]" in annotation:
        setup, access = "holder = [0]\n", "holder[0]"
    else:
        setup, access = "class Holder: pass\nholder = Holder()\n", "holder.x"
    source = module(project, "source", deferred_prefix + "target = int\n" + setup + annotation + f"\nprint({access})\n")
    before = execute(project, source)
    project.do(create_inline(project, source, source.read().index("target") + 1).get_changes())
    assert "target = int" not in source.read()
    assert execute(project, source) == before == "1\n"


def test_nested_eager_function_annotation_allows_inline(project):
    if sys.version_info >= (3, 14):
        pytest.skip("default annotations are deferred on Python 3.14+")
    source = module(project, "source", '''\
        def outer():
            original = int
            target = original
            def inner(x: target):
                pass
            original = str
            return inner
        import typing
        print(typing.get_type_hints(outer())["x"] is int)
    ''')
    before = execute(project, source)
    project.do(create_inline(project, source, source.read().index("target") + 1).get_changes())
    assert "target" not in source.read()
    assert execute(project, source) == before == "True\n"


def test_class_annotation_within_function_is_still_deferred(project, deferred_prefix):
    source = module(project, "source", deferred_prefix + dedent('''\
        original = int
        target = original
        def factory():
            class Owner:
                x: target
            return Owner
        original = str
        import typing
        print(typing.get_type_hints(factory())["x"] is int)
    '''))
    before = source.read()
    assert execute(project, source) == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before


def test_class_shadowed_annotation_checks_runtime_namespace(project, deferred_prefix):
    source = module(project, "source", deferred_prefix + dedent('''\
        target = int
        class Owner:
            target = str
            x: target
        result = target
        import typing
        print(result is int, typing.get_type_hints(Owner)["x"] is str)
    '''))
    before = execute(project, source)
    inline = create_inline(project, source, source.read().index("target") + 1)
    if deferred_prefix:
        code = source.read()
        with pytest.raises(RefactoringError, match="deferred annotation"):
            inline.get_changes()
        assert source.read() == code
        assert execute(project, source) == before == "True False\n"
    else:
        project.do(inline.get_changes())
        assert "result = int" in source.read()
        assert "target = str" in source.read()
        assert execute(project, source) == before == "True True\n"


def test_resources_sequence_is_preserved(project, deferred_prefix):
    source = module(project, "source", deferred_prefix + "target = int\nresult = target\nprint(result is int)\n")
    before = execute(project, source)
    resources = (source,)
    project.do(create_inline(project, source, source.read().index("target") + 1).get_changes(resources=resources))
    assert "target" not in source.read()
    assert execute(project, source) == before == "True\n"


def test_function_body_shadowing_still_allows_inline(project, deferred_prefix):
    source = module(project, "source", deferred_prefix + dedent('''\
        target = int
        def func(target: str):
            return target
        result = target
        print(result is int, func(str) is str)
    '''))
    before = execute(project, source)
    project.do(create_inline(project, source, source.read().index("target") + 1).get_changes())
    assert "result = int" in source.read()
    assert "return target" in source.read()
    assert execute(project, source) == before == "True True\n"


@pytest.mark.parametrize("remove", [False, True])
@pytest.mark.parametrize("only_current", [False, True])
def test_only_current_checks_annotation_in_third_module(project, deferred_prefix, remove, only_current):
    source = module(project, "source", "target = int\n")
    annotated = module(project, "annotated", deferred_prefix + "import source\ndef func(x: source.target):\n    pass\n")
    entry = module(project, "entry", '''\
        import source
        import annotated
        result = source.target
        import typing
        print(result is typing.get_type_hints(annotated.func)["x"])
    ''')
    before = {r: r.read() for r in (source, annotated, entry)}
    output = execute(project, entry)
    inline = create_inline(project, entry, entry.read().rindex("target") + 1)
    if remove:
        with pytest.raises(RefactoringError, match="deferred annotation"):
            inline.get_changes(only_current=only_current, resources=[entry, source])
        assert {r: r.read() for r in before} == before
    else:
        project.do(inline.get_changes(only_current=only_current, remove=False, resources=[entry, source]))
        assert "result = int" in entry.read()
        assert source.read() == before[source]
        assert annotated.read() == before[annotated]
    assert execute(project, entry) == output == "True\n"


def test_future_import_alias_preserves_runtime_global_binding(project):
    source = module(project, "source", "target = int\n")
    entry = module(project, "entry", '''\
        from __future__ import annotations
        from source import target as Alias
        class Owner:
            Alias = str
            x: Alias
        import typing
        print(typing.get_type_hints(Owner)["x"] is int)
    ''')
    before = {source: source.read(), entry: entry.read()}
    assert execute(project, entry) == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, source.read().index("target") + 1).get_changes()
    assert {r: r.read() for r in before} == before
    assert execute(project, entry) == "True\n"


def test_future_qualified_annotation_preserves_runtime_global_binding(project):
    source = module(project, "source", "target = int\n")
    entry = module(project, "entry", '''\
        from __future__ import annotations
        import source
        class Holder:
            target = str
        class Owner:
            source = Holder
            x: source.target
        result = source.target
        import typing
        print(result is typing.get_type_hints(Owner)["x"])
    ''')
    before = {source: source.read(), entry: entry.read()}
    assert execute(project, entry) == "True\n"
    with pytest.raises(RefactoringError, match="deferred annotation"):
        create_inline(project, source, source.read().index("target") + 1).get_changes()
    assert {r: r.read() for r in before} == before
    assert execute(project, entry) == "True\n"
