from typing import Iterable

import pytest

from rope.contrib.autoimport.sqlite import AutoImport




@pytest.fixture
def autoimport(project) -> Iterable[AutoImport]:
    autoimport = AutoImport(project, memory=True)
    autoimport.generate_modules_cache()
    yield autoimport
    autoimport.close()


@pytest.mark.parametrize("project", ((""),), indirect=True)
def test_blank(project, autoimport):
    assert project.prefs.dependencies is None
    assert autoimport.search("pytoolconfig")


@pytest.mark.parametrize("project", (("[project]\n dependencies=[]"),), indirect=True)
def test_empty(project, autoimport):
    assert len(project.prefs.dependencies) == 0
    assert [] == autoimport.search("pytoolconfig")


FILE = """
[project]
dependencies = [
    "pytoolconfig",
    "bogus"
]
"""


@pytest.mark.parametrize("project", ((FILE),), indirect=True)
def test_not_empty(project, autoimport):
    assert len(project.prefs.dependencies) == 2
    assert autoimport.search("pytoolconfig")
