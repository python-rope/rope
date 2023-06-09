from contextlib import closing
from textwrap import dedent
from unittest.mock import ANY

import pytest

from rope.base.project import Project
from rope.base.resources import File, Folder
from rope.contrib.autoimport.sqlite import AutoImport


@pytest.fixture
def autoimport(project: Project):
    with closing(AutoImport(project)) as ai:
        yield ai


def is_in_memory_database(connection):
    db_list = database_list(connection)
    assert db_list == [(0, "main", ANY)]
    return db_list[0][2] == ""


def database_list(connection):
    return list(connection.execute("PRAGMA database_list"))


def test_autoimport_connection_parameter_with_in_memory(
    project: Project,
    autoimport: AutoImport,
):
    connection = AutoImport.create_database_connection(memory=True)
    assert is_in_memory_database(connection)


def test_autoimport_connection_parameter_with_project(
    project: Project,
    autoimport: AutoImport,
):
    connection = AutoImport.create_database_connection(project=project)
    assert not is_in_memory_database(connection)


def test_autoimport_create_database_connection_conflicting_parameter(
    project: Project,
    autoimport: AutoImport,
):
    with pytest.raises(Exception, match="if memory=False, project must be provided"):
        AutoImport.create_database_connection(memory=False)


def test_autoimport_memory_parameter_is_true(
    project: Project,
    autoimport: AutoImport,
):
    ai = AutoImport(project, memory=True)
    assert is_in_memory_database(ai.connection)


def test_autoimport_memory_parameter_is_false(
    project: Project,
    autoimport: AutoImport,
):
    ai = AutoImport(project, memory=False)
    assert not is_in_memory_database(ai.connection)


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
