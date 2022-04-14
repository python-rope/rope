"""AutoImport module for rope."""
import pathlib
import re
import sqlite3
import sys
from collections import OrderedDict
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from itertools import chain
from typing import Generator, Iterable, List, Optional, Tuple

from rope.base import exceptions, libutils, resourceobserver, taskhandle
from rope.base.project import Project
from rope.base.resources import Resource
from rope.contrib.autoimport.defs import ModuleFile, Name, Package, PackageType, Source
from rope.contrib.autoimport.parse import get_names
from rope.contrib.autoimport.utils import (
    get_files,
    get_modname_from_path,
    get_package_tuple,
    sort_and_deduplicate,
    sort_and_deduplicate_tuple,
)
from rope.refactor import importutils


def get_future_names(
    packages: List[Package], underlined: bool, job_set: taskhandle.JobSet
) -> Generator[Future[Iterable[Name]], None, None]:
    """Get all names as futures."""
    with ProcessPoolExecutor() as executor:
        for package in packages:
            for module in get_files(package, underlined):
                job_set.started_job(module.modname)
                if not isinstance(job_set, taskhandle.NullJobSet):
                    job_set.count += 1
                yield executor.submit(get_names, module, package)


def filter_packages(
    packages: Iterable[Package], underlined: bool, existing: List[str]
) -> Iterable[Package]:
    """Filter list of packages to parse."""
    if underlined:

        def filter_package(package: Package) -> bool:
            return package.name not in existing

    else:

        def filter_package(package: Package) -> bool:
            return package.name not in existing and not package.name.startswith("_")

    return filter(filter_package, packages)


