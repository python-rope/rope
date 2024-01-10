import sqlite3
from contextlib import closing, contextmanager
from unittest.mock import ANY, patch

import pytest

from rope.base.project import Project
from rope.contrib.autoimport import models
from rope.contrib.autoimport._database import Database



@pytest.fixture
def database(project: Project):
    with closing(Database(project, memory=True)) as ai:
        yield ai

def is_in_memory_database(connection):
    db_list = database_list(connection)
    assert db_list == [(0, "main", ANY)]
    return db_list[0][2] == ""


def database_list(connection):
    return list(connection.execute("PRAGMA database_list"))


def test_in_memory_database_share_cache(project, project2):
    ai_1 = Database(project, memory=True)
    ai_2 = Database(project, memory=True)
    ai_3 = Database(project2, memory=True)

    with ai_1.connection:
        ai_1.connection.execute("CREATE TABLE shared(data)")
        ai_1.connection.execute("INSERT INTO shared VALUES(28)")
    assert ai_2.connection.execute("SELECT data FROM shared").fetchone() == (28,)
    with pytest.raises(sqlite3.OperationalError, match="no such table: shared"):
        ai_3.connection.execute("SELECT data FROM shared").fetchone()


def test_autoimport_connection_parameter_with_in_memory(
    project: Project,
    database: Database,
):
    connection = Database.create_database_connection(memory=True)
    assert is_in_memory_database(connection)


def test_autoimport_connection_parameter_with_project(
    project: Project,
    database: Database,
):
    connection = Database.create_database_connection(project=project)
    assert not is_in_memory_database(connection)


def test_autoimport_create_database_connection_conflicting_parameter(
    project: Project,
    database: Database,
):
    with pytest.raises(Exception, match="if memory=False, project must be provided"):
        Database.create_database_connection(memory=False)


def test_autoimport_memory_parameter_is_true(
    project: Project,
    database: Database,
):
    ai = Database(project, memory=True)
    assert is_in_memory_database(ai.connection)


def test_autoimport_memory_parameter_is_false(
    project: Project,
    database: Database,
):
    ai = Database(project, memory=False)
    assert not is_in_memory_database(ai.connection)




def test_connection(project: Project, project2: Project):
    ai1 = Database(project, memory=True)
    ai2 = Database(project, memory=True)
    ai3 = Database(project2, memory=True)

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


def test_setup_db_metadata_table_is_missing(database):
    conn = database.connection
    conn.execute("DROP TABLE metadata")
    with assert_database_is_reset(conn):
        database._setup_db()


def test_setup_db_metadata_table_is_outdated(database):
    conn = database.connection
    data = ("outdated", "", "2020-01-01T00:00:00")  # (version_hash, hash_data, created_at)
    database._execute(models.Metadata.objects.insert_into(), data)

    with assert_database_is_reset(conn), \
            patch("rope.base.versioning.calculate_version_hash", return_value="up-to-date-value"):
        database._setup_db()

    with assert_database_is_preserved(conn), \
            patch("rope.base.versioning.calculate_version_hash", return_value="up-to-date-value"):
        database._setup_db()


def test_setup_db_metadata_table_is_current(database):
    conn = database.connection
    data = ("up-to-date-value", "", "2020-01-01T00:00:00")  # (version_hash, hash_data, created_at)
    database._execute(models.Metadata.objects.delete_from())
    database._execute(models.Metadata.objects.insert_into(), data)

    with assert_database_is_preserved(conn), \
            patch("rope.base.versioning.calculate_version_hash", return_value="up-to-date-value"):
        database._setup_db()
