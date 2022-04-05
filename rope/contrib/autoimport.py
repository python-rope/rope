import ast
import pathlib
import re
import sqlite3
import sys
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from enum import Enum
from typing import List, Optional, Set, Tuple

from rope.base import exceptions, libutils, resourceobserver, taskhandle
from rope.base.project import Project
from rope.base.resources import Resource
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
    package_name: str,
    package_source: Source,
    underlined: bool = False,
) -> List[Name]:
    """Update the cache for global names in `modname` module

    `modname` is the name of a module.
    """
    # TODO use __all__ parsing if avalible
    if modpath.is_dir():
        names: List[Name]
        if modpath / "__init__.py":
            names = _get_names_from_file(
                modpath / "__init__.py",
                modname,
                package_name,
                package_source,
                only_all=True,
            )
            if len(names) > 0:
                return names
        names = []
        for file in modpath.glob("*.py"):
            names.extend(
                _get_names_from_file(
                    file,
                    modname + f".{file.name.removesuffix('.py')}",
                    package_name,
                    package_source,
                    underlined=underlined,
                )
            )
        return names
    else:
        return _get_names_from_file(
            modpath, modname, package_name, package_source, underlined=underlined
        )


class PackageType(Enum):
    STANDARD = 1  # Just a folder
    COMPILED = 2  # .so module
    SINGLE_FILE = 3  # a .py file


def _get_package_name_from_path(
    package_path: pathlib.Path,
) -> Optional[Tuple[str, PackageType]]:
    package_name = package_path.name
    if package_name.endswith(".egg-info"):
        return None
    if package_name.endswith(".so"):
        name = package_name.split(".")[0]
        return (name, PackageType.COMPILED)
        # TODO add so handling
    if package_name.endswith(".py"):
        stripped_name = package_name.removesuffix(".py")
        return (stripped_name, PackageType.SINGLE_FILE)
    return (package_name, PackageType.STANDARD)


def _get_modname_from_path(modpath: pathlib.Path, package_path: pathlib.Path) -> str:
    package_name: str = package_path.name
    modname = (
        modpath.relative_to(package_path)
        .as_posix()
        .removesuffix(".py")
        .replace("/", ".")
    )
    modname = package_name if modname == "." else package_name + "." + modname
    return modname


def _find_all_names_in_package(
    package_path: pathlib.Path,
    recursive=True,
    package_source: Source = None,
    underlined: bool = False,
) -> List[Name]:
    package_tuple = _get_package_name_from_path(package_path)
    if package_tuple is None:
        return []
    package_name, package_type = package_tuple
    if package_source is None:
        package_source = get_package_source(package_path)
    modules: List[Tuple[pathlib.Path, str]] = []
    if package_type is PackageType.SINGLE_FILE:
        modules.append((package_path, package_name))
    elif package_type is PackageType.COMPILED:
        return []
    elif recursive:
        for sub in _submodules(package_path):
            modname = _get_modname_from_path(sub, package_path)
            if underlined or modname.__contains__("_"):
                continue  # Exclude private items
            modules.append((sub, modname))
    else:
        modules.append((package_path, package_name))
    result: List[Name] = []
    for module in modules:
        result.extend(
            _get_names(module[0], module[1], package_name, package_source, underlined)
        )
    return result


def _get_names_from_file(
    module: pathlib.Path,
    modname: str,
    package: str,
    package_source: Source,
    only_all: bool = False,
    underlined: bool = False,
) -> List[Name]:
    with open(module, mode="rb") as file:
        try:
            root_node = ast.parse(file.read())
        except SyntaxError as e:
            print(e)
            return []
    results: List[Name] = []
    for node in ast.iter_child_nodes(root_node):
        node_names: List[str] = []
        if isinstance(node, ast.Assign):
            for target in node.targets:
                try:
                    assert isinstance(target, ast.Name)
                    if target.id == "__all__":
                        # TODO add tuple handling
                        all_results: List[Name] = []
                        assert isinstance(node.value, ast.List)
                        for item in node.value.elts:
                            assert isinstance(item, ast.Constant)
                            all_results.append(
                                (
                                    str(item.value),
                                    modname,
                                    package,
                                    package_source.value,
                                )
                            )
                        return all_results
                    else:
                        node_names.append(target.id)
                except (AttributeError, AssertionError):
                    # TODO handle tuple assignment
                    pass
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            node_names = [node.name]
        for node_name in node_names:
            if underlined or not node_name.startswith("_"):
                results.append((node_name, modname, package, package_source.value))
    if only_all:
        return []
    return results


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


def _sort_and_deduplicate(results: List[Tuple[str, int]]) -> List[str]:
    if len(results) == 0:
        return []
    results.sort(key=lambda y: y[-1])
    results_sorted = list(zip(*results))[0]
    return list(OrderedDict.fromkeys(results_sorted))


def _sort_and_deduplicate_tuple(
    results: List[Tuple[str, str, int]]
) -> List[Tuple[str, str]]:
    if len(results) == 0:
        return []
    results.sort(key=lambda y: y[-1])
    results_sorted = []
    for result in results:
        results_sorted.append(result[:-1])
    return list(OrderedDict.fromkeys(results_sorted))


