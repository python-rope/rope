import ast
import pathlib
import re
import sqlite3
import sys
from enum import Enum
from typing import Dict, Generator, List, Optional, Tuple

from rope.base import (builtins, exceptions, libutils, pynames, pyobjects,
                       resourceobserver, resources, taskhandle)
from rope.base.project import File, Folder
from rope.refactor import importutils


class Source(Enum):
    PROJECT = 0  # Obviously any project packages come first
    MANUAL = 1  # Any packages manually added are probably important to the user
    STANDARD = 2  # We want to favor standard library items
    SITE_PACKAGE = 3
    UNKNOWN = 4


def get_package_source(package: pathlib.Path) -> Source:
    """Detect the source of a given package. Rudimentary implementation."""
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
            "select name, module from names where name like (?)", (starting,)
        ).fetchall()
        for result in results:
            if not self._check_import(result[1]):
                del results[result]
        return results

    def exact_match(self, target: str):
        # TODO implement exact match
        pass

    def get_modules(self, name):
        """Return the list of modules that have global `name`"""
        results = self.connection.execute(
            "SELECT module FROM names WHERE name LIKE (?)", (name,)
        ).fetchall()
        for result in results:
            if not self._check_import(result[0]):
                del results[result]
        return results

    def get_all_names(self):
        """Return the list of all cached global names"""
        self._check_all()
        results = self.connection.execute("select name from names").fetchall()
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
        if modules is None:
            folders = self.project.get_python_path_folders()
            for folder in folders:
                for package in pathlib.Path(folder.path).iterdir():
                    self._generate_module_cache(
                        package,
                        job_set,
                        task_handle,
                    )

        else:
            for modname in modules:
                # TODO: need to find path
                self._generate_module_cache(
                    modname, job_set, task_handle, package_source=Source.MANUAL
                )

    def _generate_module_cache(
        self,
        packagepath: pathlib.Path,
        job_set,
        task_handle=taskhandle.NullTaskHandle(),
        recursive=True,
        package_source: Source = None,
    ):
        if package_source is None:
            package_source = get_package_source(packagepath)
        package_name = packagepath.name
        job_set.started_job("Working on <%s>" % packagepath.name)
        if package_name.endswith(".egg-info"):
            return
        # TODO add so handling
        if self.connection.execute(
            "select * from names where package is (?)", (package_name,)
        ).fetchone() is not None:
            return
        if recursive:
            for sub in submodules(packagepath):
                modname = (
                    sub.relative_to(packagepath)
                    .as_posix()
                    .removesuffix(".py")
                    .replace("/", ".")
                )
                if modname.__contains__("_"):
                    continue
                modname = (
                    package_name if modname == "." else package_name + "." + modname
                )
                self._update_module(sub, modname, packagepath.name, package_source)
        else:
            self._update_module(
                packagepath, packagepath.name, packagepath.name, package_source
            )
        job_set.finished_job()

    def _get_names(
        self,
        module: pathlib.Path,
        modname: str,
        package: str,
        package_source: Source,
    ) -> Generator[Tuple[str, str, str, int], None, None]:
        with open(module, mode="rb") as file:
            root_node = ast.parse(file.read())
        for node in ast.iter_child_nodes(root_node):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not node.name.startswith("_"):
                    yield (node.name, modname, package, package_source.value)

    def _add_names(self, names_to_add, *args):
        self.connection.executemany(
            "insert into names(name,module,package,source) values (?,?,?,?)",
            names_to_add(*args),
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

    # def update_resource(self, resource, underlined=None):
    #     """Update the cache for global names in `resource`"""
    #     try:
    #         pymodule = self.project.get_pymodule(resource)
    #         modname = self._module_name(resource)
    #         self._add_names(pymodule, modname, underlined)
    #
    #     except exceptions.ModuleSyntaxError:
    #         pass
    #
    def _update_module(
        self,
        modpath: pathlib.Path,
        modname: str,
        package: str,
        package_source: Source,
    ):
        """Update the cache for global names in `modname` module

        `modname` is the name of a module.
        """
        # TODO use __all__ parsing if avalible
        if modpath.is_dir():
            for file in modpath.glob("*.py"):
                self._update_module(file, modname, package, package_source)

        else:
            self._add_names(self._get_names, modpath, modname, package, package_source)

    def _module_name(self, resource):
        return libutils.modname(resource)

    # def _add_names(self, pymodule, modname, underlined):
    #     if underlined is None:
    #         underlined = self.underlined
    #     if isinstance(pymodule, pyobjects.PyDefinedObject):
    #         attributes = pymodule._get_structural_attributes()
    #     else:
    #         attributes = pymodule.get_attributes()
    #     for name, pyname in attributes.items():
    #         if underlined or name.startswith("_"):
    #             if isinstance(
    #                 pyname,
    #                 (pynames.AssignedName, pynames.DefinedName, builtins.BuiltinModule),
    #             ):
    #                 self.connection.execute(
    #                     "insert into names(name,module) values (?,?)", (name, modname)
    #                 )

    def _changed(self, resource):
        if not resource.is_folder():
            self.update_resource(resource)

    def _moved(self, resource, newresource):
        if not resource.is_folder():
            modname = self._module_name(resource)
            self._del_if_exist(modname)
            self.update_resource(newresource)

    def _del_if_exist(self, module_name):
        self.connection.execute("delete from names where module = ?", (module_name,))

    def _removed(self, resource):
        if not resource.is_folder():
            modname = self._module_name(resource)
            self._del_if_exist(modname)

    def close(self):
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
