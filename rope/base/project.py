from __future__ import annotations

import contextlib
import json
import os
import sys
import sysconfig
import types
import warnings
from abc import ABC, abstractmethod
from contextlib import ExitStack
from typing import TYPE_CHECKING, Optional

import rope.base.fscommands  # Use full qualification for clarity.
import rope.base.resourceobserver as resourceobserver
from rope.base import exceptions, history, pycore, taskhandle, utils
from rope.base.exceptions import ModuleNotFoundError

# At present rope.base.prefs starts with `# type:ignore`.
# As a result, mypy knows nothing about Prefs and get_config.
from rope.base.prefs import Prefs, get_config  # type: ignore
from rope.base.resources import File, Folder, Resource, _ResourceMatcher

try:
    import cPickle as pickle  # type: ignore
except ImportError:
    import pickle  # type: ignore


if TYPE_CHECKING:
    from rope.base import pyobjects, pyobjectsdef


class _Project(ABC):
    prefs: Prefs
    data_files: _DataFiles
    _custom_source_folders: list[Folder]

    def __init__(self, fscommands, external_project=None):
        self.observers = []
        self.fscommands = fscommands
        self.external_project = external_project
        self.prefs = Prefs()
        self.data_files = _DataFiles(self)
        self._custom_source_folders = []

    def get_resource(self, resource_name: str) -> Resource:
        """Get a resource in a project.

        `resource_name` is the path of a resource in a project.  It is
        the path of a resource relative to project root.  Project root
        folder address is an empty string.  If the resource does not
        exist a `exceptions.ResourceNotFound` exception would be
        raised.  Use `get_file()` and `get_folder()` when you need to
        get nonexistent `Resource`.

        """
        path = self._get_resource_path(resource_name)
        if not self.fscommands.exists(path):
            raise exceptions.ResourceNotFoundError(
                "Resource <%s> does not exist" % resource_name
            )
        elif self.fscommands.isfile(path):
            return File(self, resource_name)
        elif self.fscommands.isdir(path):
            return Folder(self, resource_name)
        else:
            raise exceptions.ResourceNotFoundError("Unknown resource " + resource_name)

    def get_module(
        self, name: str, folder: Optional[Folder] = None
    ) -> pyobjects.AbstractModule:
        """Returns a `PyObject` if the module was found."""
        # check if this is a builtin module
        pymod = self.pycore.builtin_module(name)
        if pymod is not None:
            return pymod
        module = self.find_module(name, folder)
        if module is None:
            observed = self._stdlib_module_alias(name, folder)
            if observed is not None:
                return observed
            raise ModuleNotFoundError("Module %s not found" % name)
        return self.pycore.resource_to_pyobject(module)

    def _stdlib_module_alias(self, name, folder):
        """Read an existing stdlib module election without importing target code."""
        observed = sys.modules.get(name)
        if not isinstance(observed, types.ModuleType) or observed.__spec__ is None:
            return None
        origin = observed.__spec__.name
        if origin == name or sys.modules.get(origin) is not observed:
            return None
        if not hasattr(sys, "stdlib_module_names") or (
            origin.partition(".")[0] not in sys.stdlib_module_names
            or name.partition(".")[0] not in sys.stdlib_module_names
        ):
            return None
        parent_name, separator, _ = name.rpartition(".")
        parent = sys.modules.get(parent_name)
        filename = getattr(observed, "__file__", None)
        parent_filename = getattr(parent, "__file__", None)
        if (
            not separator
            or not isinstance(filename, str)
            or not isinstance(parent_filename, str)
        ):
            return None
        stdlib = os.path.realpath(sysconfig.get_path("stdlib"))
        filename = os.path.realpath(filename)
        try:
            contained = os.path.normcase(
                os.path.commonpath((stdlib, filename))
            ) == os.path.normcase(stdlib)
        except ValueError:
            return None
        if not contained:
            return None
        declared_parent = self.find_module(parent_name, folder)
        declared_origin = self.find_module(origin, folder)
        if (
            declared_parent is None
            or declared_origin is None
            or declared_origin.is_folder()
        ):
            return None
        if declared_parent.is_folder():
            if not declared_parent.has_child("__init__.py"):
                return None
            declared_parent = declared_parent.get_child("__init__.py")
        if not utils.same_file_path(
            declared_parent.real_path, parent_filename
        ) or not utils.same_file_path(declared_origin.real_path, filename):
            return None
        return self.pycore.resource_to_pyobject(declared_origin)

    def get_python_path_folders(self) -> list[Resource]:
        result = []
        external = (
            get_no_project() if self.external_project is None else self.external_project
        )
        for src in self.prefs.get("python_path", []) + sys.path:
            with contextlib.suppress(exceptions.ResourceNotFoundError):
                result.append(external.get_resource(src))

        return result

    # INFO: It was decided not to cache source folders, since:
    #  - Does not take much time when the root folder contains
    #    packages, that is most of the time
    #  - We need a separate resource observer; `self.observer`
    #    does not get notified about module and folder creations
    def get_source_folders(self) -> list[Folder]:
        """Returns project source folders"""
        if self.root is None:
            return []
        result = list(self._custom_source_folders)
        result.extend(self.pycore._find_source_folders(self.root))
        return result

    def validate(self, folder):
        """Validate files and folders contained in this folder

        It validates all of the files and folders contained in this
        folder if some observers are interested in them.

        """
        for observer in list(self.observers):
            observer.validate(folder)

    def add_observer(self, observer):
        """Register a `ResourceObserver`

        See `FilteredResourceObserver`.
        """
        self.observers.append(observer)

    def remove_observer(self, observer):
        """Remove a registered `ResourceObserver`"""
        if observer in self.observers:
            self.observers.remove(observer)

    def do(self, changes, task_handle=taskhandle.DEFAULT_TASK_HANDLE):
        """Apply the changes in a `ChangeSet`

        Most of the time you call this function for committing the
        changes for a refactoring.
        """
        self.history.do(changes, task_handle=task_handle)

    def get_pymodule(self, resource, force_errors=False):
        return self.pycore.resource_to_pyobject(resource, force_errors)

    def get_pycore(self):
        return self.pycore

    def get_file(self, path: str) -> File:
        """Get the file with `path` (it may not exist)"""
        return File(self, path)

    def get_folder(self, path: str) -> Folder:
        """Get the folder with `path` (it may not exist)"""
        return Folder(self, path)

    def get_prefs(self):
        return self.prefs

    def get_relative_module(
        self,
        name: str,
        folder: Folder,
        level: int,
    ) -> pyobjectsdef.PyPackage | pyobjectsdef.PyModule:
        module = self.find_relative_module(name, folder, level)
        if module is None:
            raise ModuleNotFoundError("Module %s not found" % name)
        return self.pycore.resource_to_pyobject(module)

    def find_module(
        self, modname: str, folder: Optional[Folder] = None
    ) -> Optional[Resource]:
        """Returns a resource corresponding to the given module

        returns None if it can not be found
        """

        def folders():
            yield from self.get_source_folders()
            yield from self.get_python_path_folders()
            if folder is not None:
                yield folder

        return _find_module_in_folders(folders(), modname)

    def find_relative_module(
        self,
        modname: str,
        folder: Folder,
        level: int,
    ) -> Optional[Resource]:
        for i in range(level - 1):
            folder = folder.parent
        if modname == "":
            return folder
        else:
            return _find_module_in_folders([folder], modname)

    def is_ignored(self, resource):
        return False

    @property
    @utils.saveit
    def history(self):
        return history.History(self)

    @property
    @utils.saveit
    def pycore(self) -> pycore.PyCore:
        return pycore.PyCore(self)

    @abstractmethod
    def close(self):
        """Closes project open resources"""

    @property
    @abstractmethod
    def ropefolder(self) -> Optional[Folder]:
        # FIXME: use class-level ReadOnly attribute when they become available (PEP-767)
        ...

    @abstractmethod
    def _get_resource_path(self, name: str) -> str: ...

    @abstractmethod
    def get_files(self) -> list[Resource]:
        return []

    @abstractmethod
    def get_python_files(self) -> list[Resource]:
        return []


