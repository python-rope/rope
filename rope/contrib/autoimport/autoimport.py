"""AutoImport module for rope."""
import pathlib
import re
import sqlite3
import sys
from concurrent.futures import ProcessPoolExecutor
from itertools import chain
from typing import List, Optional, Tuple

from rope.base import exceptions, libutils, resourceobserver, taskhandle
from rope.base.project import Project
from rope.base.resources import Resource
from rope.refactor import importutils

from .defs import Name, Package, PackageType, Source
from .parse import (find_all_names_in_package, get_names_from_compiled,
                    get_names_from_file)
from .utils import (get_modname_from_path, get_package_name_from_path,
                    sort_and_deduplicate, sort_and_deduplicate_tuple)


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
        db_path = ":memory:" if memory else f"{project.ropefolder.path}/autoimport.db"
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
        names_table = "(name TEXT, module TEXT, package TEXT, source INTEGER)"
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

    def search(self, name) -> List[str]:
        """Search both modules and names for an import string."""
        results: List[Tuple[str, int]] = []
        for module, source in self.connection.execute(
            "SELECT module, source FROM names WHERE name LIKE (?)", (name,)
        ):
            results.append((f"from {module} import {name}", source))
        for module, source in self.connection.execute(
            "Select module, source FROM names where module LIKE (?)", ("%." + name,)
        ):
            results.append(
                (f"from {module.removesuffix(f'.{name}')} import {name}", source)
            )
        for module, source in self.connection.execute(
            "Select module, source from names where module LIKE (?)", (name,)
        ):
            results.append((f"import {name}", source))
        return sort_and_deduplicate(results)

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
    ):
        """
        Generate global name cache for external modules listed in `modules`.

        If no modules are provided, it will generate a cache for every module avalible.
        This method searches in your sys.path and configured python folders.
        Do not use this for generating your own project's internal names,
        use generate_resource_cache for that instead.
        """
        packages: List[pathlib.Path] = []
        compiled_packages: List[str] = []
        to_add: List[Package] = []
        if modules is None:
            packages, compiled_packages, to_add = self._get_avalible_packages()
        else:
            existing = self._get_existing()
            for modname in modules:
                mod_tuple = self._find_package_path(modname)
                if mod_tuple is None:
                    continue
                package_path, package_name, package_type = mod_tuple
                if package_name in existing:
                    continue
                if package_type in (PackageType.COMPILED, PackageType.BUILTIN):
                    compiled_packages.append(package_name)
                else:
                    assert package_path  # Should only return none for a builtin
                    packages.append(package_path)
                to_add.append((package_name,))
        self._add_packages(to_add)
        with ProcessPoolExecutor() as exectuor:
            for name_list in exectuor.map(find_all_names_in_package, packages):
                self._add_names(name_list)
            for name_list in exectuor.map(get_names_from_compiled, compiled_packages):
                self._add_names(name_list)

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
        names = self.connection.execute(
            "select module from names where name like (?)", (name,)
        ).fetchall()
        for module in names:
            try:
                module_name = module[0].removeprefix(f"{self._project_name}.")
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

    def _get_avalible_packages(
        self, underlined: bool = False
    ) -> Tuple[List[pathlib.Path], List[str], List[Package]]:
        packages: List[pathlib.Path] = []
        package_names: List[
            Package
        ] = []  # List of packages to add to the package table
        # Get builtins first
        compiled_packages: List[str] = list(sys.builtin_module_names)
        folders = self.project.get_python_path_folders()
        existing = self._get_existing()
        underlined = underlined if underlined else self.underlined
        for folder in folders:
            for package in pathlib.Path(folder.path).iterdir():
                package_tuple = get_package_name_from_path(package)
                if package_tuple is None:
                    continue
                package_name, package_type = package_tuple
                if package_name in existing:
                    continue
                if package_name.startswith("_") and not underlined:
                    continue
                if package_type == PackageType.COMPILED:
                    compiled_packages.append(package_name)
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

    def _add_names(self, names: List[Name]):
        self.connection.executemany(
            "insert into names(name,module,package,source) values (?,?,?,?)",
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
        for folder in self.project.get_python_path_folders():
            for package in pathlib.Path(folder.path).iterdir():
                package_tuple = get_package_name_from_path(package)
                if package_tuple is None:
                    continue
                name, package_type = package_tuple
                if name == target_name:
                    return (package, name, package_type)
        return None
