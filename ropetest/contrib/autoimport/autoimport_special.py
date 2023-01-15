# Special cases, easier to express in pytest
import os
from pathlib import Path

import pytest

from rope.base.project import Project
from rope.base.resources import Resource
from rope.contrib.autoimport.sqlite import AutoImport


@pytest.fixture
def project(tmp_path: Path):
    return Project(tmp_path)


@pytest.fixture
def autoimport(project: Project):
    a = AutoImport(project)
    yield a
    a.close()


@pytest.fixture
def mod1_folder(project: Project, tmp_path: Path):
    s = "mod1"
    p = tmp_path / s
    p.mkdir()
    assert p.exists()
    yield Resource(project, s)


@pytest.fixture
def mod2_file(project: Project, tmp_path: Path):
    s = "mod2.py"
    p = tmp_path / s
    p.touch()
    assert p.exists()
    yield Resource(project, s)


def test_init_py(
    autoimport: AutoImport, project: Project, mod1_folder: Resource, mod2_file: Resource
):
    s = "__init__.py"
    i = mod1_folder.pathlib / s
    with i.open(mode="x") as f:
        f.write("def foo():\n")
        f.write("\tpass\n")
    with mod2_file.pathlib.open(mode="w") as f:
        f.write("foo")
    autoimport.generate_cache([Resource(project, os.path.join("mod1", s))])
    results = autoimport.search("foo", True)
    print(results)
    assert [("from mod1 import foo", "foo")] == results
