import os
import re
import shutil
import cPickle as pickle

import rope.base.change
import rope.base.fscommands
from rope.base import exceptions, taskhandle, prefs, history, pycore
from rope.base.resourceobserver import *
from rope.base.resources import File, Folder


class _Project(object):

    def __init__(self, fscommands):
        self.observers = []
        self._history = None
        self.operations = rope.base.change._ResourceOperations(self, fscommands)
        self.prefs = prefs.Prefs()
        self._pycore = None
        self.data_files = _DataFiles(self)

    def get_resource(self, resource_name):
        """Get a resource in a project.

        `resource_name` is the path of a resource in a project.  It is
        the path of a resource relative to project root.  Project root
        folder address is an empty string.  If the resource does not
        exist a `exceptions.ResourceNotFound` exception would be
        raised.  Use `get_file()` and `get_folder()` when you need to
        get non- existent `Resource`\s.

        """
        path = self._get_resource_path(resource_name)
        if not os.path.exists(path):
            raise exceptions.ResourceNotFoundError(
                'Resource <%s> does not exist' % resource_name)
        elif os.path.isfile(path):
            return File(self, resource_name)
        elif os.path.isdir(path):
            return Folder(self, resource_name)
        else:
            raise exceptions.ResourceNotFoundError('Unknown resource '
                                                   + resource_name)

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

    def do(self, changes, task_handle=taskhandle.NullTaskHandle()):
        """Apply the changes in a `ChangeSet`

        Most of the time you call this function for committing the
        changes for a refactoring.
        """
        self.history.do(changes, task_handle=task_handle)

    def get_pycore(self):
        if self._pycore is None:
            self._pycore = pycore.PyCore(self)
        return self._pycore

    def get_file(self, path):
        """Get the file with `path` (it may not exist)"""
        return File(self, path)

    def get_folder(self, path):
        """Get the folder with `path` (it may not exist)"""
        return Folder(self, path)

    def is_ignored(self, resource):
        return False

    def close(self):
        """Closes project open resources"""

    def sync(self):
        """Closes project open resources"""
        self.close()

    def get_prefs(self):
        return self.prefs

    def _get_resource_path(self, name):
        pass

    def _get_history(self):
        if self._history is None:
            self._history = history.History(self)
        return self._history

    history = property(_get_history)
    pycore = property(get_pycore)
    ropefolder = None


class Project(_Project):
    """A Project containing files and folders"""

    def __init__(self, projectroot, fscommands=None,
                 ropefolder='.ropeproject', **prefs):
        """A rope project

        :parameters:
            - `projectroot`: The address of the root folder of the project
            - `fscommands`: Implements the file system operations rope uses
              have a look at `rope.base.fscommands`
            - `ropefolder`: The name of the folder in which rope stores
              project configurations and data.  Pass `None` for not using
              such a folder at all.
            - `prefs`: Specify project preferences.  These values
              overwrite config file preferences.

        """
        self._address = _realpath(projectroot).rstrip('/\\')
        self._ropefolder_name = ropefolder
        if not os.path.exists(self._address):
            os.mkdir(self._address)
        elif not os.path.isdir(self._address):
            raise exceptions.RopeError('Project root exists and'
                                       ' is not a directory')
        if fscommands is None:
            fscommands = rope.base.fscommands.create_fscommands(self._address)
        super(Project, self).__init__(fscommands)
        self.ignored = _IgnoredResources()
        self.file_list = _FileListCacher(self)
        self.prefs.add_callback('ignored_resources', self.ignored.set_ignored)
        if ropefolder is not None:
            self.prefs['ignored_resources'] = [ropefolder]
        self._init_prefs(prefs)

    def get_files(self):
        return self.file_list.get_files()

    def _get_resource_path(self, name):
        return os.path.join(self._address, *name.split('/'))

    def _init_ropefolder(self):
        if self.ropefolder is not None:
            if not self.ropefolder.exists():
                self.ropefolder.create()
            if not self.ropefolder.has_child('config.py'):
                config = self.ropefolder.create_file('config.py')
                config.write(self._default_config())

    def _init_prefs(self, prefs):
        run_globals = {}
        if self.ropefolder is not None:
            config = self.get_file(self.ropefolder.path + '/config.py')
            run_globals.update({'__name__': '__main__',
                                '__builtins__': __builtins__,
                                '__file__': config.real_path})
            if config.exists():
                config = self.ropefolder.get_child('config.py')
                execfile(config.real_path, run_globals)
            else:
                exec(self._default_config(), run_globals)
            if 'set_prefs' in run_globals:
                run_globals['set_prefs'](self.prefs)
        for key, value in prefs.items():
            self.prefs[key] = value
        self._init_other_parts()
        self._init_ropefolder()
        if 'project_opened' in run_globals:
            run_globals['project_opened'](self)

    def _default_config(self):
        import rope.base.default_config
        import inspect
        return inspect.getsource(rope.base.default_config)

    def _init_other_parts(self):
        # Forcing the creation of `self.pycore` to register observers
        self.pycore

    def is_ignored(self, resource):
        return self.ignored.is_ignored(resource)

    def close(self):
        self.data_files.write()
        super(Project, self).close()

    def set(self, key, value):
        """Set the `key` preference to `value`"""
        self.prefs.set(key, value)

    @property
    def ropefolder(self):
        if self._ropefolder_name is not None:
            return self.get_folder(self._ropefolder_name)

    def validate(self, folder=None):
        if folder is None:
            folder = self.root
        super(Project, self).validate(folder)

    root = property(lambda self: self.get_resource(''))
    address = property(lambda self: self._address)