class Project(_Project):
    """A Project containing files and folders"""

    file_list: _FileListCacher

    def __init__(
        self,
        projectroot,
        fscommands=None,
        ropefolder=".ropeproject",
        external_project=None,
        *,
        config_files=True,
        **prefs,
    ):
        """A rope project

        :parameters:
            - `projectroot`: The address of the root folder of the project
            - `fscommands`: Implements the file system operations used
              by rope; have a look at `rope.base.fscommands`
            - `ropefolder`: The name of the folder in which rope stores
              project configurations and data.  Pass `None` for not using
              such a folder at all.
            - `external_project`: Resource owner for Python-path modules.
              Pass a separate ``NoProject`` with the same filesystem commands
              to keep external and local reads in one captured filesystem.
            - `config_files`: Pass ``False`` to take preferences only from
              `prefs` over the defaults; no ``pyproject.toml``, ropefolder
              ``config.py`` or global configuration is read.
            - `prefs`: Specify project preferences.  These values
              overwrite config file preferences.

        """
        if projectroot != "/":
            projectroot = (
                _realpath(projectroot)
                if fscommands is None
                else fscommands.realpath(projectroot)
            ).rstrip("/\\")
        assert isinstance(projectroot, str)
        self._address = projectroot
        self._ropefolder_name = ropefolder
        self._config_files = config_files
        filesystem = (
            rope.base.fscommands.FileSystemCommands()
            if fscommands is None
            else fscommands
        )
        if not filesystem.exists(self._address):
            filesystem.create_folder(self._address)
        elif not filesystem.isdir(self._address):
            raise exceptions.RopeError("Project root exists and" " is not a directory")
        if fscommands is None:
            fscommands = rope.base.fscommands.create_fscommands(self._address)
        super().__init__(fscommands, external_project=external_project)
        self.ignored = _ResourceMatcher()
        self.file_list = _FileListCacher(self)

        extra_ignores = [
            p.pathlib.relative_to(self.root.pathlib)
            for p in self.get_python_path_folders()
            if p.pathlib.is_relative_to(self.root.pathlib)
            and "site-packages" in p.pathlib.parts
        ]
        if extra_ignores:
            # I'm using this approach, because self.prefs.add after _init_prefs
            # does not work for some reason.
            prefs.setdefault("ignored_resources", []).extend(
                str(p) for p in extra_ignores
            )

        self._init_prefs(prefs)
        if ropefolder is not None:
            self.prefs.add("ignored_resources", ropefolder)

        for path in self.prefs.get("source_folders", []):
            folder = self.get_resource(path)
            self._custom_source_folders.append(folder)

    def __repr__(self):
        return '<{}.{} "{}">'.format(
            self.__class__.__module__,
            self.__class__.__name__,
            self.address,
        )

    def get_files(self) -> list[Resource]:
        return list(self.file_list.get_files())

    def get_python_files(self) -> list[Resource]:
        """Returns all python files available in the project"""
        return [
            resource
            for resource in self.get_files()
            if self.pycore.is_python_file(resource)
        ]

    def _get_resource_path(self, name: str) -> str:
        return os.path.normpath(os.path.join(self._address, *name.split("/")))

    def _init_ropefolder(self):
        if self.ropefolder is not None and not self.ropefolder.exists():
            self._create_recursively(self.ropefolder)

    def _create_recursively(self, folder):
        if folder.parent != self.root and not folder.parent.exists():
            self._create_recursively(folder.parent)
        folder.create()

    def _init_prefs(self, prefs):
        config = (
            get_config(self.root, self.ropefolder).parse()
            if self._config_files
            else Prefs()
        )
        self.prefs = config
        self.prefs.add_callback("ignored_resources", self.ignored.set_patterns)
        self.ignored.set_patterns(self.prefs.ignored_resources)
        for key, value in prefs.items():
            self.prefs.set(key, value)
        self._init_other_parts()
        self._init_ropefolder()
        if config.project_opened:
            config.project_opened(self)

    def _init_other_parts(self):
        # Forcing the creation of `self.pycore` to register observers
        self.pycore  # pylint: disable=pointless-statement

    def is_ignored(self, resource: Resource):
        return self.ignored.does_match(resource)

    def sync(self):
        """Closes project open resources"""
        self.close()

    def close(self):
        """Closes project open resources"""
        self.data_files.write()

    def set(self, key, value):
        """Set the `key` preference to `value`"""
        self.prefs.set(key, value)

    @property
    def ropefolder(self) -> Optional[Folder]:
        if self._ropefolder_name is not None:
            return self.get_folder(self._ropefolder_name)
        return None

    def validate(self, folder=None):
        if folder is None:
            folder = self.root
        super().validate(folder)

    root = property(lambda self: self.get_resource(""))
    address = property(lambda self: self._address)


