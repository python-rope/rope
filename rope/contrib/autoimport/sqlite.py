"""AutoImport module for rope."""
import contextlib
import re
import sys
import warnings
from collections import OrderedDict
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from itertools import chain
from pathlib import Path
from typing import Generator, Iterable, Iterator, List, Optional, Set, Tuple
from rope.contrib.autoimport._database import Database
from rope.base import exceptions, libutils, resourceobserver, taskhandle
from rope.base.project import Project
from rope.base.resources import Resource
from rope.contrib.autoimport import models
from rope.contrib.autoimport.defs import (
    ModuleFile,
    ModuleInfo,
    NameType,
    Package,
    PackageType,
    SearchResult,
    Source,
    Name,
)
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
    modules: Iterable[Tuple[Package, ModuleInfo]],
    job_set: taskhandle.BaseJobSet,
) -> Generator[Future, None, None]:
    """Get all names as futures."""
    with ProcessPoolExecutor() as executor:
        for package, module in modules:
            job_set.started_job(module.modname)
            job_set.increment()
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


_deprecated_default: bool = object()  # type: ignore


class AutoImport:
    """A class for finding the module that provides a name.

    This class maintains a cache of global names in python modules.
    Note that this cache is not accurate and might be out of date.

    """

    database: Database
    memory: bool
    project: Project
    project_package: Package
    underlined: bool

    def __init__(
        self,
        project: Project,
        observe: bool = True,
        underlined: bool = False,
        memory: bool = _deprecated_default,
    ):
        """Construct an AutoImport object.

        Parameters
        ___________
        project : rope.base.project.Project
            the project to use for project imports
        observe : bool
            if true, listen for project changes and update the cache.
        underlined : bool
            If `underlined` is `True`, underlined names are cached, too.
        memory:
            If true, don't persist to disk

            DEPRECATION NOTICE: The default value will change to use an on-disk
            database by default in the future. If you want to use an in-memory
            database, you need to pass `memory=True` explicitly:

                autoimport = AutoImport(..., memory=True)
        """
        self.project = project
        project_package = get_package_tuple(project.root.pathlib, project)
        assert project_package is not None
        assert project_package.path is not None
        self.project_package = project_package
        self.underlined = underlined
        self.memory = memory
        if memory is _deprecated_default:
            self.memory = True
            warnings.warn(
                "The default value for `AutoImport(memory)` argument will "
                "change to use an on-disk database by default in the future. "
                "If you want to use an in-memory database, you need to pass "
                "`AutoImport(memory=True)` explicitly.",
                DeprecationWarning,
            )
        self.database = Database(self.project, self.memory)
        if observe:
            observer = resourceobserver.ResourceObserver(
                changed=self._changed, moved=self._moved, removed=self._removed
            )
            project.add_observer(observer)

    def import_assist(self, starting: str):
        """
        Find modules that have a global name that starts with `starting`.

        For a more complete list, use the search or search_full methods.

        Parameters
        __________
        starting : str
            what all the names should start with
        Return
        __________
        Return a list of ``(name, module)`` tuples
        """
        results = self.database._execute(
            models.Name.import_assist.select("name", "module", "source"), (starting,)
        ).fetchall()
        return sort_and_deduplicate_tuple(
            results
        )  # Remove duplicates from multiple occurrences of the same item

    def search(self, name: str, exact_match: bool = False) -> List[Tuple[str, str]]:
        """
        Search both modules and names for an import string.

        This is a simple wrapper around search_full with basic sorting based on Source.

        Returns a sorted list of import statement, modname pairs
        """
        results: List[Tuple[str, str, int]] = [
            (statement, import_name, source)
            for statement, import_name, source, type in self.search_full(
                name, exact_match
            )
        ]
        return sort_and_deduplicate_tuple(results)

    def search_full(
        self,
        name: str,
        exact_match: bool = False,
        ignored_names: Optional[Set[str]] = None,
    ) -> Generator[SearchResult, None, None]:
        """
        Search both modules and names for an import string.

        Parameters
        __________
        name: str
            Name to search for
        exact_match: bool
            If using exact_match, only search for that name.
            Otherwise, search for any name starting with that name.
        ignored_names : Set[str]
            Will ignore any names in this set

        Return
        __________
        Unsorted Generator of SearchResults. Each is guaranteed to be unique.
        """
        if ignored_names is None:
            ignored_names = set()
        results = set(self._search_name(name, exact_match))
        results = results.union(self._search_module(name, exact_match))
        for result in results:
            if result.name not in ignored_names:
                yield result

    def _search_name(
        self, name: str, exact_match: bool = False
    ) -> Generator[SearchResult, None, None]:
        """
        Search both names for available imports.

        Returns the import statement, import name, source, and type.
        """
        if not exact_match:
            name = name + "%"  # Makes the query a starts_with query
        for import_name, module, source, name_type in self.database._execute(
            models.Name.search_by_name_like.select("name", "module", "source", "type"),
            (name,),
        ):
            yield (
                SearchResult(
                    f"from {module} import {import_name}",
                    import_name,
                    source,
                    name_type,
                )
            )

    def _search_module(
        self, name: str, exact_match: bool = False
    ) -> Generator[SearchResult, None, None]:
        """
        Search both modules for available imports.

        Returns the import statement, import name, source, and type.
        """
        if not exact_match:
            name = name + "%"  # Makes the query a starts_with query
        for module, source in self.database._execute(
            models.Name.search_submodule_like.select("module", "source"), (name,)
        ):
            parts = module.split(".")
            import_name = parts[-1]
            remaining = parts[0]
            for part in parts[1:-1]:
                remaining += "."
                remaining += part
            yield (
                SearchResult(
                    f"from {remaining} import {import_name}",
                    import_name,
                    source,
                    NameType.Module.value,
                )
            )
        for module, source in self.database._execute(
            models.Name.search_module_like.select("module", "source"), (name,)
        ):
            if "." in module:
                continue
            yield SearchResult(
                f"import {module}", module, source, NameType.Module.value
            )

    def get_modules(self, name) -> List[str]:
        """Get the list of modules that have global `name`."""
        results = self.database._execute(
            models.Name.search_by_name.select("module", "source"), (name,)
        ).fetchall()
        return sort_and_deduplicate(results)

    def get_all_names(self) -> List[str]:
        """Get the list of all cached global names."""
        return self.database._execute(models.Name.objects.select("name")).fetchall()

    def generate_cache(
        self,
        resources: Optional[List[Resource]] = None,
        underlined: bool = False,
        task_handle: taskhandle.BaseTaskHandle = taskhandle.DEFAULT_TASK_HANDLE,
    ):
        """Generate global name cache for project files.

        If `resources` is a list of `rope.base.resource.File`, only
        those files are searched; otherwise all python modules in the
        project are cached.
        """
        if resources is None:
            resources = self.project.get_python_files()
        self.database.delete_package(self.project_package.name)

        def get_modules():
            for file in resources:
                module = self._resource_to_module(file, underlined)
                yield (self.project_package, module)

        self._index(get_modules(), task_handle, False)

    def _index(
        self,
        modules: Iterable[Tuple[Package, ModuleInfo]],
        task_handle: taskhandle.BaseTaskHandle = taskhandle.DEFAULT_TASK_HANDLE,
        single_thread: bool = False,
        commit: bool = True,
    ):
        job_set = task_handle.create_jobset("Generating autoimport cache", 0)
        if single_thread:
            for package, module in modules:
                job_set.started_job(module.modname)
                for name in get_names(module, package):
                    self.database.add_name(name)
                    job_set.finished_job()
        else:
            for future_name in as_completed(get_future_names(modules, job_set)):
                self.database.add_names(future_name.result())
                job_set.finished_job()
        if commit:
            self.database.commit()

    def generate_modules_cache(
        self,
        modules: Optional[List[str]] = None,
        task_handle: taskhandle.BaseTaskHandle = taskhandle.DEFAULT_TASK_HANDLE,
        single_thread: bool = False,
        underlined: Optional[bool] = None,
    ):
        """
        Generate global name cache for external modules listed in `modules`.

        If no modules are provided, it will generate a cache for every module available.
        This method searches in your sys.path and configured python folders.
        Do not use this for generating your own project's internal names,
        use generate_resource_cache for that instead.
        """
        underlined = self.underlined if underlined is None else underlined

        packages: List[Package] = (
            self._get_available_packages()
            if modules is None
            else list(self._get_packages_from_modules(modules))
        )

        existing = self._get_packages_from_cache()
        packages = list(filter_packages(packages, underlined, existing))
        if not packages:
            return
        self.database.add_packages(packages)

        def get_modules():
            for package in packages:
                for module in get_files(package, underlined):
                    yield package, module

        self._index(get_modules(), task_handle, single_thread)

    def _get_packages_from_modules(self, modules: List[str]) -> Iterator[Package]:
        for modname in modules:
            package = self._find_package_path(modname)
            if package is None:
                continue
            yield package

    def update_module(self, module: str):
        """Update a module in the cache, or add it if it doesn't exist."""
        self._del_if_exist(module)
        self.generate_modules_cache([module])

    def close(self):
        """Close the autoimport database."""
        self.database.close()

    def get_name_locations(self, name):
        """Return a list of ``(resource, lineno)`` tuples."""
        result = []
        modules = self.database._execute(
            models.Name.search_by_name_like.select("module"), (name,)
        ).fetchall()
        for module in modules:
            with contextlib.suppress(exceptions.ModuleNotFoundError):
                module_name = module[0]
                if module_name.startswith(f"{self.project_package.name}."):
                    module_name = ".".join(module_name.split("."))
                pymodule = self.project.get_module(module_name)
                if name in pymodule:
                    pyname = pymodule[name]
                    module, lineno = pyname.get_definition_location()
                    if module is not None:
                        resource = module.get_module().get_resource()
                        if resource is not None and lineno is not None:
                            result.append((resource, lineno))
        return result

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
        module = self._resource_to_module(resource, underlined)
        self._del_if_exist(module_name=module.modname, commit=False)
        self._index([(self.project_package, module)], single_thread=True, commit=commit)

    def _changed(self, resource):
        if not resource.is_folder():
            self.update_resource(resource)

    def _moved(self, resource: Resource, newresource: Resource):
        if not resource.is_folder():
            modname = self._resource_to_module(resource).modname
            self._del_if_exist(modname)
            self.update_resource(newresource)

    def _del_if_exist(self, module_name, commit: bool = True):
        self.database._execute(models.Name.delete_by_module_name, (module_name,))
        if commit:
            self.database.commit()

    def _get_python_folders(self) -> List[Path]:
        def filter_folders(folder: Path) -> bool:
            return folder.is_dir() and folder.as_posix() != "/usr/bin"

        folders = self.project.get_python_path_folders()
        folder_paths = filter(filter_folders, map(Path, folders))
        return list(OrderedDict.fromkeys(folder_paths))

    def _safe_iterdir(self, folder: Path):
        dirs = folder.iterdir()
        while True:
            try:
                yield next(dirs)
            except PermissionError:
                pass
            except StopIteration:
                break

    def _get_available_packages(self) -> List[Package]:
        packages: List[Package] = [
            Package(module, Source.BUILTIN, None, PackageType.BUILTIN)
            for module in sys.builtin_module_names
        ]
        for folder in self._get_python_folders():
            for package in self._safe_iterdir(folder):
                package_tuple = get_package_tuple(package, self.project)
                if package_tuple is None:
                    continue
                packages.append(package_tuple)
        return packages

    def _get_packages_from_cache(self) -> List[str]:
        existing: List[str] = list(
            chain(
                *self.database._execute(models.Package.objects.select_star()).fetchall()
            )
        )
        existing.append(self.project_package.name)
        return existing

    def _removed(self, resource):
        if not resource.is_folder():
            modname = self._resource_to_module(resource).modname
            self._del_if_exist(modname)

    def _find_package_path(self, target_name: str) -> Optional[Package]:
        if target_name in sys.builtin_module_names:
            return Package(target_name, Source.BUILTIN, None, PackageType.BUILTIN)
        for folder in self._get_python_folders():
            for package in self._safe_iterdir(folder):
                package_tuple = get_package_tuple(package, self.project)
                if package_tuple is None:
                    continue
                name, source, package_path, package_type = package_tuple
                if name == target_name:
                    return package_tuple

        return None

    def _resource_to_module(
        self, resource: Resource, underlined: bool = False
    ) -> ModuleFile:
        assert self.project_package.path
        underlined = underlined if underlined else self.underlined
        resource_path: Path = resource.pathlib
        # The project doesn't need its name added to the path,
        # since the standard python file layout accounts for that
        # so we set add_package_name to False
        resource_modname: str = get_modname_from_path(
            resource_path, self.project_package.path, add_package_name=False
        )
        return ModuleFile(
            resource_path,
            resource_modname,
            underlined,
            resource_path.name == "__init__.py",
        )

    def _dump_all(self) -> Tuple[List[Name], List[Package]]:
        """Dump the entire database."""
        return self.database._dump_all()

    def clear_cache(self):
        """Clear all entries in global-name cache.

        It might be a good idea to use this function before
        regenerating global names.

        """
        self.database.clear_cache()
