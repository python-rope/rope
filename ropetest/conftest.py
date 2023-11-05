import pathlib

import pytest

from rope.base import resources
from ropetest import testutils


@pytest.fixture
def project():
    project = testutils.sample_project()
    yield project
    testutils.remove_project(project)


@pytest.fixture
def project2():
    project = testutils.sample_project("another_project")
    yield project
    testutils.remove_project(project)


@pytest.fixture
def project_path(project):
    yield pathlib.Path(project.address)


@pytest.fixture
def project2():
    project = testutils.sample_project("sample_project2")
    yield project
    testutils.remove_project(project)


"""
Standard project structure for pytest fixtures
/mod1.py            -- mod1
/pkg1/__init__.py   -- pkg1
/pkg1/mod2.py       -- mod2
"""

@pytest.fixture
def mod1(project) -> resources.File:
    return testutils.create_module(project, "mod1")


@pytest.fixture
def pkg1(project) -> resources.Folder:
    return testutils.create_package(project, "pkg1")


@pytest.fixture
def mod2(project, pkg1) -> resources.Folder:
    return testutils.create_module(project, "mod2", pkg1)
