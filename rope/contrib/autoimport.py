import pathlib
import re
import sqlite3
from os import listdir
from pkgutil import walk_packages
from typing import Dict

from rope.base import (builtins, exceptions, libutils, pynames, pyobjects,
                       resourceobserver, resources, taskhandle)
from rope.refactor import importutils


class AutoImport(object):
    """A class for finding the module that provides a name

    This class maintains a cache of global names in python modules.
    Note that this cache is not accurate and might be out of date.

    """

    packages: Dict[str, Dict[str, str]] = {}

    def __init__(self, project, observe=True, underlined=False):
        """Construct an AutoImport object

        If `observe` is `True`, listen for project changes and update
        the cache.

        If `underlined` is `True`, underlined names are cached, too.
        """
        self.project = project
        self.underlined = underlined
        self.connection = sqlite3.connect(f"{project.ropefolder.path}/autoimport.db")
        self.connection.execute("create table if not exists names(name, module)")
        self._check_all()
        # XXX: using a filtered observer
        observer = resourceobserver.ResourceObserver(
            changed=self._changed, moved=self._moved, removed=self._removed
        )
        if observe:
            project.add_observer(observer)

    def _check_import(self, module):
        """
        Checks the ability to import an external package, removes it if not avalible
        """
        # Not Implemented Yet, silently will fail
        pass

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
            "select (name, module) from name where name like (?)", (starting,)
        )
        for result in results:
            if not self._check_import(result(1)):
                del results[result]
        return results

    def get_modules(self, name):
        """Return the list of modules that have global `name`"""
        results = self.connection.execute(
            "SELECT module FROM names WHERE name LIKE (?)", (name,)
        ).fetchall()
        for result in results:
            if not self._check_import(result(0)):
                del results[result]
        return results

    def get_all_names(self):
        """Return the list of all cached global names"""
        self._check_all()
        results = self.connection.execute(
            "select module from names where name"
        ).fetchall()
        return results

    def get_name_locations(self, target_name):
        """Return a list of ``(resource, lineno)`` tuples"""
        result = []
        for name, module in self.connection.execute("select (name, module) "):
            if target_name in name:
                try:
                    pymodule = self.project.get_module(module)
                    if target_name in pymodule:
                        pyname = pymodule[target_name]
                        module, lineno = pyname.get_definition_location()
                        if module is not None:
                            resource = module.get_module().get_resource()
                            if resource is not None and lineno is not None:
                                result.append((resource, lineno))
                except exceptions.ModuleNotFoundError:
                    pass
        return result

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
        self, modules=None, underlined=None, task_handle=taskhandle.NullTaskHandle()
    ):
        """Generate global name cache for modules listed in `modules`"""
        job_set = task_handle.create_jobset(
            "Generating autoimport cache for modules",
            "all" if modules is None else len(modules),
        )
        if modules is None:
            folders = self.project.get_python_path_folders()
            for package in walk_packages(onerror=self._handle_import_error):
                self._generate_module_cache(
                    f"{package.name}",
                    job_set,
                    underlined,
                    task_handle,
                )

        else:
            for modname in modules:
                self._generate_module_cache(modname, job_set, underlined, task_handle)

    def _generate_module_cache(
        self, modname, job_set, underlined=None, task_handle=taskhandle.NullTaskHandle()
    ):
        job_set.started_job("Working on <%s>" % modname)
        if modname.endswith(".*"):
            # This is wildly inneffecient given that we know the path already
            mod = self.project.find_module(modname[:-2])
            if mod:
                for sub in submodules(mod):
                    self.update_resource(sub, underlined)
        else:
            self.update_module(modname, underlined)
        job_set.finished_job()

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

    def update_resource(self, resource, underlined=None):
        """Update the cache for global names in `resource`"""
        try:
            pymodule = self.project.get_pymodule(resource)
            modname = self._module_name(resource)
            self._add_names(pymodule, modname, underlined)

        except exceptions.ModuleSyntaxError:
            pass

    def update_module(self, modname, underlined=None):
        """Update the cache for global names in `modname` module

        `modname` is the name of a module.
        """
        try:
            if self.connection.execute(
                "select count(1) from names where module is (?)", (modname,)
            ):
                return
            pymodule = self.project.get_module(modname)
            self._add_names(pymodule, modname, underlined)
        except exceptions.ModuleNotFoundError:
            pass

    def _module_name(self, resource):
        return libutils.modname(resource)

    def _add_names(self, pymodule, modname, underlined):
        if underlined is None:
            underlined = self.underlined
        if isinstance(pymodule, pyobjects.PyDefinedObject):
            attributes = pymodule._get_structural_attributes()
        else:
            attributes = pymodule.get_attributes()
        for name, pyname in attributes.items():
            if underlined or name.startswith("_"):
                if isinstance(
                    pyname,
                    (pynames.AssignedName, pynames.DefinedName, builtins.BuiltinModule),
                ):
                    self.connection.execute(
                        "insert into names(name,module) values (?,?)", (name, modname)
                    )

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


def submodules(mod):
    if isinstance(mod, resources.File):
        if mod.name.endswith(".py") and mod.name != "__init__.py":
            return set([mod])
        return set()
    if not mod.has_child("__init__.py"):
        return set()
    result = set([mod])
    for child in mod.get_children():
        result |= submodules(child)
    return result
