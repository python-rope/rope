import subprocess
import sys
from textwrap import dedent

import pytest

from rope.base.exceptions import RefactoringError
from rope.base.project import Project
from rope.refactor.inline import create_inline

pytestmark = pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 syntax")


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


@pytest.mark.parametrize("remove", [True, False])
@pytest.mark.parametrize("cross_module", [False, True])
def test_refuses_moving_side_effect_into_type_alias(project, remove, cross_module):
    source = module(project, "source", '''\
        events = []
        def make():
            events.append("called")
            return int
        target = make()
    ''')
    code = '''\
        type Alias = target
        print(events)
        print(Alias.__value__ is int)
        print(events)
    '''
    if cross_module:
        entry = module(project, "entry", "from source import target, events\n" + dedent(code))
    else:
        source.write(source.read() + dedent(code))
        entry = source
    before = {r: r.read() for r in (source, entry)}
    output = execute(project, entry)
    assert output == "['called']\nTrue\n['called']\n"
    with pytest.raises(RefactoringError, match="referenced in a type alias"):
        create_inline(project, source, source.read().index("target") + 1).get_changes(remove=remove)
    assert {r: r.read() for r in before} == before
    assert execute(project, entry) == output


def test_refuses_changing_late_name_binding(project):
    source = module(project, "source", '''\
        original = int
        target = original
        type Alias = target
        original = str
        print(Alias.__value__ is int)
    ''')
    before = source.read()
    assert execute(project, source) == "True\n"
    with pytest.raises(RefactoringError):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before
    assert execute(project, source) == "True\n"


@pytest.mark.parametrize("alias", [
    "type Alias = (\n    target\n)\n",
    "type Alias[T: target] = list[T]\n",
    "type 别名 = target\n",
])
def test_refuses_multiline_bound_and_unicode_alias(project, alias):
    source = module(project, "source", "target = int\n" + alias)
    before = source.read()
    with pytest.raises(RefactoringError):
        create_inline(project, source, before.index("target") + 1).get_changes()
    assert source.read() == before


@pytest.mark.parametrize("remove", [False, True])
def test_only_current_type_alias_reference_is_refused(project, remove):
    source = module(project, "source", "target = int\ntype Alias = target\n")
    before = source.read()
    with pytest.raises(RefactoringError):
        create_inline(project, source, before.rindex("target") + 1).get_changes(only_current=True, remove=remove)
    assert source.read() == before


def test_only_current_eager_reference_can_keep_binding(project):
    source = module(project, "source", '''\
        target = int
        type Alias = target
        result = target
        print(result is Alias.__value__)
    ''')
    before = execute(project, source)
    changes = create_inline(project, source, source.read().rindex("target") + 1).get_changes(only_current=True, remove=False)
    project.do(changes)
    assert "result = int" in source.read()
    assert "target = int" in source.read()
    assert execute(project, source) == before == "True\n"


def test_only_current_cannot_remove_binding_used_by_alias(project):
    source = module(project, "source", "target = int\ntype Alias = target\nresult = target\n")
    before = source.read()
    with pytest.raises(RefactoringError):
        create_inline(project, source, before.rindex("target") + 1).get_changes(only_current=True)
    assert source.read() == before


def test_unrelated_type_alias_does_not_block_eager_inline(project):
    source = module(project, "source", '''\
        target = int
        type Alias = str
        result = target
        print(result is int)
    ''')
    before = execute(project, source)
    project.do(create_inline(project, source, source.read().index("target") + 1).get_changes())
    assert "target" not in source.read()
    assert execute(project, source) == before == "True\n"


@pytest.mark.parametrize("qualified", [False, True])
def test_cross_module_only_current_alias_reference_is_refused(project, qualified):
    source = module(project, "source", "target = int\n")
    code = (
        "import source\ntype Alias = source.target\n"
        if qualified else "from source import target\ntype Alias = target\n"
    )
    entry = module(project, "entry", code)
    before = {source: source.read(), entry: entry.read()}
    with pytest.raises(RefactoringError):
        create_inline(project, entry, code.rindex("target") + 1).get_changes(only_current=True, remove=False)
    assert {r: r.read() for r in before} == before


def test_cross_module_only_current_eager_reference_can_keep_binding(project):
    source = module(project, "source", "target = int\ntype Alias = target\n")
    entry = module(project, "entry", "from source import target, Alias\nresult = target\nprint(result is Alias.__value__)\n")
    before = execute(project, entry)
    changes = create_inline(project, entry, entry.read().rindex("target") + 1).get_changes(only_current=True, remove=False)
    project.do(changes)
    assert "result = int" in entry.read()
    assert source.read() == "target = int\ntype Alias = target\n"
    assert execute(project, entry) == before == "True\n"


def test_shadowed_name_in_type_alias_does_not_block_inline(project):
    source = module(project, "source", '''\
        target = int
        def make_alias():
            target = str
            type Alias = target
            return Alias
        result = target
        print(result is int, make_alias().__value__ is str)
    ''')
    before = execute(project, source)
    project.do(create_inline(project, source, source.read().index("target") + 1).get_changes())
    assert "result = int" in source.read()
    assert "target = str" in source.read()
    assert execute(project, source) == before == "True True\n"
