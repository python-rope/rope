from textwrap import dedent

import pytest

from rope.base import evaluate, exceptions, pynames
from rope.refactor.inline import create_inline
from rope.refactor.rename import Rename
from ropetest import testutils


@pytest.fixture
def project():
    project = testutils.sample_project()
    yield project
    testutils.remove_project(project)


@pytest.fixture
def module(project):
    return testutils.create_module(project, "sample")


@pytest.fixture(
    params=[
        (
            dedent("""\
            callback = eval("lambda target: target")
        """),
            "callback",
        ),
        (
            dedent("""\
            callbacks = {"active": eval("lambda target: target")}
        """),
            'callbacks["active"]',
        ),
        (
            dedent("""\
            class Holder:
                pass
            holder = Holder()
            holder.callback = eval("lambda target: target")
        """),
            "holder.callback",
        ),
        (
            dedent("""\
            def get_callback():
                return eval("lambda target: target")
        """),
            "get_callback()",
        ),
    ]
)
def unknown_call(request):
    setup, callee = request.param
    return dedent("""\
        target = int
    """) + setup + f"result = {callee}(target=target)\n"


def run(source):
    namespace = {}
    exec(source, namespace)
    return namespace["result"]


def test_unknown_keyword_has_no_variable_identity(project, module, unknown_call):
    module.write(unknown_call)
    pymodule = project.get_pymodule(module)
    label_offset = unknown_call.index("target=target")
    assert evaluate.eval_location2(pymodule, label_offset) == (None, None)
    assert (
        evaluate.eval_location(pymodule, label_offset + len("target="))
        is pymodule["target"]
    )


def test_rename_variable_preserves_unknown_keyword(project, module, unknown_call):
    assert run(unknown_call) is int
    module.write(unknown_call)
    changes = Rename(project, module, unknown_call.index("target")).get_changes(
        "renamed"
    )
    project.do(changes)
    refactored = module.read()
    assert "(target=renamed)" in refactored
    assert run(refactored) is int


def test_inline_variable_preserves_unknown_keyword(project, module, unknown_call):
    assert run(unknown_call) is int
    module.write(unknown_call)
    changes = create_inline(project, module, unknown_call.index("target")).get_changes()
    project.do(changes)
    refactored = module.read()
    assert "(target=int)" in refactored
    assert run(refactored) is int


def test_unknown_keyword_cannot_select_same_named_variable(project, module):
    source = dedent("""\
        target = int
        callback = eval("lambda target: target")
        result = callback(target=target)
    """)
    module.write(source)
    with pytest.raises(exceptions.RefactoringError):
        Rename(project, module, source.index("target=target"))
    assert module.read() == source


@pytest.mark.parametrize(
    "callee, setup",
    [
        (
            "callback",
            dedent("""\
            def callback(target=int):
                return target
        """),
        ),
        (
            "callback",
            dedent("""\
            class Callback:
                def __call__(self, target=int):
                    return target
            callback = Callback()
        """),
        ),
    ],
)
@pytest.mark.parametrize("selection", ["formal", "keyword"])
def test_known_parameter_rename_preserves_identity(
    project, module, callee, setup, selection
):
    source = dedent("""\
        target = str
    """) + setup + f"result = {callee}(target=target)\n"
    module.write(source)
    formal_offset = source.index("target=int")
    keyword_offset = source.index("target=target")
    pymodule = project.get_pymodule(module)
    formal = evaluate.eval_location(pymodule, formal_offset)
    assert isinstance(formal, pynames.ParameterName)
    assert evaluate.eval_location(pymodule, keyword_offset) is formal
    offset = formal_offset if selection == "formal" else keyword_offset
    assert run(source) is str
    project.do(Rename(project, module, offset).get_changes("renamed"))
    refactored = module.read()
    assert "renamed=int" in refactored
    assert "(renamed=target)" in refactored
    assert run(refactored) is str


def test_rename_default_value_and_keyword_argument_value(project, module):
    source = dedent("""\
        target = int
        def callback(value=target):
            return value
        result = callback(value=target)
    """)
    expected = dedent("""\
        renamed = int
        def callback(value=renamed):
            return value
        result = callback(value=renamed)
    """)
    assert run(source) is int
    module.write(source)
    project.do(Rename(project, module, source.index("target")).get_changes("renamed"))
    assert module.read() == expected
    assert run(module.read()) is int


def test_builtin_keyword_retains_parameter_identity(project, module):
    source = dedent("""\
        target = int
        result = dict(target=target)
    """)
    module.write(source)
    pymodule = project.get_pymodule(module)
    label_offset = source.index("target=target")
    assert isinstance(
        evaluate.eval_location(pymodule, label_offset), pynames.ParameterName
    )
    project.do(Rename(project, module, source.index("target")).get_changes("renamed"))
    assert "dict(target=renamed)" in module.read()
    assert run(module.read()) == {"target": int}
