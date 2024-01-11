import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from textwrap import dedent
from unittest.mock import ANY, patch

import pytest

from rope.base.project import Project
from rope.base.resources import File, Folder
from rope.contrib.autoimport import models
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


def test_in_memory_database_share_cache(project, project2):
    ai_1 = AutoImport(project, memory=True)
    ai_2 = AutoImport(project, memory=True)

    ai_3 = AutoImport(project2, memory=True)

    with ai_1.connection:
        ai_1.connection.execute("CREATE TABLE shared(data)")
        ai_1.connection.execute("INSERT INTO shared VALUES(28)")
    assert ai_2.connection.execute("SELECT data FROM shared").fetchone() == (28,)
    with pytest.raises(sqlite3.OperationalError, match="no such table: shared"):
        ai_3.connection.execute("SELECT data FROM shared").fetchone()


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


def test_multithreading(
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
    autoimport = AutoImport(project, memory=False)
    autoimport.generate_cache([mod1_init])

    tp = ThreadPoolExecutor(1)
    results = tp.submit(autoimport.search, "foo", True).result()
    assert [("from pkg1 import foo", "foo")] == results


def test_connection(project: Project, project2: Project):
    ai1 = AutoImport(project)
    ai2 = AutoImport(project)
    ai3 = AutoImport(project2)

    assert ai1.connection is not ai2.connection
    assert ai1.connection is not ai3.connection


@contextmanager
def assert_database_is_reset(conn):
    conn.execute("ALTER TABLE names ADD COLUMN deprecated_column")
    names_ddl, = [ddl for ddl in conn.iterdump() if "CREATE TABLE names" in ddl]
    assert "deprecated_column" in names_ddl

    yield

    names_ddl, = [ddl for ddl in conn.iterdump() if "CREATE TABLE names" in ddl]
    assert "deprecated_column" not in names_ddl, "Database did not get reset"


@contextmanager
def assert_database_is_preserved(conn):
    conn.execute("ALTER TABLE names ADD COLUMN deprecated_column")
    names_ddl, = [ddl for ddl in conn.iterdump() if "CREATE TABLE names" in ddl]
    assert "deprecated_column" in names_ddl

    yield

    names_ddl, = [ddl for ddl in conn.iterdump() if "CREATE TABLE names" in ddl]
    assert "deprecated_column" in names_ddl, "Database was reset unexpectedly"


def test_setup_db_metadata_table_is_missing(autoimport):
    conn = autoimport.connection
    conn.execute("DROP TABLE metadata")
    with assert_database_is_reset(conn):
        autoimport._setup_db()


def test_setup_db_metadata_table_is_outdated(autoimport):
    conn = autoimport.connection
    data = ("outdated", "", "2020-01-01T00:00:00")  # (version_hash, hash_data, created_at)
    autoimport._execute(models.Metadata.objects.insert_into(), data)

    with assert_database_is_reset(conn), \
            patch("rope.base.versioning.calculate_version_hash", return_value="up-to-date-value"):
        autoimport._setup_db()

    with assert_database_is_preserved(conn), \
            patch("rope.base.versioning.calculate_version_hash", return_value="up-to-date-value"):
        autoimport._setup_db()


def test_setup_db_metadata_table_is_current(autoimport):
    conn = autoimport.connection
    data = ("up-to-date-value", "", "2020-01-01T00:00:00")  # (version_hash, hash_data, created_at)
    autoimport._execute(models.Metadata.objects.delete_from())
    autoimport._execute(models.Metadata.objects.insert_into(), data)

    with assert_database_is_preserved(conn), \
            patch("rope.base.versioning.calculate_version_hash", return_value="up-to-date-value"):
        autoimport._setup_db()


class TestQueryUsesIndexes:
    def explain(self, autoimport, query):
        explanation = list(autoimport._execute(query.explain(), ("abc",)))[0][-1]
        # the explanation text varies, on some sqlite version
        explanation = explanation.replace("TABLE ", "")
        return explanation

    def test_search_by_name_uses_index(self, autoimport):
        query = models.Name.search_by_name.select_star()
        assert (
            self.explain(autoimport, query)
            == "SEARCH names USING INDEX names_name (name=?)"
        )

    def test_search_by_name_like_uses_index(self, autoimport):
        query = models.Name.search_by_name_like.select_star()
        assert (
            self.explain(autoimport, query)
            == "SEARCH names USING INDEX names_name_nocase (name>? AND name<?)"
        )

    def test_search_module_like_uses_index(self, autoimport):
        query = models.Name.search_module_like.select_star()
        assert (
            self.explain(autoimport, query)
            == "SEARCH names USING INDEX names_module_nocase (module>? AND module<?)"
        )

    def test_search_submodule_like_uses_index(self, autoimport):
        query = models.Name.search_submodule_like.select_star()
        assert (
            self.explain(autoimport, query)
            == "SCAN names" # FIXME: avoid full table scan
        )