class NoProject(_Project):
    """A null object for holding out of project files.

    This class is singleton use `get_no_project` global function
    """

    def __init__(self):
        fscommands = rope.base.fscommands.FileSystemCommands()
        self.root = None
        super(NoProject, self).__init__(fscommands)

    def _get_resource_path(self, name):
        real_name = name.replace('/', os.path.sep)
        return _realpath(real_name)

    def get_resource(self, name):
        universal_name = _realpath(name).replace(os.path.sep, '/')
        return super(NoProject, self).get_resource(universal_name)

    def get_files(self):
        return []

    _no_project = None


def get_no_project():
    if NoProject._no_project is None:
        NoProject._no_project = NoProject()
    return NoProject._no_project


class _IgnoredResources(object):

    def __init__(self):
        self.patterns = []
        self._ignored_patterns = []

    def set_ignored(self, patterns):
        """Specify which resources to ignore

        `patterns` is a `list` of `str`\s that can contain ``*`` and
        ``?`` signs for matching resource names.

        """
        self._ignored_patterns = None
        self.patterns = patterns

    def _add_ignored_pattern(self, pattern):
        re_pattern = pattern.replace('.', '\\.').\
                     replace('*', '[^/]*').replace('?', '[^/]').\
                     replace('//', '/(.*/)?')
        re_pattern = '(.*/)?' + re_pattern + '(/.*)?'
        self.ignored_patterns.append(re.compile(re_pattern))

    def is_ignored(self, resource):
        for pattern in self.ignored_patterns:
            if pattern.match(resource.path):
                return True
        path = os.path.join(resource.project.address,
                            *resource.path.split('/'))
        if os.path.islink(path):
            return True
        return False

    def _get_compiled_patterns(self):
        if self._ignored_patterns is None:
            self._ignored_patterns = []
            for pattern in self.patterns:
                self._add_ignored_pattern(pattern)
        return self._ignored_patterns

    ignored_patterns = property(_get_compiled_patterns)


class _FileListCacher(object):

    def __init__(self, project):
        self.project = project
        self._list = None
        self.observer = None

    def get_files(self):
        if self._list is None:
            if self.observer is None:
                self._init_observer()
            self._list = self._get_files_recursively(self.project.root)
            folders = [resource for resource in self._list
                       if resource.is_folder()]
            for resource in folders:
                self.observer.add_resource(resource)
        return self._list

    def _get_files_recursively(self, folder):
        result = set()
        for file in folder.get_files():
            result.add(file)
        for child in folder.get_folders():
            result.update(self._get_files_recursively(child))
        return result

    def _init_observer(self):
        if self.observer is None:
            self.rawobserver = ResourceObserver(
                self._changed, self._moved, self._created,
                self._removed, self._validate)
            self.observer = FilteredResourceObserver(self.rawobserver)
            self.project.add_observer(self.rawobserver)
            self.project.add_observer(self.observer)

    def _changed(self, resource):
        if resource.is_folder():
            self._list = None

    def _moved(self, resource, new_resource):
        if resource.is_folder():
            self._list = None
        elif self._list is not None:
            self._removed(resource)
            self._created(new_resource)

    def _created(self, resource):
        if not resource.is_folder() and self._list is not None:
            if not self.project.is_ignored(resource):
                self._list.add(resource)

    def _removed(self, resource):
        if resource.is_folder():
            self._list = None
        else:
            if self._list is not None and resource in self._list:
                self._list.remove(resource)

    def _validate(self, resource):
        pass


class _DataFiles(object):

    def __init__(self, project):
        self.project = project
        self.hooks = []

    def read_data(self, name, compress=False, import_=False):
        if self.project.ropefolder is None:
            return None
        opener = self._get_opener(compress)
        compress = opener != open
        file = self._get_file(name, compress)
        if not compress and import_:
            self._import_old_files(name)
        if file.exists():
            input = opener(file.real_path, 'rb')
            try:
                result = []
                try:
                    while True:
                        result.append(pickle.load(input))
                except EOFError:
                    pass
                if len(result) == 1:
                    return result[0]
                if len(result) > 1:
                    return result
            finally:
                input.close()

    def write_data(self, name, data, compress=False):
        if self.project.ropefolder:
            file = self._get_file(name, compress)
            opener = self._get_opener(compress)
            compress = opener != open
            output = opener(file.real_path, 'wb')
            try:
                pickle.dump(data, output, 2)
            finally:
                output.close()

    def add_write_hook(self, hook):
        self.hooks.append(hook)

    def write(self):
        for hook in self.hooks:
            hook()

    def _import_old_files(self, name):
        old = self._get_file(name + '.pickle', False)
        new = self._get_file(name, False)
        if old.exists() and not new.exists():
            shutil.move(old.real_path, new.real_path)

    def _get_opener(self, compress):
        if compress:
            try:
                import gzip
                return gzip.open
            except ImportError:
                pass
        return open

    def _get_file(self, name, compress):
        path = self.project.ropefolder.path + '/' + name
        if compress:
            name += '.gz'
        return self.project.get_file(path)


def _realpath(path):
    """Return the real path of `path`

    Is equivalent to ``realpath(abspath(expanduser(path)))``.

    """
    return os.path.realpath(os.path.abspath(os.path.expanduser(path)))
