# Special cases, easier to express in pytest
from contextlib import closing
from textwrap import dedent

import pytest

from rope.base.project import Project
from rope.base.resources import File, Folder
from rope.contrib.autoimport.sqlite import AutoImport


@pytest.fixture
def autoimport(project: Project):
    with closing(AutoImport(project)) as ai:
        yield ai


def test_init_py(
    autoimport: AutoImport,
    project: Project,
    pkg1: Folder,
    mod1: File,
):
    mod1_init = pkg1.get_child("__init__.py")
    mod1_init.write(dedent("""\
        def foo():
            pass
    """))
    mod1.write(dedent("""\
        foo
    """))
    autoimport.generate_cache([mod1_init])
    results = autoimport.search("foo", True)
    assert [("from pkg1 import foo", "foo")] == results
