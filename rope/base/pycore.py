import bisect
import difflib
import sys

import rope.base.oi.objectinfer
import rope.base.oi.objectinfo
import rope.base.project
from rope.base import ast, exceptions, taskhandle, codeanalyze
from rope.base.exceptions import ModuleNotFoundError
from rope.base.oi import dynamicoi
from rope.base.pyobjects import PyModule, PyPackage, PyClass


class PyCore(object):

    def __init__(self, project):
        self.project = project
        self._init_resource_observer()
        self.cache_observers = []
        self.classes_cache = _ClassesCache(self)
        self.module_cache = _ModuleCache(self)
        self.object_info = rope.base.oi.objectinfo.ObjectInfoManager(project)
        self.object_infer = rope.base.oi.objectinfer.ObjectInfer(self)
        self._init_automatic_soi()
        self._init_source_folders()

    def _init_resource_observer(self):
        callback = self._invalidate_resource_cache
        observer = rope.base.project.ResourceObserver(
            changed=callback, moved=callback, removed=callback)
        self.observer = rope.base.project.FilteredResourceObserver(observer)
        self.project.add_observer(self.observer)

    def _init_source_folders(self):
        self._custom_source_folders = []
        for path in self.project.prefs.get('source_folders', []):
            self._custom_source_folders.append(path)
        for path in self.project.prefs.get('python_path', []):
            sys.path.append(path)

    def _init_automatic_soi(self):
        if not self.project.get_prefs().get('automatic_soi', False):
            return
        callback = self._file_changed_for_soi
        observer = rope.base.project.ResourceObserver(
            changed=callback, moved=callback, removed=callback)
        self.project.add_observer(observer)

    def _file_changed_for_soi(self, resource, new_resource=None):
        old_contents = self.project.history.\
                       contents_before_current_change(resource)
        if old_contents is not None:
            perform_soi_on_changed_scopes(self.project, resource, old_contents)

    def is_python_file(self, resource):
        return not resource.is_folder() and resource.name.endswith('.py')

    def get_module(self, name, current_folder=None):
        """Returns a `PyObject` if the module was found."""
        module = self.find_module(name, current_folder)
        if module is None:
            raise ModuleNotFoundError('Module %s not found' % name)
        return self.resource_to_pyobject(module)

    def get_relative_module(self, name, current_folder, level):
        module = self.find_relative_module(name, current_folder, level)
        if module is None:
            raise ModuleNotFoundError('Module %s not found' % name)
        return self.resource_to_pyobject(module)

    def get_string_module(self, module_content, resource=None):
        """Returns a `PyObject` object for the given module_content"""
        return PyModule(self, module_content, resource)

    def get_string_scope(self, module_content, resource=None):
        """Returns a `Scope` object for the given module_content"""
        return self.get_string_module(module_content, resource).get_scope()

    def _invalidate_resource_cache(self, resource, new_resource=None):
        for observer in self.cache_observers:
            observer(resource)

    def create_module(self, src_folder, new_module):
        """Creates a module and returns a `rope.project.File`"""
        packages = new_module.split('.')
        parent = src_folder
        for package in packages[:-1]:
            parent = parent.get_child(package)
        return parent.create_file(packages[-1] + '.py')

    def create_package(self, src_folder, new_package):
        """Creates a package and returns a `rope.project.Folder`"""
        packages = new_package.split('.')
        parent = src_folder
        for package in packages[:-1]:
            parent = parent.get_child(package)
        made_packages = parent.create_folder(packages[-1])
        made_packages.create_file('__init__.py')
        return made_packages

    def _find_module_in_source_folder(self, source_folder, module_name):
        result = []
        module = source_folder
        packages = module_name.split('.')
        for pkg in packages[:-1]:
            if  module.is_folder() and module.has_child(pkg):
                module = module.get_child(pkg)
                result.append(module)
            else:
                return None
        if not module.is_folder():
            return None

        if module.has_child(packages[-1]) and \
           module.get_child(packages[-1]).is_folder():
            result.append(module.get_child(packages[-1]))
            return result
        elif module.has_child(packages[-1] + '.py') and \
             not module.get_child(packages[-1] + '.py').is_folder():
            result.append(module.get_child(packages[-1] + '.py'))
            return result
        return None

    def get_python_path_folders(self):
        result = []
        for src in sys.path:
            try:
                src_folder = rope.base.project.get_no_project().get_resource(src)
                result.append(src_folder)
            except rope.base.exceptions.RopeError:
                pass
        return result

    def find_module(self, module_name, current_folder=None):
        """Returns a resource corresponding to the given module

        returns None if it can not be found
        """
        module_resource_list = self._find_module_resource_list(module_name,
                                                               current_folder)
        if module_resource_list is not None:
            return module_resource_list[-1]

    def find_relative_module(self, module_name, current_folder, level):
        for i in range(level - 1):
            current_folder = current_folder.parent
        if module_name == '':
            return current_folder
        else:
            module = self._find_module_in_source_folder(current_folder, module_name)
            if module is not None:
                return module[-1]

    def _find_module_resource_list(self, module_name, current_folder=None):
        """Returns a list of lists of `Folder`s and `File`s for the given module"""
        for src in self.get_source_folders():
            module = self._find_module_in_source_folder(src, module_name)
            if module is not None:
                return module
        for src in self.get_python_path_folders():
            module = self._find_module_in_source_folder(src, module_name)
            if module is not None:
                return module
        if current_folder is not None:
            module = self._find_module_in_source_folder(current_folder,
                                                        module_name)
            if module is not None:
                return module
        return None

    # INFO: It was decided not to cache source folders, since:
    #  - Does not take much time when the root folder contains
    #    packages, that is most of the time
    #  - We need a separate resource observer; `self.observer`
    #    does not get notified about module and folder creations
    def get_source_folders(self):
        """Returns project source folders"""
        if self.project.root is None:
            return []
        result = list(self._custom_source_folders)
        result.extend(self._find_source_folders(self.project.root))
        return result

    def resource_to_pyobject(self, resource):
        return self.module_cache.get_pymodule(resource)

    def get_python_files(self):
        """Returns all python files available in the project"""
        return [resource for resource in self.project.get_files()
                if self.is_python_file(resource)]

    def _is_package(self, folder):
        if folder.has_child('__init__.py') and \
           not folder.get_child('__init__.py').is_folder():
            return True
        else:
            return False

    def _find_source_folders(self, folder):
        for resource in folder.get_folders():
            if self._is_package(resource):
                return [folder]
        result = []
        for resource in folder.get_files():
            if resource.name.endswith('.py'):
                result.append(folder)
                break
        for resource in folder.get_folders():
            result.extend(self._find_source_folders(resource))
        return result

    def _get_object_infer(self):
        return self.object_infer

    def run_module(self, resource, args=None, stdin=None, stdout=None):
        """Run `resource` module

        Returns a `rope.base.oi.dynamicoi.PythonFileRunner` object for
        controlling the process.

        """
        receiver = self.object_info.doi_data_received
        if not self.project.get_prefs().get('perform_doi', True):
            receiver = None
        runner = dynamicoi.PythonFileRunner(self, resource, args, stdin,
                                            stdout, receiver)
        runner.add_finishing_observer(self.module_cache.forget_all_data)
        runner.run()
        return runner

    def analyze_module(self, resource, should_analyze=lambda py: True,
                       search_subscopes=lambda py: True):
        """Analyze `resource` module for static object inference

        This function forces rope to analyze this module to collect
        information about function calls.  `should_analyze` is a
        function that is called with a `PyDefinedObject` argument.  If
        it returns `True` the element is analyzed.  If it is `None` or
        returns `False` the element is not analyzed.

        `search_subscopes` is like `should_analyze`; The difference is
        that if it returns `False` the sub-scopes are not ignored.
        That is it is assumed that `should_analyze` returns `False for
        all of its subscopes.

        """
        pymodule = self.resource_to_pyobject(resource)
        self.module_cache.forget_all_data()
        self.object_infer.soi.analyze_module(pymodule, should_analyze,
                                             search_subscopes)

    def get_subclasses(self, pyclass, task_handle=taskhandle.NullTaskHandle()):
        classes = self.classes_cache.get_classes(task_handle)
        return [class_ for class_ in classes
                if pyclass in class_.get_superclasses()]

    def get_classes(self, task_handle=taskhandle.NullTaskHandle()):
        return self.classes_cache.get_classes(task_handle)

    def __str__(self):
        return str(self.module_cache) + str(self.object_info)