class AutoImport(object):
    """A class for finding the module that provides a name

    This class maintains a cache of global names in python modules.
    Note that this cache is not accurate and might be out of date.

    """

    connection: sqlite3.Connection
    underlined: bool
    project: Project

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
        self._setup_db()
        self._check_all()
        if observe:
            observer = resourceobserver.ResourceObserver(
                changed=self._changed, moved=self._moved, removed=self._removed
            )
            project.add_observer(observer)

    def _setup_db(self):
        self.connection.execute(
            "create table if not exists names(name TEXT, module TEXT, package TEXT, source INTEGER)"
        )

    def import_assist(self, starting):
        """Return a list of ``(name, module)`` tuples

        This function tries to find modules that have a global name
        that starts with `starting`.
        """
        results = self.connection.execute(
            "select name, module, source from names WHERE name LIKE (?)",
            (starting + "%",),
        ).fetchall()
        for result in results:
            if not self._check_import(result[1]):
                del results[result]
        return _sort_and_deduplicate_tuple(
            results
        )  # Remove duplicates from multiple occurences of the same item

    def search(self, name) -> List[str]:
        """Searches both modules and names for an import string"""
        results: List[Tuple[str, int]] = []
        for name, module, source in self.connection.execute(
            "SELECT name, module, source FROM names WHERE name LIKE (?)", (name,)
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
        return _sort_and_deduplicate(results)

    def get_modules(self, name) -> List[str]:
        """Return the list of modules that have global `name`"""
        results = self.connection.execute(
            "SELECT module, source FROM names WHERE name LIKE (?)", (name,)
        ).fetchall()
        for result in results:
            if not self._check_import(result[0]):
                del results[result]
        return _sort_and_deduplicate(results)

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

    def generate_resource_cache(
        self,
        resources=None,
        underlined: bool = False,
        task_handle=taskhandle.NullTaskHandle(),
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

    def generate_modules_cache(
        self,
        modules=None,
        task_handle=taskhandle.NullTaskHandle(),
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
                    package_tuple = _get_package_name_from_path(package)
                    if package_tuple is None:
                        continue
                    package_name = package_tuple[0]
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
                package_path = self._find_package_path(modname)
                print(package_path)
                if package_path is None:
                    continue
                packages.append(package_path)
        with ProcessPoolExecutor() as exectuor:
            for name_list in exectuor.map(_find_all_names_in_package, packages):
                self._add_names(name_list)

    def update_module(self, module: str):
        self.generate_modules_cache([module])

    def close(self):
        self.connection.commit()
        self.connection.close()

    def get_name_locations(self, name):
        """Return a list of ``(resource, lineno)`` tuples"""
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
        """Clear all entries in global-name cache

        It might be a good idea to use this function before
        regenerating global names.

        """
        self.connection.execute("drop table names")
        self._setup_db()
        self.connection.commit()

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

    def update_resource(self, resource: Resource, underlined: bool = False):
        """Update the cache for global names in `resource`"""
        resource_path: pathlib.Path = pathlib.Path(resource.real_path)
        package_path: pathlib.Path = pathlib.Path(self.project.address)
        resource_modname: str = _get_modname_from_path(resource_path, package_path)
        package_tuple = _get_package_name_from_path(package_path)
        underlined = underlined if underlined else self.underlined
        if package_tuple is None:
            return None
        package_name = package_tuple[0]
        names = _get_names_from_file(
            resource_path,
            resource_modname,
            package_name,
            Source.PROJECT,
            underlined=underlined,
        )
        self._add_names(names)

    def _changed(self, resource):
        if not resource.is_folder():
            self.update_resource(resource)

    def _moved(self, resource: Resource, newresource: Resource):
        if not resource.is_folder():
            modname = self._modname(resource)
            self._del_if_exist(modname)
            self.update_resource(newresource)

    def _del_if_exist(self, module_name):
        self.connection.execute("delete from names where module = ?", (module_name,))
        self.connection.commit()

    @property
    def _project_name(self):
        package_path: pathlib.Path = pathlib.Path(self.project.address)
        package_tuple = _get_package_name_from_path(package_path)
        if package_tuple is None:
            return None
        return package_tuple[0]

    def _modname(self, resource: Resource):
        resource_path: pathlib.Path = pathlib.Path(resource.real_path)
        package_path: pathlib.Path = pathlib.Path(self.project.address)
        resource_modname: str = _get_modname_from_path(resource_path, package_path)
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
        self.connection.commit()

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

    def _find_package_path(self, package_name: str) -> Optional[pathlib.Path]:
        for folder in self.project.get_python_path_folders():
            for package in pathlib.Path(folder.path).iterdir():
                package_tuple = _get_package_name_from_path(package)
                if package_tuple is None:
                    continue
                if package_tuple[0] == package_name:
                    return package
        return None


def _submodules(mod: pathlib.Path) -> Set[pathlib.Path]:
    """Simple submodule finder that doesn't try to import anything"""
    result = set()
    if mod.is_dir() and (mod / "__init__.py").exists():
        result.add(mod)
        for child in mod.iterdir():
            result |= _submodules(child)
    return result
    return result
