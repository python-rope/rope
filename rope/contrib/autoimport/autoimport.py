"""AutoImport module for rope."""
import logging
import pathlib
import re
import sqlite3
import sys
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from itertools import chain, repeat
from typing import List, Optional, Tuple, Iterable

from rope.base import exceptions, libutils, resourceobserver, taskhandle
from rope.base.project import Project
from rope.base.resources import Resource
from rope.contrib.autoimport.defs import Name, Package, PackageType, Source
from rope.contrib.autoimport.parse import (find_all_names_in_package,
                                           get_names_from_compiled,
                                           get_names_from_file)
from rope.contrib.autoimport.utils import (get_modname_from_path,
                                           get_package_name_from_path,
                                           get_package_source,
                                           sort_and_deduplicate,
                                           sort_and_deduplicate_tuple)
from rope.refactor import importutils

logger = logging.getLogger(__name__)


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
        packages_table = "(pacakge TEXT)"
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
        for import_name, module, source, type in self.connection.execute(
            "SELECT name, module, source, type FROM names WHERE name LIKE (?)", (name,)
        ):
            results_name.append(
                (f"from {module} import {import_name}", import_name, source, type)
            )
        for module, source, type in self.connection.execute(
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
                (f"from {remaining} import {import_name}", import_name, source, type)
            )
        for module, source, type in self.connection.execute(
            "Select module, source from names where module LIKE (?)", (name,)
        ):
            results_module.append((f"import {module}", module, source, type))
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

    def generate_resource_cache(
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
        packages: List[pathlib.Path] = []
        compiled_packages: List[Tuple[str, Source]] = []
        to_add: List[Package] = []
        if self.underlined:
            underlined = True
        if modules is None:
            packages, compiled_packages, to_add = self._get_avalible_packages(
                underlined
            )
        else:
            existing = self._get_existing()
            for modname in modules:
                mod_tuple = self._find_package_path(modname)
                if mod_tuple is None:
                    continue
                package_path, package_name, package_type = mod_tuple
                if package_name.startswith("_") and not underlined:
                    continue
                if package_name in existing:
                    continue
                if package_type in (PackageType.COMPILED, PackageType.BUILTIN):
                    if package_type is PackageType.COMPILED:
                        assert (
                            package_path is not None
                        )  # It should have been found, and isn't a builtin
                        source = get_package_source(package_path, self.project)
                    else:
                        source = Source.BUILTIN
                    compiled_packages.append((package_name, source))
                else:
                    assert package_path  # Should only return none for a builtin
                    packages.append(package_path)
                to_add.append((package_name,))
        self._add_packages(to_add)
        if single_thread:
            for package in packages:
                self._add_names(
                    find_all_names_in_package(package, underlined=underlined)
                )
        else:
            underlined_list = repeat(underlined, len(packages))
            with ProcessPoolExecutor() as exectuor:
                for name_list in exectuor.map(
                    find_all_names_in_package, packages, underlined_list
                ):
                    self._add_names(name_list)
        for compiled_package, source in compiled_packages:
            try:
                self._add_names(
                    get_names_from_compiled(compiled_package, source, underlined)
                )
            except Exception as e:
                logger.error(
                    f"{compiled_package} could not be imported for autoimport analysis"
                )
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
        resource_path: pathlib.Path = pathlib.Path(resource.real_path)
        package_path: pathlib.Path = self._project_path
        underlined = underlined if underlined else self.underlined
        # The project doesn't need its name added to the path,
        # since the standard python file layout accounts for that
        # so we set add_package_name to False
        resource_modname: str = get_modname_from_path(
            resource_path, package_path, add_package_name=False
        )
        package_tuple = get_package_name_from_path(package_path)
        if package_tuple is None:
            return
        package_name = package_tuple[0]
        self._del_if_exist(module_name=resource_modname, commit=False)
        names = get_names_from_file(
            resource_path,
            resource_modname,
            package_name,
            Source.PROJECT,
            underlined=underlined,
        )
        self._add_names(names)
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

    def _get_avalible_packages(
        self, underlined: bool = False
    ) -> Tuple[List[pathlib.Path], List[Tuple[str, Source]], List[Package]]:
        packages: List[pathlib.Path] = []
        package_names: List[
            Package
        ] = []  # List of packages to add to the package table
        # Get builtins first
        compiled_packages: List[Tuple[str, Source]] = [
            (module, Source.BUILTIN) for module in sys.builtin_module_names
        ]
        existing = self._get_existing()
        underlined = underlined if underlined else self.underlined
        for folder in self._get_python_folders():
            for package in folder.iterdir():
                package_tuple = get_package_name_from_path(package)
                if package_tuple is None:
                    continue
                package_name, package_type = package_tuple
                if package_name in existing:
                    continue
                if package_name.startswith("_") and not underlined:
                    continue
                if package_type == PackageType.COMPILED:
                    compiled_packages.append(
                        (package_name, get_package_source(package, self.project))
                    )
                else:
                    packages.append(package)
                package_names.append((package_name,))
        return packages, compiled_packages, package_names

    def _add_packages(self, packages: List[Package]):
        self.connection.executemany("INSERT into packages values(?)", packages)

    def _get_existing(self) -> List[str]:
        existing: List[str] = list(
            chain(*self.connection.execute("select * from packages").fetchall())
        )
        existing.append(self._project_name)
        return existing

    @property
    def _project_name(self):
        package_path: pathlib.Path = pathlib.Path(self.project.address)
        package_tuple = get_package_name_from_path(package_path)
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

    def _add_names(self, names: Iterable[Name]):
        self.connection.executemany(
            "insert into names(name,module,package,source) values (?,?,?,?,?)",
            names,
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

    def _find_package_path(
        self, target_name: str
    ) -> Optional[Tuple[Optional[pathlib.Path], str, PackageType]]:
        if target_name in sys.builtin_module_names:
            return (None, target_name, PackageType.BUILTIN)
        for folder in self._get_python_folders():
            for package in folder.iterdir():
                package_tuple = get_package_name_from_path(package)
                if package_tuple is None:
                    continue
                name, package_type = package_tuple
                if name == target_name:
                    return (package, name, package_type)
        return None