class _ModuleCache(object):

    def __init__(self, pycore):
        self.pycore = pycore
        self.module_map = {}
        self.pycore.cache_observers.append(self._invalidate_resource)
        self.observer = self.pycore.observer

    def _invalidate_resource(self, resource):
        if resource in self.module_map:
            self.module_map[resource].invalidate()
            self.forget_all_data()
            self.observer.remove_resource(resource)
            del self.module_map[resource]

    def get_pymodule(self, resource):
        if resource in self.module_map:
            return self.module_map[resource]
        if resource.is_folder():
            result = PyPackage(self.pycore, resource)
        else:
            result = PyModule(self.pycore, resource.read(), resource=resource)
        self.module_map[resource] = result
        self.observer.add_resource(resource)
        return result

    def forget_all_data(self):
        for pymodule in self.module_map.values():
            pymodule._forget_concluded_data()

    def __str__(self):
        return 'PyCore caches %d PyModules\n' % len(self.module_map)


class _ClassesCache(object):

    def __init__(self, pycore):
        self.pycore = pycore
        self.pycore.cache_observers.append(self._invalidate_resource)
        self.cache = {}
        self.changed = True

    def _invalidate_resource(self, resource):
        if resource in self.cache:
            self.changed = True
            del self.cache[resource]

    def get_classes(self, task_handle):
        files = self.pycore.get_python_files()
        job_set = self._get_job_set(files, task_handle)
        result = []
        for resource in files:
            job_set.started_job('Working On <%s>' % resource.path)
            result.extend(self._get_resource_classes(resource))
            job_set.finished_job()
        self.changed = False
        return result

    def _get_job_set(self, files, task_handle):
        if self.changed:
            job_set = task_handle.create_jobset(name='Looking For Classes',
                                                 count=len(files))
        else:
            job_set = taskhandle.NullJobSet()
        return job_set

    def _get_resource_classes(self, resource):
        if resource not in self.cache:
            try:
                classes = self._calculate_resource_classes(resource)
                self.cache[resource] = classes
            except exceptions.ModuleSyntaxError:
                return []
        return self.cache[resource]

    def _calculate_resource_classes(self, resource):
        classes = []
        pymodule = self.pycore.resource_to_pyobject(resource)
        pyscope = pymodule.get_scope()
        for line in _ClassesCache._ClassFinder().\
            find_class_lines(pymodule.get_ast()):
            holding_scope = pyscope.get_inner_scope_for_line(line)
            if isinstance(holding_scope.pyobject, PyClass):
                classes.append(holding_scope.pyobject)
        return classes

    class _ClassFinder(object):

        def __init__(self):
            self.class_lines = []

        def _ClassDef(self, node):
            self.class_lines.append(node.lineno)
            self.find_class_lines(node)

        def find_class_lines(self, node):
            for child in ast.get_child_nodes(node):
                ast.walk(child, self)
            return self.class_lines


