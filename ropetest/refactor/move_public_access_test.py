import os
import subprocess
import sys
from textwrap import dedent, indent

import pytest

from rope.base import evaluate, exceptions
from rope.base.project import Project
from rope.refactor import move


@pytest.fixture
def native_project(tmp_path):
    project = Project(tmp_path, ropefolder=None, source_folders=[""])
    yield project
    project.close()


def _write(project, path, source):
    target = project.root.real_path + "/" + path
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as output:
        output.write(source)
    return project.get_file(path)


def _run(project, code):
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=project.root.real_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_move_to_same_holder_normalizes_self_import_and_evaluated_base(native_project):
    project = native_project
    project.prefs.imports.preferred_import_style = "from-global"
    target = _write(project, "target.py", dedent("""\
        class Destination:
            class First:
                def kind(self):
                    return "first"
    """))
    source = _write(project, "source.py", dedent("""\
        from __future__ import annotations
        from target import Destination as Existing
        class Owner:
            class Second(Existing.First):
                def kind(self):
                    return "second:" + super().kind()
                def first(self) -> 'Existing.First':
                    return Existing.First()
    """))
    mover = move.create_move(project, source, source.read().index("Second"))
    project.do(mover.get_changes(target, destination_offset=target.read().index("Destination")))
    assert "from target import" not in target.read()
    assert _run(project, dedent("""\
        from typing import get_type_hints
        from target import Destination
        assert Destination.Second.__mro__[1] is Destination.First
        assert get_type_hints(Destination.Second.first)["return"] is Destination.First
        assert isinstance(Destination.Second().first(), Destination.First)
        print(Destination.Second().kind())
    """)) == "second:first\n"


def test_mutual_nested_contracts_and_sibling_inheritance_move_as_a_cohort(native_project):
    project = native_project
    project.prefs.imports.preferred_import_style = "from-global"
    target = _write(project, "target.py", dedent("""\
        class Destination:
            pass
    """))
    source = _write(project, "source.py", dedent("""\
        from __future__ import annotations
        class Owner:
            class First:
                def other(self) -> 'Owner.Second':
                    return Owner.Second()
            class Second(First):
                def first(self) -> 'Owner.First':
                    return Owner.First()
    """))
    for name in ("First", "Second"):
        mover = move.create_move(project, source, source.read().index("class " + name) + len("class "))
        project.do(mover.get_changes(target, destination_offset=target.read().index("Destination")))
    assert "from target import" not in target.read()
    assert "from source import" not in target.read()
    assert _run(project, dedent("""\
        from typing import get_type_hints
        from target import Destination
        assert Destination.Second.__mro__[1] is Destination.First
        assert get_type_hints(Destination.First.other)["return"] is Destination.Second
        assert get_type_hints(Destination.Second.first)["return"] is Destination.First
        assert isinstance(Destination.First().other(), Destination.Second)
        assert isinstance(Destination.Second().first(), Destination.First)
        print("cohort preserved")
    """)) == "cohort preserved\n"


def _contract(owner, bases, nesting, kind, *, target=False):
    source = "class " + owner + ("(" + ", ".join(bases) + ")" if bases else "") + ":\n"
    level = 1
    for number in range(nesting):
        source += "    " * level + "class Level" + str(number)
        source += "(Target):\n" if target and number == nesting - 1 else ":\n"
        level += 1
    source += indent(dedent('''\
        class Contract:
            def kind(self):
                return {!r}
    ''').format(kind), "    " * level)
    return source


@pytest.mark.parametrize("namespace_depth", [0, 1, 4])
@pytest.mark.parametrize("nesting", [0, 1, 3])
def test_barrels_aliases_inherited_contracts_and_c3_override(native_project, namespace_depth, nesting):
    project = native_project
    parts = ["ns" + str(number) for number in range(namespace_depth)] + ["contracts"]
    directory, package = "/".join(parts), ".".join(parts)
    target = _write(project, directory + "/target.py", dedent("""\
        class Target:
            pass
    """))
    owner = _write(project, directory + "/owner.py",
        "from .target import Target\n"
        + _contract("Owner", ("Target",) if not nesting else (), nesting, "base", target=True)
        + dedent("""\
            class Left(Owner):
                pass
            class InheritedRight(Owner):
                pass
        """)
        + _contract("Right", ("Owner",), nesting, "override")
        + dedent("""\
            class Public(Left, InheritedRight):
                pass
            class Override(Left, Right):
                pass
        """)
        + _contract("Stranger", (), nesting, "stranger"))
    _write(project, directory + "/exports.py", dedent("""\
        from .owner import Public as PublicFacade
        Mid = PublicFacade
        __all__ = ["PublicFacade", "Mid"]
    """))
    _write(project, directory + "/__init__.py", dedent("""\
        from .exports import PublicFacade as p, Mid as Alias
        from .owner import Override, Stranger
        __all__ = ["p", "Alias", "Override", "Stranger"]
    """))
    path = ".".join(["Level" + str(number) for number in range(nesting)] + ["Contract"])
    consumer = _write(project, directory + "/consumer.py", dedent("""\
        from . import *
        from .owner import Owner as Direct
        from . import exports as namespace
        direct = Direct.{path}()
        public = p.{path}()
        chain = namespace.Mid.{path}()
        override = Override.{path}()
        stranger = Stranger.{path}()
        def annotated(value: 'Alias.{path}') -> 'Alias.{path}':
            return value
    """).format(path=path))
    script = dedent("""\
        from {package}.consumer import direct, public, chain, override, stranger, annotated
        from {package}.owner import Public, Override
        assert [item.__name__ for item in Public.__mro__[:4]] == ["Public", "Left", "InheritedRight", "Owner"]
        assert [item.__name__ for item in Override.__mro__[:4]] == ["Override", "Left", "Right", "Owner"]
        assert type(direct) is type(public) is type(chain)
        assert annotated(public) is public
        print(direct.kind(), public.kind(), chain.kind(), override.kind(), stranger.kind())
    """).format(package=package)
    assert _run(project, script) == "base base base override stranger\n"
    public = project.get_module(package + ".owner")["Public"].get_object()

    def selected(site):
        environment = site.tools.pymodule.get_source_binding_index().context_at(site.offset).environment
        names = site.get_primary_text().split(".")
        for count in range(1, len(names)):
            binding = evaluate.eval_str(environment, ".".join(names[:count]))
            if binding is not None and binding.get_object() is public:
                return False
        return True

    mover = move.create_move(project, owner, owner.read().index("Contract"))
    project.do(mover.get_changes(target, destination_offset=target.read().index("Target"), match_filter=selected))
    assert "public = p." + path + "()" in consumer.read()
    assert "chain = namespace.Mid." + path + "()" in consumer.read()
    assert "'Alias." + path + "'" in consumer.read()
    assert _run(project, script) == "base base base override stranger\n"


def test_unresolved_alias_cycle_rejects_before_any_effect(native_project):
    project = native_project
    source = _write(project, "source.py", dedent("""\
        class Owner:
            class Contract:
                pass
    """))
    target = _write(project, "target.py", dedent("""\
        class Target:
            pass
    """))
    _write(project, "first.py", "from second import Alias\n")
    _write(project, "second.py", "from first import Alias\n")
    _write(project, "consumer.py", dedent("""\
        from first import Alias
        value: 'Alias.Contract'
    """))
    before = source.read(), target.read()
    mover = move.create_move(project, source, source.read().index("Contract"))
    with pytest.raises(exceptions.RefactoringError, match="Unproven"):
        mover.get_changes(target, destination_offset=target.read().index("Target"))
    assert (source.read(), target.read()) == before