class NoProject(_Project):
    """A null object for holding out-of-project files.

    This class is a singleton, use `get_no_project` global function.
    """

    _no_project: Optional[NoProject] = None
    ropefolder: Optional[Folder] = None

    def __init__(self, fscommands=None):
        if fscommands is None:
            fscommands = rope.base.fscommands.FileSystemCommands()
        super().__init__(fscommands)

    def _get_resource_path(self, name: str) -> str:
        real_name = name.replace("/", os.path.sep)
        return self.fscommands.realpath(real_name)

    def get_resource(self, name: str) -> Resource:
        universal_name = self.fscommands.realpath(name).replace(os.path.sep, "/")
        return super().get_resource(universal_name)

    def get_files(self) -> list[Resource]:
        return []

    def get_python_files(self) -> list[Resource]:
        return []

    def close(self):
        warnings.warn("Cannot close a NoProject", DeprecationWarning, stacklevel=2)


def get_no_project() -> NoProject:
    if NoProject._no_project is None:
        NoProject._no_project = NoProject()
    return NoProject._no_project


class _FileListCacher:
    files: set[Resource]

    def __init__(self, project):
        self.project = project
        self.files = None
        rawobserver = resourceobserver.ResourceObserver(
            self._changed, self._invalid, self._invalid, self._invalid, self._invalid
        )
        self.project.add_observer(rawobserver)

    def get_files(self) -> set[Resource]:
        if self.files is None:
            self.files = set()
            self._add_files(self.project.root)
        return self.files

    def _add_files(self, folder):
        for child in folder.get_children():
            if child.is_folder():
                self._add_files(child)
            elif not self.project.is_ignored(child):
                self.files.add(child)

    def _changed(self, resource):
        if resource.is_folder():
            self.files = None

    def _invalid(self, resource, new_resource=None):
        self.files = None


