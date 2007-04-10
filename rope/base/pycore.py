import difflib
import re
import sys

import rope.base.oi.objectinfo
import rope.base.oi.objectinfer
import rope.base.project
from rope.base.exceptions import ModuleNotFoundError
from rope.base.oi import dynamicoi
from rope.base.pyobjects import PyModule, PyPackage, PyClass


class PyCore(object):

    def __init__(self, project):
        self.project = project
        self.module_map = {}
        self.classes = None
        observer = rope.base.project.ResourceObserver(
            self._invalidate_resource_cache, self._invalidate_resource_cache)
        self.observer = rope.base.project.FilteredResourceObserver(observer)
        self.project.add_observer(self.observer)
        self.object_info = rope.base.oi.objectinfo.ObjectInfoManager(project)
        self.object_infer = rope.base.oi.objectinfer.ObjectInfer(self)
        if project.get_prefs().get('automatic_soi', False):
            self._init_automatic_soi()

    def _init_automatic_soi(self):
        observer = rope.base.project.ResourceObserver(self._file_changed,
                                                      self._file_changed)
        self.project.add_observer(observer)

    def _file_changed(self, resource, new_resource=None):
        if resource.exists() and self.is_python_file(resource):
            try:
                old_contents = self.project.history.get_prev_contents(resource)
                new_contents = resource.read()
                # detecting changes in new_contents relative to old_contents
                detector = TextChangeDetector(new_contents, old_contents)
                def should_analyze(pydefined):
                    scope = pydefined.get_scope()
                    return detector.is_changed(scope.get_start(), scope.get_end())
                self.analyze_module(resource, should_analyze)
            except SyntaxError:
                pass

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
        self.classes = None
        if resource in self.module_map:
            local_module = self.module_map[resource]
            self.observer.remove_resource(resource)
            del self.module_map[resource]
            local_module._invalidate_concluded_data()

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
            module = self._find_module_in_source_folder(current_folder, module_name)
            if module is not None:
                return module
        return None

    def get_source_folders(self):
        """Returns project source folders"""
        if self.project.root is None:
            return []
        return self._find_source_folders(self.project.root)

    def resource_to_pyobject(self, resource):
        if resource in self.module_map:
            return self.module_map[resource]
        if resource.is_folder():
            result = PyPackage(self, resource)
        else:
            result = PyModule(self, resource.read(), resource=resource)
        self.module_map[resource] = result
        self.observer.add_resource(resource)
        return result

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

    def _invalidate_all_concluded_data(self):
        for module in self.module_map.values():
            module._invalidate_concluded_data()

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
        runner.add_finishing_observer(self._invalidate_all_concluded_data)
        runner.run()
        return runner

    def analyze_module(self, resource, should_analyze=None):
        """Analyze `resource` module for static object inference

        This function forces rope to analyze this module to concluded
        information about function calls.

        """
        pymodule = self.resource_to_pyobject(resource)
        pymodule._invalidate_concluded_data()
        self.object_infer.soi.analyze_module(pymodule, should_analyze)
        pymodule._invalidate_concluded_data()

    def get_subclasses(self, pyclass):
        if self.classes is None:
            classes = []
            pattern = re.compile(r'^[ \t]*class[ \t]+\w', re.M)
            for resource in self.get_python_files():
                pyscope = self.resource_to_pyobject(resource).get_scope()
                source = pyscope.pyobject.source_code
                for match in pattern.finditer(source):
                    holding_scope = pyscope.get_inner_scope_for_offset(match.start())
                    if isinstance(holding_scope.pyobject, PyClass):
                        classes.append(holding_scope.pyobject)
            self.classes = classes
        return [class_ for class_ in self.classes
                if pyclass in class_.get_superclasses()]


class TextChangeDetector(object):

    def __init__(self, old, new):
        self.old = old
        self.new = new
        self._set_diffs()

    def _set_diffs(self):
        differ = difflib.Differ()
        self.lines = []
        for line in differ.compare(self.old.splitlines(True),
                                   self.new.splitlines(True)):
            if line.startswith(' '):
                self.lines.append(False)
            elif line.startswith('-'):
                self.lines.append(True)

    def is_changed(self, start, end):
        """Tell whether any of start till end lines have changed

        The end points are inclusive and indices start from 1.
        """
        for i in range(start - 1, min(end, len(self.lines))):
            if self.lines[i]:
                return True
        return False
