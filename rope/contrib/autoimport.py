import ast
import pathlib
import re
import sqlite3
import sys
from concurrent.futures import ProcessPoolExecutor
from enum import Enum
from typing import Generator, List, Optional, Set, Tuple

from rope.base import exceptions, libutils, resourceobserver, taskhandle
from rope.base.project import Project
from rope.refactor import importutils


class Source(Enum):
    PROJECT = 0  # Obviously any project packages come first
    MANUAL = 1  # Any packages manually added are probably important to the user
    STANDARD = 2  # We want to favor standard library items
    SITE_PACKAGE = 3
    UNKNOWN = 4


Name = Tuple[str, str, str, int]


def _get_names(
    modpath: pathlib.Path,
    modname: str,
    package: str,
    package_source: Source,
) -> List[Name]:
    """Update the cache for global names in `modname` module

    `modname` is the name of a module.
    """
    # TODO use __all__ parsing if avalible
    if modpath.is_dir():
        names: List[Name] = []
        for file in modpath.glob("*.py"):
            names.extend(_get_names(file, modname, package, package_source))
        return names
    else:
        return list(_get_names_from_file(modpath, modname, package, package_source))


def _find_all_names_in_package(
    package_path: pathlib.Path,
    recursive=True,
    package_source: Source = None,
) -> List[Name]:
    package_name = package_path.name
    if package_source is None:
        package_source = get_package_source(package_path)
    if package_name.endswith(".egg-info"):
        return []
        # TODO add so handling
    modules: List[Tuple[pathlib.Path, str]] = []
    if package_name.endswith(".py"):
        stripped_name = package_name.removesuffix(".py")
        modules.append((package_path, stripped_name))
    if recursive:
        for sub in submodules(package_path):
            modname = (
                sub.relative_to(package_path)
                .as_posix()
                .removesuffix(".py")
                .replace("/", ".")
            )
            if modname.__contains__("_"):
                continue
            modname = package_name if modname == "." else package_name + "." + modname
            modules.append((sub, modname))
    else:
        modules.append((package_path, package_name))
    result: List[Name] = []
    for module in modules:
        result.extend(_get_names(module[0], module[1], package_name, package_source))
    return result


def _get_names_from_file(
    module: pathlib.Path,
    modname: str,
    package: str,
    package_source: Source,
) -> Generator[Name, None, None]:
    with open(module, mode="rb") as file:
        root_node = ast.parse(file.read())
    for node in ast.iter_child_nodes(root_node):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                yield (node.name, modname, package, package_source.value)


def get_package_source(
    package: pathlib.Path, project: Optional[Project] = None
) -> Source:
    """Detect the source of a given package. Rudimentary implementation."""
    if project is not None and package.as_posix().__contains__(project.address):
        return Source.PROJECT
    if package.as_posix().__contains__("site-packages"):
        return Source.SITE_PACKAGE
    if package.as_posix().startswith(sys.prefix):
        return Source.STANDARD
    else:
        return Source.UNKNOWN