class _DataFiles:
    def __init__(self, project):
        self.project = project
        self.hooks = []

    def read_data(self, name):
        if self.project.ropefolder is None:
            return None
        file = self._get_file(name)
        if file.exists():
            with open(file.real_path, "rb") as input_file:
                result = []
                try:
                    while True:
                        result.append(pickle.load(input_file))
                except EOFError:
                    pass
                if len(result) == 1:
                    return result[0]
                if len(result) > 1:
                    return result

    def write_data(self, name, data):
        if self.project.ropefolder is not None:
            file = self._get_file(name)
            with ExitStack() as cm:
                output_file = cm.enter_context(open(file.real_path, "wb"))
                output_file2 = cm.enter_context(open(file.real_path + ".json", "w"))
                pickle.dump(data, output_file, 2)
                json.dump(data, output_file2, default=lambda o: o.__getstate__())

    def add_write_hook(self, hook):
        self.hooks.append(hook)

    def write(self):
        for hook in self.hooks:
            hook()

    def _get_file(self, name):
        path = self.project.ropefolder.path + "/" + name
        return self.project.get_file(path)


def _realpath(path: str) -> str:
    """Return the real path of `path`

    Is equivalent to ``realpath(abspath(expanduser(path)))``.

    Of the particular notice is the hack dealing with the unfortunate
    situation of running native-Windows python (os.name == 'nt') inside
    of Cygwin (abspath starts with '/'), which apparently normal
    os.path.realpath completely messes up.

    """
    # there is a bug in cygwin for os.path.abspath() for abs paths
    if sys.platform == "cygwin":
        if path[1:3] == ":\\":
            return path
        elif path[1:3] == ":/":
            path = "/cygdrive/" + path[0] + path[2:]
        return os.path.abspath(os.path.expanduser(path))
    return os.path.realpath(os.path.abspath(os.path.expanduser(path)))


def _find_module_in_folders(folders, modname):
    for name in modname.split("."):
        namespaces = []
        for folder in folders:
            if not folder.is_folder():
                continue
            package = folder.get_child(name) if folder.has_child(name) else None
            if package is not None and package.is_folder():
                if (
                    package.has_child("__init__.py")
                    and not package.get_child("__init__.py").is_folder()
                ):
                    module = package
                    folders = [package]
                    break
                namespaces.append(package)
            if folder.has_child(name + ".py"):
                source = folder.get_child(name + ".py")
                if not source.is_folder():
                    module = source
                    folders = []
                    break
        else:
            if not namespaces:
                return None
            module = namespaces[0]
            folders = namespaces
    return module