def perform_soi_on_changed_scopes(project, resource, old_contents):
    pycore = project.pycore
    if resource.exists() and pycore.is_python_file(resource):
        try:
            new_contents = resource.read()
            # detecting changes in new_contents relative to old_contents
            detector = _TextChangeDetector(new_contents, old_contents)
            def search_subscopes(pydefined):
                scope = pydefined.get_scope()
                return detector.is_changed(scope.get_start(), scope.get_end())
            def should_analyze(pydefined):
                scope = pydefined.get_scope()
                start = scope.get_start()
                end = scope.get_end()
                return detector.consume_changes(start, end)
            pycore.analyze_module(resource, should_analyze, search_subscopes)
        except exceptions.ModuleSyntaxError:
            pass


class _TextChangeDetector(object):

    def __init__(self, old, new):
        self.old = old
        self.new = new
        self._set_diffs()

    def _set_diffs(self):
        differ = difflib.Differ()
        self.lines = []
        lineno = 0
        for line in differ.compare(self.old.splitlines(True),
                                   self.new.splitlines(True)):
            if line.startswith(' '):
                lineno += 1
            elif line.startswith('-'):
                lineno += 1
                self.lines.append(lineno)

    def is_changed(self, start, end):
        """Tell whether any of start till end lines have changed

        The end points are inclusive and indices start from 1.
        """
        left, right = self._get_changed(start, end)
        if left < right:
            return True
        return False

    def consume_changes(self, start, end):
        """Clear the changed status of lines from start till end"""
        left, right = self._get_changed(start, end)
        if left < right:
            del self.lines[left:right]
        return left < right

    def _get_changed(self, start, end):
        left = bisect.bisect_left(self.lines, start)
        right = bisect.bisect_right(self.lines, end)
        return left, right
