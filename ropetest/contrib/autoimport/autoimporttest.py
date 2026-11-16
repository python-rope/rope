import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from textwrap import dedent
from threading import Barrier, Event
from unittest.mock import ANY, patch

import pytest

from rope.base import exceptions
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
    with closing(AutoImport.create_database_connection(memory=True)) as connection:
        assert is_in_memory_database(connection)


def test_autoimport_connection_parameter_with_project(
    project: Project,
    autoimport: AutoImport,
):
    with closing(AutoImport.create_database_connection(project=project)) as connection:
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
    project: Project,
    pkg1: Folder,
    mod1: File,
):
    mod1_init = pkg1.get_child("__init__.py")
    mod1_init.write(
        dedent("""\
        def foo():
            pass
    """)
    )
    mod1.write(
        dedent("""\
        foo
    """)
    )
    with closing(AutoImport(project, memory=False)) as autoimport:
        autoimport.generate_cache([mod1_init])

        with ThreadPoolExecutor(1) as tp:
            results = tp.submit(autoimport.search, "foo", True).result()
            assert [("from pkg1 import foo", "foo")] == results


def test_multithread_connections_closed_on_close(project: Project):
    with AutoImport(project, memory=True) as ai:
        main_conn = ai.connection
        worker_conns = []
        ready = Barrier(4, timeout=5)

        def worker():
            conn = ai.connection
            worker_conns.append(conn)
            ready.wait()
            return list(ai.search("foo"))

        with ThreadPoolExecutor(3) as tp:
            futures = [tp.submit(worker) for _ in range(3)]
            ready.wait()
            for f in futures:
                f.result(timeout=5)

        all_conns = {main_conn} | set(worker_conns)
        assert len(all_conns) == 4
        assert all_conns.issubset(ai._connections.values())

    assert ai._closed
    assert len(ai._connections) == 0
    for conn in all_conns:
        with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):
            conn.execute("SELECT 1")

    with pytest.raises(exceptions.RopeError, match="AutoImport instance has been closed"):
        _ = ai.connection


@pytest.mark.parametrize("memory", [True, False])
def test_finished_thread_connections_are_reaped(project: Project, memory: bool):
    ai = AutoImport(project, memory=memory)
    worker_connections = []

    for _ in range(3):
        with ThreadPoolExecutor(1) as executor:
            worker_connections.append(executor.submit(lambda: ai.connection).result())
        assert len(ai._connections) <= 2

    for conn in worker_connections[:-1]:
        with pytest.raises(
            sqlite3.ProgrammingError, match="Cannot operate on a closed database"
        ):
            conn.execute("SELECT 1")

    ai.close()
    for conn in worker_connections:
        with pytest.raises(
            sqlite3.ProgrammingError, match="Cannot operate on a closed database"
        ):
            conn.execute("SELECT 1")


@pytest.mark.parametrize("memory", [True, False])
def test_close_rejects_live_worker_connections(project: Project, memory: bool):
    with AutoImport(project, memory=memory) as ai:
        started = Event()
        finish = Event()

        def worker():
            conn = ai.connection
            started.set()
            assert finish.wait(timeout=5)
            return conn.execute("SELECT 1").fetchone()

        with ThreadPoolExecutor(1) as executor:
            future = executor.submit(worker)
            try:
                assert started.wait(timeout=5)
                connections = dict(ai._connections)
                observer = ai._observer
                with pytest.raises(exceptions.RopeError, match="wait for them to finish"):
                    ai.close()
                assert not ai._closed
                assert ai._connections == connections
                assert ai._observer is observer
                assert ai.connection.execute("SELECT 1").fetchone() == (1,)
            finally:
                finish.set()
            assert future.result(timeout=5) == (1,)

    assert ai._closed


@pytest.mark.parametrize("memory", [True, False])
def test_close_allows_live_worker_after_releasing_connection(
    project: Project, memory: bool
):
    released = Event()
    finish = Event()
    with AutoImport(project, memory=memory) as ai:
        def worker():
            conn = ai.connection
            ai.close_thread_connection()
            with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
                conn.execute("SELECT 1")
            released.set()
            assert finish.wait(timeout=5)
            with pytest.raises(exceptions.RopeError, match="instance has been closed"):
                _ = ai.connection

        with ThreadPoolExecutor(1) as executor:
            future = executor.submit(worker)
            try:
                assert released.wait(timeout=5)
                assert not future.done()
                ai.close()
                assert ai._closed
                assert not ai._connections
            finally:
                finish.set()
            future.result(timeout=5)


def test_close_thread_connection(project: Project):
    with AutoImport(project, memory=True) as ai:
        worker_conn = None

        def worker():
            nonlocal worker_conn
            worker_conn = ai.connection
            assert worker_conn in ai._connections.values()
            ai.close_thread_connection()
            assert worker_conn not in ai._connections.values()
            with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):
                worker_conn.execute("SELECT 1")
            new_conn = ai.connection
            assert new_conn is not worker_conn
            assert new_conn in ai._connections.values()

        with ThreadPoolExecutor(1) as tp:
            tp.submit(worker).result()


def test_close_idempotent(project: Project):
    ai = AutoImport(project, memory=True)
    conn = ai.connection
    ai.close()
    assert ai._closed
    ai.close()
    with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):
        conn.execute("SELECT 1")


