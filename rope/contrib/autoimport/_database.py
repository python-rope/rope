import json
import secrets
import sqlite3
from datetime import datetime
from hashlib import sha256
from typing import Iterable, List, Optional, Tuple

from threading import local
from rope.base import versioning
from rope.base.project import Project
from rope.contrib.autoimport import models
from rope.contrib.autoimport.defs import (
    Name,
    Package,
)


class Database:
    project: Project
    memory: bool

    def __init__(self, project: Project, memory: bool = False):
        self.thread_local = local()
        self.connection = self.create_database_connection(
            project=project,
            memory=memory,
        )
        self.project = project
        self.memory = memory
        self._setup_db()

    @classmethod
    def create_database_connection(
        cls,
        *,
        project: Optional[Project] = None,
        memory: bool = False,
    ) -> sqlite3.Connection:
        """
        Create an sqlite3 connection

        project : rope.base.project.Project
            the project to use for project imports
        memory : bool
            if true, don't persist to disk
        """

        def calculate_project_hash(data: str) -> str:
            return sha256(data.encode()).hexdigest()

        if not memory and project is None:
            raise Exception("if memory=False, project must be provided")
        if memory or project is None or project.ropefolder is None:
            # Allows the in-memory db to be shared across threads
            # See https://www.sqlite.org/inmemorydb.html
            project_hash: str
            if project is None:
                project_hash = secrets.token_hex()
            elif project.ropefolder is None:
                project_hash = calculate_project_hash(project.address)
            else:
                project_hash = calculate_project_hash(project.ropefolder.real_path)
            return sqlite3.connect(
                f"file:rope-{project_hash}:?mode=memory&cache=shared", uri=True
            )
        else:
            return sqlite3.connect(project.ropefolder.pathlib / "autoimport.db")

    def _setup_db(self):
        models.Metadata.create_table(self.connection)
        version_hash = list(
            self._execute(models.Metadata.objects.select("version_hash"))
        )
        current_version_hash = versioning.calculate_version_hash(self.project)
        if not version_hash or version_hash[0][0] != current_version_hash:
            self.clear_cache()

    def clear_cache(self):
        """Clear all entries in global-name cache.

        It might be a good idea to use this function before
        regenerating global names.

        """
        with self.connection:
            self._execute(models.Name.objects.drop_table())
            self._execute(models.Package.objects.drop_table())
            self._execute(models.Metadata.objects.drop_table())
            models.Name.create_table(self.connection)
            models.Package.create_table(self.connection)
            models.Metadata.create_table(self.connection)
            data = (
                versioning.calculate_version_hash(self.project),
                json.dumps(versioning.get_version_hash_data(self.project)),
                datetime.utcnow().isoformat(),
            )
            assert models.Metadata.columns == [
                "version_hash",
                "hash_data",
                "created_at",
            ]
            self._execute(models.Metadata.objects.insert_into(), data)

            self.connection.commit()

    @property
    def connection(self) -> sqlite3.Connection:
        """
        Creates a new connection if called from a new thread.

        This makes sure AutoImport can be shared across threads.
        """
        if not hasattr(self.thread_local, "connection"):
            self.thread_local.connection = self.create_database_connection(
                project=self.project,
                memory=self.memory,
            )
        return self.thread_local.connection

    @connection.setter
    def connection(self, value: sqlite3.Connection):
        self.thread_local.connection = value

    def close(self):
        """Close the autoimport database."""
        self.connection.commit()
        self.connection.close()

    def _execute(self, query: models.FinalQuery, *args, **kwargs):
        assert isinstance(query, models.FinalQuery)
        return self.connection.execute(query._query, *args, **kwargs)

    def _executemany(self, query: models.FinalQuery, *args, **kwargs):
        assert isinstance(query, models.FinalQuery)
        return self.connection.executemany(query._query, *args, **kwargs)

    @staticmethod
    def _convert_name(name: Name) -> tuple:
        return (
            name.name,
            name.modname,
            name.package,
            name.source.value,
            name.name_type.value,
        )

    def _dump_all(self) -> Tuple[List[Name], List[Package]]:
        """Dump the entire database."""
        name_results = self._execute(models.Name.objects.select_star()).fetchall()
        package_results = self._execute(models.Package.objects.select_star()).fetchall()
        return name_results, package_results

    def add_names(self, names: Iterable[Name]):
        if names is not None:
            self._executemany(
                models.Name.objects.insert_into(),
                [self._convert_name(name) for name in names],
            )

    def add_name(self, name: Name):
        self._execute(models.Name.objects.insert_into(), self._convert_name(name))

    def add_packages(self, packages: List[Package]):
        data = [(p.name, str(p.path)) for p in packages]
        self._executemany(models.Package.objects.insert_into(), data)

    def delete_package(self, package_name: str):
        self._execute(models.Package.delete_by_package_name, (package_name,))

    def commit(self):
        self.connection.commit()