class AutoImport(object):
    """A class for finding the module that provides a name

    This class maintains a cache of global names in python modules.
    Note that this cache is not accurate and might be out of date.

    """

    connection: sqlite3.Connection

    def __init__(self, project, observe=True, underlined=False, memory=True):
        """Construct an AutoImport object

        If `observe` is `True`, listen for project changes and update
        the cache.

        If `underlined` is `True`, underlined names are cached, too.
        """
        self.project = project
        self.underlined = underlined
        db_path = ":memory:" if memory else f"{project.ropefolder.path}/autoimport.db"
        self.connection = sqlite3.connect(db_path)
        self.connection.execute(
            "create table if not exists names(name TEXT, module TEXT, package TEXT, source INTEGER)"
        )
        self._check_all()
        # XXX: using a filtered observer
        observer = resourceobserver.ResourceObserver(
            changed=self._changed, moved=self._moved, removed=self._removed
        )
        if observe:
            project.add_observer(observer)

    def _check_import(self, module) -> bool:
        """
        Checks the ability to import an external package, removes it if not avalible
        """
        # Not Implemented Yet, silently will fail
        return True

    def _check_all(self):
        """
        Checks all modules and removes bad ones
        """
        pass

    def import_assist(self, starting):
        """Return a list of ``(name, module)`` tuples

        This function tries to find modules that have a global name
        that starts with `starting`.
        """
        results = self.connection.execute(
            "select name, module from names where name like (?)%", (starting,)
        ).fetchall()
        for result in results:
            if not self._check_import(result[1]):
                del results[result]
        return set(
            results
        )  # Remove duplicates from multiple occurences of the same item

    def search(self, name) -> Set[str]:
        """Searches both modules and names for an import string"""
        results: List[str] = []
        for name, module in self.connection.execute(
            "SELECT name, module FROM names WHERE name LIKE (?)", (name,)
        ):
            results.append(f"from {module} import {name}")
        for module in self.connection.execute(
            "Select module FROM names where module LIKE (?)", ("%." + name,)
        ):
            results.append(f"from {module[0].removesuffix(f'.{name}')} import {name}")
        for module in self.connection.execute(
            "Select module from names where module LIKE (?)", (name,)
        ):
            results.append(f"import {name}")
        return set(results)

    def exact_match(self, target: str):
        # TODO implement exact match
        pass

    def get_modules(self, name):
        """Return the list of modules that have global `name`"""
        results = self.connection.execute(
            "SELECT module FROM names WHERE module LIKE (?)", (name,)
        ).fetchall()
        for result in results:
            if not self._check_import(result[0]):
                del results[result]
        return set(*results)

    def get_all_names(self) -> List[str]:
        """Return the list of all cached global names"""
        self._check_all()
        results = self.connection.execute("select name from names").fetchall()
        return results

    def get_all(self) -> List[Name]:
        """Dumps the entire database"""
        self._check_all()
        results = self.connection.execute("select * from names").fetchall()
        return results

    # def get_name_locations(self, target_name):
    #     """Return a list of ``(resource, lineno)`` tuples"""
    #     result = []
    #     for name, module in self.connection.execute("select (name, module) from names"):
    #         if target_name in name:
    #             try:
    #                 pymodule = self.project.get_module(module)
    #                 if target_name in pymodule:
    #                     pyname = pymodule[target_name]
    #                     module, lineno = pyname.get_definition_location()
    #                     if module is not None:
    #                         resource = module.get_module().get_resource()
    #                         if resource is not None and lineno is not None:
    #                             result.append((resource, lineno))
    #             except exceptions.ModuleNotFoundError:
    #                 pass
    #     return result

    def generate_cache(
        self, resources=None, underlined=None, task_handle=taskhandle.NullTaskHandle()
    ):
        """Generate global name cache for project files

        If `resources` is a list of `rope.base.resource.File`, only
        those files are searched; otherwise all python modules in the
        project are cached.

        """
        if resources is None:
            resources = self.project.get_python_files()
        job_set = task_handle.create_jobset(
            "Generating autoimport cache", len(resources)
        )
        for file in resources:
            job_set.started_job("Working on <%s>" % file.path)
            self.update_resource(file, underlined)
            job_set.finished_job()

    def _handle_import_error(self, *args):
        pass

    def generate_modules_cache(
        self, modules=None, task_handle=taskhandle.NullTaskHandle()
    ):
        """Generate global name cache for modules listed in `modules`"""
        job_set = task_handle.create_jobset(
            "Generating autoimport cache for modules",
            "all" if modules is None else len(modules),
        )
        packages: List[pathlib.Path] = []
        if modules is None:
            folders = self.project.get_python_path_folders()
            for folder in folders:
                for package in pathlib.Path(folder.path).iterdir():
                    package_name = package.name
                    if (
                        self.connection.execute(
                            "select * from names where package LIKE (?)",
                            (package_name,),
                        ).fetchone()
                        is None
                    ):
                        packages.append(package)

        else:
            for modname in modules:
                # TODO: need to find path, somehow
                packages.append(modname)
        with ProcessPoolExecutor() as exectuor:
            for name_list in exectuor.map(_find_all_names_in_package, packages):
                self._add_names(name_list)

    def _add_names(self, names: List[Name]):
        self.connection.executemany(
            "insert into names(name,module,package,source) values (?,?,?,?)",
            names,
        )

    def clear_cache(self):
        """Clear all entries in global-name cache

        It might be a good idea to use this function before
        regenerating global names.

        """
        self.connection.execute("drop table names")

    def find_insertion_line(self, code):
        """Guess at what line the new import should be inserted"""
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

    def update_resource(self, resource):
        """Update the cache for global names in `resource`"""
        try:
            self._add_names(
                [
                    resource.path,
                    resource.path.name,
                    self.project.address,
                    Source.PROJECT.value,
                ]
            )

        except exceptions.ModuleSyntaxError:
            pass

    def _changed(self, resource):
        if not resource.is_folder():
            self.update_resource(resource)

    def _moved(self, resource, newresource):
        if not resource.is_folder():
            modname = libutils.modname(resource)
            self._del_if_exist(modname)
            self.update_resource(newresource)

    def _del_if_exist(self, module_name):
        self.connection.execute("delete from names where module = ?", (module_name,))

    def _removed(self, resource):
        if not resource.is_folder():
            modname = libutils.modname(resource)
            self._del_if_exist(modname)

    def close(self):
        self.connection.commit()
        self.connection.close()


def submodules(mod: pathlib.Path):
    """Simple submodule finder that doesn't try to import anything"""
    if mod.suffix == ".py" and mod.name != "__init__.py":
        return set([mod])
    if not (mod / "__init__.py").exists():
        return set()
    result = set([mod])
    for child in mod.iterdir():
        result |= submodules(child)
    return result