@pytest.mark.parametrize(
    "fail_commit, fail_close", [(True, False), (False, True), (True, True)]
)
def test_close_reports_errors_after_closing_all_connections(
    project: Project, fail_commit: bool, fail_close: bool
):
    commit_error = sqlite3.OperationalError("commit failed")
    close_error = sqlite3.OperationalError("close failed")

    class FailingConnection(sqlite3.Connection):
        def commit(self):
            if fail_commit:
                raise commit_error
            super().commit()

        def close(self):
            super().close()
            if fail_close:
                raise close_error

    with AutoImport(project, memory=True) as ai:
        with closing(ai.connection):
            conn = sqlite3.connect(":memory:", factory=FailingConnection)
            ai.connection = conn
        with ThreadPoolExecutor(1) as executor:
            worker_conn = executor.submit(lambda: ai.connection).result(timeout=5)

        with pytest.raises(sqlite3.OperationalError) as raised:
            ai.close()
        assert raised.value is (commit_error if fail_commit else close_error)
        assert ai._closed
        assert not ai._connections
        assert ai._observer is None
        for connection in (conn, worker_conn):
            with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
                connection.execute("SELECT 1")
        ai.close()


def test_registration_closes_new_connection_when_reaping_fails(project: Project):
    error = sqlite3.OperationalError("commit failed")

    class FailingConnection(sqlite3.Connection):
        def commit(self):
            raise error

    with AutoImport(project, memory=True) as ai:
        failing_conn = sqlite3.connect(
            ":memory:", factory=FailingConnection, check_same_thread=False
        )
        ready = Barrier(3, timeout=5)

        def worker(connection=None):
            if connection is not None:
                ai.connection = connection
            conn = ai.connection
            ready.wait()
            return conn

        with ThreadPoolExecutor(2) as executor:
            failing_future = executor.submit(worker, failing_conn)
            other_future = executor.submit(worker)
            ready.wait()
            assert failing_future.result(timeout=5) is failing_conn
            other_conn = other_future.result(timeout=5)

        created = []
        create_connection = ai.create_database_connection

        def create(**kwargs):
            conn = create_connection(**kwargs)
            created.append(conn)
            return conn

        with patch.object(ai, "create_database_connection", side_effect=create):
            with ThreadPoolExecutor(1) as executor:
                future = executor.submit(lambda: ai.connection)
                with pytest.raises(sqlite3.OperationalError) as raised:
                    future.result(timeout=5)
        assert raised.value is error
        assert len(created) == 1
        for conn in [failing_conn, other_conn, *created]:
            with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
                conn.execute("SELECT 1")
        assert list(ai._connections.values()) == [ai.connection]
        assert ai.connection.execute("SELECT 1").fetchone() == (1,)


@pytest.mark.parametrize("registration_wins", [True, False])
def test_connection_registration_races_with_close(
    project: Project, registration_wins: bool
):
    paused = Event()
    resume = Event()
    created = []

    with AutoImport(project, memory=True) as ai:
        register_connection = ai._register_connection

        def register(conn):
            created.append(conn)
            if registration_wins:
                register_connection(conn)
            paused.set()
            assert resume.wait(timeout=5)
            if not registration_wins:
                register_connection(conn)

        def worker():
            return ai.connection.execute("SELECT 1").fetchone()

        with patch.object(ai, "_register_connection", side_effect=register):
            with ThreadPoolExecutor(1) as executor:
                future = executor.submit(worker)
                try:
                    assert paused.wait(timeout=5)
                    if registration_wins:
                        with pytest.raises(
                            exceptions.RopeError, match="wait for them to finish"
                        ):
                            ai.close()
                        assert not ai._closed
                        assert created[0] in ai._connections.values()
                    else:
                        ai.close()
                        assert ai._closed
                        assert not ai._connections
                finally:
                    resume.set()
                if registration_wins:
                    assert future.result(timeout=5) == (1,)
                else:
                    with pytest.raises(
                        exceptions.RopeError, match="AutoImport instance has been closed"
                    ):
                        future.result(timeout=5)
        assert len(created) == 1

    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        created[0].execute("SELECT 1")


def test_register_connection_after_close(project: Project):
    ai = AutoImport(project, memory=True)
    ai.close()
    conn = AutoImport.create_database_connection(memory=True)
    with pytest.raises(exceptions.RopeError, match="AutoImport instance has been closed"):
        ai._register_connection(conn)
    assert conn not in ai._connections.values()
    with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):
        conn.execute("SELECT 1")


def test_connection_setter_after_close(project: Project):
    ai = AutoImport(project, memory=True)
    ai.close()
    with closing(AutoImport.create_database_connection(memory=True)) as conn:
        with pytest.raises(exceptions.RopeError, match="AutoImport instance has been closed"):
            ai.connection = conn
        assert conn.execute("SELECT 1").fetchone() == (1,)


def test_connection_setter_replaces_existing(project: Project):
    with AutoImport(project, memory=True) as ai:
        with closing(ai.connection) as old_conn:
            assert old_conn in ai._connections.values()
            conn = AutoImport.create_database_connection(memory=True)
            ai.connection = conn
            assert ai.connection is conn
            assert conn in ai._connections.values()
            assert old_conn not in ai._connections.values()
            assert old_conn.execute("SELECT 1").fetchone() == (1,)
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        conn.execute("SELECT 1")


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
