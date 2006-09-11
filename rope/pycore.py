import re
import sys

import rope.objectinfer
import rope.refactor
import rope.dynamicoi
from rope.exceptions import ModuleNotFoundException
from rope.pyobjects import *


class PyCore(object):

    def __init__(self, project):
        self.project = project
        self.module_map = {}
        self.object_infer = rope.objectinfer.ObjectInfer(self)
        self.refactoring = rope.refactor.PythonRefactoring(self)
        self.dynamicoi = rope.dynamicoi.DynamicObjectInference(self)

    def get_module(self, name, current_folder=None):
        """Returns a `PyObject` if the module was found."""
        module = self.find_module(name, current_folder)
        if module is None:
            raise ModuleNotFoundException('Module %s not found' % name)
        return self.resource_to_pyobject(module)
    
    def get_relative_module(self, name, current_folder, level):
        module = self.find_relative_module(name, current_folder, level)
        if module is None:
            raise ModuleNotFoundException('Module %s not found' % name)
        return self.resource_to_pyobject(module)
    
    def get_string_module(self, module_content, resource=None):
        """Returns a `PyObject` object for the given module_content"""
        return PyModule(self, module_content, resource)

    def get_string_scope(self, module_content, resource=None):
        """Returns a `Scope` object for the given module_content"""
        return self.get_string_module(module_content, resource).get_scope()

    def _invalidate_resource_cache(self, resource):
        if resource in self.module_map:
            local_module = self.module_map[resource]
            del self.module_map[resource]
            resource.remove_change_observer(self._invalidate_resource_cache)
            for dependant in local_module.dependant_modules:
                self._invalidate_resource_cache(dependant)

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
    
    def _get_python_path_folders(self):
        result = []
        for src in sys.path:
            try:
                src_folder = self.project.get_out_of_project_resource(src)
                result.append(src_folder)
            except rope.exceptions.RopeException:
                pass
        return result
    
    def find_module(self, module_name, current_folder=None):
        """Returns a resource pointing to the given module
        
        returns None if it can not be found
        """
        module_resource_list = self._find_module_resource_list(module_name,
                                                               current_folder)
        if module_resource_list is not None:
            return module_resource_list[-1]
    
    def find_relative_module(self, module_name, current_folder, level):
        for i in range(level - 1):
            current_folder = current_folder.get_parent()
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
        for src in self._get_python_path_folders():
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
        return self._find_source_folders(self.project.get_root_folder())
    
    def resource_to_pyobject(self, resource):
        if resource in self.module_map:
            return self.module_map[resource]
        if resource.is_folder():
            result = PyPackage(self, resource)
        else:
            result = PyModule(self, resource.read(), resource=resource)
        self.module_map[resource] = result
        resource.add_change_observer(self._invalidate_resource_cache)
        return result
    
    def get_python_files(self):
        """Returns all python files available in the project"""
        return [resource for resource in self.project.get_files()
                if resource.get_name().endswith('.py')]

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
            if resource.get_name().endswith('.py'):
                result.append(folder)
        for resource in folder.get_folders():
            result.extend(self._find_source_folders(resource))
        return result
    
    def _get_object_infer(self):
        return self.object_infer
    
    def get_refactoring(self):
        return self.refactoring

    def run_module(self, resource, stdin=None, stdout=None):
        return self.dynamicoi.run_module(resource, stdin, stdout)
    
    def get_subclasses(self, pyclass):
        classes = []
        pattern = re.compile(r'^\s*class\s+\w', re.M)
        for resource in self.get_python_files():
            pyscope = self.resource_to_pyobject(resource).get_scope()
            import rope.codeanalyze
            source = pyscope.pyobject.source_code
            lines = rope.codeanalyze.SourceLinesAdapter(source)
            for match in pattern.finditer(source):
                holding_scope = pyscope.get_inner_scope_for_line(lines.get_line_number(match.start()))
                classes.append(holding_scope.pyobject)
        return [class_ for class_ in classes if pyclass in class_.get_superclasses()]