class AutoImport:
    """A class for finding the module that provides a name.

    This class maintains a cache of global names in python modules.
    Note that this cache is not accurate and might be out of date.

    """

    connection: sqlite3.Connection
    underlined: bool
    project: Project

    def __init__(self, project, observe=True, underlined=False, memory=True):
        """Construct an AutoImport object.

        Parameters
        ___________
        project : rope.base.project.Project
            the project to use for project imports
        observe : bool
            if true, listen for project changes and update the cache.
        underlined : bool
            If `underlined` is `True`, underlined names are cached, too.
        memory : bool
            if true, don't persist to disk
        """
        self.project = project
        self.underlined = underlined
        db_path: str
        if memory or project.ropefolder is None:
            db_path = ":memory:"
        else:
            db_path = f"{project.ropefolder.path}/autoimport.db"
        self.connection = sqlite3.connect(db_path)
        self._setup_db()
        self._check_all()
        if observe:
            observer = resourceobserver.ResourceObserver(
                changed=self._changed, moved=self._moved, removed=self._removed
            )
            project.add_observer(observer)

    def _setup_db(self):
        packages_table = "(package TEXT)"
        names_table = (
            "(name TEXT, module TEXT, package TEXT, source INTEGER, type INTEGER)"
        )
        self.connection.execute(f"create table if not exists names{names_table}")
        self.connection.execute(f"create table if not exists packages{packages_table}")
        self.connection.commit()

    def import_assist(self, starting: str):
        """
        Find modules that have a global name that starts with `starting`.

        Parameters
        __________
        starting : str
            what all the names should start with
        Return
        __________
        Return a list of ``(name, module)`` tuples
        """
        results = self.connection.execute(
            "select name, module, source from names WHERE name LIKE (?)",
            (starting + "%",),
        ).fetchall()
        for result in results:
            if not self._check_import(result[1]):
                del results[result]
        return sort_and_deduplicate_tuple(
            results
        )  # Remove duplicates from multiple occurences of the same item

    def search(self, name: str, exact_match: bool = False) -> List[Tuple[str, str]]:
        """
        Search both modules and names for an import string.

        Returns list of import statement ,modname pairs
        """
        if not exact_match:
            name = name + "%"  # Makes the query a starts_with query
        results: List[Tuple[str, str, int]] = []
        for import_name, module, source in self.connection.execute(
            "SELECT name, module, source FROM names WHERE name LIKE (?)", (name,)
        ):
            results.append((f"from {module} import {import_name}", import_name, source))
        for module, source in self.connection.execute(
            "Select module, source FROM names where module LIKE (?)", ("%." + name,)
        ):
            parts = module.split(".")
            import_name = parts[-1]
            remaining = parts[0]
            for part in parts[1:-1]:
                remaining += "."
                remaining += part
            results.append(
                (f"from {remaining} import {import_name}", import_name, source)
            )
        for module, source in self.connection.execute(
            "Select module, source from names where module LIKE (?)", (name,)
        ):
            results.append((f"import {module}", module, source))
        return sort_and_deduplicate_tuple(results)

    def lsp_search(
        self, name: str, exact_match: bool = False
    ) -> Tuple[List[Tuple[str, str, int, int]], List[Tuple[str, str, int, int]]]:
        """
        Search both modules and names for an import string.

        Returns the name, import statement, source, split into normal names and modules.
        """
        if not exact_match:
            name = name + "%"  # Makes the query a starts_with query
        results_name: List[Tuple[str, str, int, int]] = []
        results_module: List[Tuple[str, str, int, int]] = []
        for import_name, module, source, name_type in self.connection.execute(
            "SELECT name, module, source, type FROM names WHERE name LIKE (?)", (name,)
        ):
            results_name.append(
                (f"from {module} import {import_name}", import_name, source, name_type)
            )
        for module, source, name_type in self.connection.execute(
            "Select module, source, type FROM names where module LIKE (?)",
            ("%." + name,),
        ):
            parts = module.split(".")
            import_name = parts[-1]
            remaining = parts[0]
            for part in parts[1:-1]:
                remaining += "."
                remaining += part
            results_module.append(
                (
                    f"from {remaining} import {import_name}",
                    import_name,
                    source,
                    name_type,
                )
            )
        for module, source, name_type in self.connection.execute(
            "Select module, source, type from names where module LIKE (?)", (name,)
        ):
            results_module.append((f"import {module}", module, source, name_type))
        return results_name, results_module

    def get_modules(self, name) -> List[str]:
        """Get the list of modules that have global `name`."""
        results = self.connection.execute(
            "SELECT module, source FROM names WHERE name LIKE (?)", (name,)
        ).fetchall()
        for result in results:
            if not self._check_import(result[0]):
                del results[result]
        return sort_and_deduplicate(results)

    def get_all_names(self) -> List[str]:
        """Get the list of all cached global names."""
        self._check_all()
        results = self.connection.execute("select name from names").fetchall()
        return results

    def _dump_all(self) -> Tuple[List[Name], List[Package]]:
        """Dump the entire database."""
        self._check_all()
        name_results = self.connection.execute("select * from names").fetchall()
        package_results = self.connection.execute("select * from packages").fetchall()
        return name_results, package_results

    def generate_cache(
        self,
        resources: List[Resource] = None,
        underlined: bool = False,
        task_handle=taskhandle.NullTaskHandle(),
    ):
        """Generate global name cache for project files.

        If `resources` is a list of `rope.base.resource.File`, only
        those files are searched; otherwise all python modules in the
        project are cached.
        """
        if resources is None:
            resources = self.project.get_python_files()
        job_set = task_handle.create_jobset(
            "Generating autoimport cache", len(resources)
        )
        # Should be very fast, so doesn't need multithreaded computation
        for file in resources:
            job_set.started_job(f"Working on {file.path}")
            self.update_resource(file, underlined, commit=False)
            job_set.finished_job()
        self.connection.commit()

    def generate_modules_cache(
        self,
        modules: List[str] = None,
        task_handle=taskhandle.NullTaskHandle(),
        single_thread: bool = False,
        underlined: bool = False,
    ):
        """
        Generate global name cache for external modules listed in `modules`.

        If no modules are provided, it will generate a cache for every module avalible.
        This method searches in your sys.path and configured python folders.
        Do not use this for generating your own project's internal names,
        use generate_resource_cache for that instead.
        """
        packages: List[Package] = []
        if self.underlined:
            underlined = True
        existing = self._get_existing()
        if modules is None:
            packages = self._get_available_packages()
        else:
            for modname in modules:
                package = self._find_package_path(modname)
                if package is None:
                    continue
                packages.append(package)
        packages = list(filter_packages(packages, underlined, existing))
        self._add_packages(packages)
        job_set = task_handle.create_jobset("Generating autoimport cache", 0)
        if single_thread:
            for package in packages:
                for module in get_files(package, underlined):
                    job_set.started_job(module.modname)
                    for name in get_names(module, package):
                        self._add_name(name)
                        job_set.finished_job()
        else:
            for future_name in as_completed(
                get_future_names(packages, underlined, job_set)
            ):
                self._add_names(future_name.result())
                job_set.finished_job()

        self.connection.commit()

    def update_module(self, module: str):
        """Update a module in the cache, or add it if it doesn't exist."""
        self._del_if_exist(module)
        self.generate_modules_cache([module])

    def close(self):
        """Close the autoimport database."""
        self.connection.commit()
        self.connection.close()

    def get_name_locations(self, name):
        """Return a list of ``(resource, lineno)`` tuples."""
        result = []
        modules = self.connection.execute(
            "select module from names where name like (?)", (name,)
        ).fetchall()
        for module in modules:
            try:
                module_name = module[0]
                if module_name.startswith(f"{self._project_name}."):
                    module_name = ".".join(module_name.split("."))
                pymodule = self.project.get_module(module_name)
                if name in pymodule:
                    pyname = pymodule[name]
                    module, lineno = pyname.get_definition_location()
                    if module is not None:
                        resource = module.get_module().get_resource()
                        if resource is not None and lineno is not None:
                            result.append((resource, lineno))
            except exceptions.ModuleNotFoundError:
                pass
        return result

    def clear_cache(self):
        """Clear all entries in global-name cache.

        It might be a good idea to use this function before
        regenerating global names.

        """
        self.connection.execute("drop table names")
        self._setup_db()
        self.connection.commit()

    def find_insertion_line(self, code):
        """Guess at what line the new import should be inserted."""
        match = re.search(r"^(def|class)\s+", code)
        if match is not None:
            code = code[: match.start()]
        try:
            pymodule = libutils.get_string_module(self.project, code)
        except exceptions.ModuleSyntaxError:
            return 1
        testmodname = "__rope_testmodule_rope"
        importinfo = importutils.NormalImport(((testmodname, None),))
        module_imports = importutils.get_module_imports(self.project, pymodule)
        module_imports.add_import(importinfo)
        code = module_imports.get_changed_source()
        offset = code.index(testmodname)
        lineno = code.count("\n", 0, offset) + 1
        return lineno

    def update_resource(
        self, resource: Resource, underlined: bool = False, commit: bool = True
    ):
        """Update the cache for global names in `resource`."""
        underlined = underlined if underlined else self.underlined
        package = get_package_tuple(self._project_path, self.project)
        if package is None or package.path is None:
            return
        resource_path: pathlib.Path = pathlib.Path(resource.real_path)
        # The project doesn't need its name added to the path,
        # since the standard python file layout accounts for that
        # so we set add_package_name to False
        resource_modname: str = get_modname_from_path(
            resource_path, package.path, add_package_name=False
        )
        module = ModuleFile(
            resource_path,
            resource_modname,
            underlined,
            resource_path.name == "__init__.py",
        )
        self._del_if_exist(module_name=resource_modname, commit=False)
        for name in get_names(module, package):
            self._add_name(name)
        if commit:
            self.connection.commit()

    def _changed(self, resource):
        if not resource.is_folder():
            self.update_resource(resource)

    def _moved(self, resource: Resource, newresource: Resource):
        if not resource.is_folder():
            modname = self._modname(resource)
            self._del_if_exist(modname)
            self.update_resource(newresource)

    def _del_if_exist(self, module_name, commit: bool = True):
        self.connection.execute("delete from names where module = ?", (module_name,))
        if commit:
            self.connection.commit()

    def _get_python_folders(self) -> List[pathlib.Path]:
        folders = self.project.get_python_path_folders()
        folder_paths = [
            pathlib.Path(folder.path) for folder in folders if folder.path != "/usr/bin"
        ]
        return list(OrderedDict.fromkeys(folder_paths))

    def _get_available_packages(self) -> List[Package]:
        packages: List[Package] = [
            Package(module, Source.BUILTIN, None, PackageType.BUILTIN)
            for module in sys.builtin_module_names
        ]
        for folder in self._get_python_folders():
            for package in folder.iterdir():
                package_tuple = get_package_tuple(package, self.project)
                if package_tuple is None:
                    continue
                packages.append(package_tuple)
        return packages

    def _add_packages(self, packages: List[Package]):
        for package in packages:
            self.connection.execute("INSERT into packages values(?)", (package.name,))

    def _get_existing(self) -> List[str]:
        existing: List[str] = list(
            chain(*self.connection.execute("select * from packages").fetchall())
        )
        existing.append(self._project_name)
        return existing

    @property
    def _project_name(self):
        package_path: pathlib.Path = pathlib.Path(self.project.address)
        package_tuple = get_package_tuple(package_path)
        if package_tuple is None:
            return None
        return package_tuple[0]

    @property
    def _project_path(self):
        return pathlib.Path(self.project.address)

    def _modname(self, resource: Resource):
        resource_path: pathlib.Path = pathlib.Path(resource.real_path)
        package_path: pathlib.Path = pathlib.Path(self.project.address)
        resource_modname: str = get_modname_from_path(
            resource_path, package_path, add_package_name=False
        )
        return resource_modname

    def _removed(self, resource):
        if not resource.is_folder():
            modname = self._modname(resource)
            self._del_if_exist(modname)

    def _add_future_names(self, names: Future[List[Name]]):
        self._add_names(names.result())

    def _add_names(self, names: Iterable[Name]):
        for name in names:
            self._add_name(name)

    def _add_name(self, name: Name):
        self.connection.execute(
            "insert into names values (?,?,?,?,?)",
            (
                name.name,
                name.modname,
                name.package,
                name.source.value,
                name.name_type.value,
            ),
        )

    def _check_import(self, module: pathlib.Path) -> bool:
        """
        Check the ability to import an external package, removes it if not avalible.

        Parameters
        ----------
        module: pathlib.path
            The module to check
        Returns
        ----------
        """
        # Not Implemented Yet, silently will fail
        return True

    def _check_all(self):
        """Check all modules and removes bad ones."""
        pass

    def _find_package_path(self, target_name: str) -> Optional[Package]:
        if target_name in sys.builtin_module_names:
            return Package(target_name, Source.BUILTIN, None, PackageType.BUILTIN)
        for folder in self._get_python_folders():
            for package in folder.iterdir():
                package_tuple = get_package_tuple(package, self.project)
                if package_tuple is None:
                    continue
                name, source, package_path, package_type = package_tuple
                if name == target_name:
                    return package_tuple

        return None
