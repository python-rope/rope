import re

import rope.codeanalyze
import rope.pynames
import rope.pyobjects
from rope.refactor.change import (ChangeSet, ChangeFileContents,
                                  MoveResource, CreateFolder)
import rope.refactor.occurances

class RenameRefactoring(object):
    
    def __init__(self, pycore):
        self.pycore = pycore
    
    def local_rename(self, resource, offset, new_name):
        return self._rename(resource, offset, new_name, True)
    
    def rename(self, resource, offset, new_name):
        return self._rename(resource, offset, new_name)
    
    def _rename(self, resource, offset, new_name, in_file=False):
        old_name = rope.codeanalyze.get_name_at(resource, offset)
        old_pynames = self._get_old_pynames(offset, resource, in_file, old_name)
        if not old_pynames:
            return None
        # HACK: Do a local rename for names defined in function scopes.
        # XXX: This might cause problems for global keyword usages.
        if not in_file and len(old_pynames) == 1 and \
           self._is_renaming_a_function_local_name(old_pynames[0]):
            in_file = True
        files = self._get_interesting_files(resource, in_file)
        changes = ChangeSet()
        for file_ in files:
            new_content = RenameInModule(self.pycore, old_pynames, old_name, new_name).\
                          get_changed_module(file_)
            if new_content is not None:
                changes.add_change(ChangeFileContents(file_, new_content))
        
        if self._is_renaming_a_module(old_pynames):
            changes.add_change(self._rename_module(old_pynames[0].get_object(), new_name))
        return changes
    
    def _is_renaming_a_function_local_name(self, pyname):
        module, lineno = pyname.get_definition_location()
        if lineno is None:
            return False
        scope = module.get_scope().get_inner_scope_for_line(lineno)
        if isinstance(pyname, rope.pynames.DefinedName) and \
           scope.get_kind() in ('Function', 'Class'):
            scope = scope.parent
        return scope.get_kind() == 'Function' and pyname in scope.get_names().values()
    
    def _is_renaming_a_module(self, old_pynames):
        if len(old_pynames) == 1 and \
           old_pynames[0].get_object().get_type() == rope.pycore.PyObject.get_base_type('Module'):
            return True
        return False

    def _get_old_pynames(self, offset, resource, in_file, old_name):
        old_pyname = rope.codeanalyze.get_pyname_at(self.pycore, resource,
                                                    offset)
        if old_pyname is None:
            return []
        if self._is_a_class_method(old_pyname) and not in_file:
            return self._get_all_methods_in_hierarchy(old_pyname.get_object().
                                                      parent, old_name)
        else:
            return [old_pyname]

    def _get_interesting_files(self, resource, in_file):
        if not in_file:
            return self.pycore.get_python_files()
        return [resource]
    
    def _is_a_class_method(self, pyname):
        return isinstance(pyname, rope.pynames.DefinedName) and \
               pyname.get_object().get_type() == rope.pyobjects.PyObject.get_base_type('Function') and \
               pyname.get_object().parent.get_type() == rope.pyobjects.PyObject.get_base_type('Type')
    
    def _get_superclasses_defining_method(self, pyclass, attr_name):
        result = set()
        for superclass in pyclass.get_superclasses():
            if attr_name in superclass.get_attributes():
                result.update(self._get_superclasses_defining_method(superclass, attr_name))
        if not result:
            return set([pyclass])
        return result
    
    def _get_all_methods_in_subclasses(self, pyclass, attr_name):
        result = set([pyclass.get_attribute(attr_name)])
        for subclass in self.pycore.get_subclasses(pyclass):
            result.update(self._get_all_methods_in_subclasses(subclass, attr_name))
        return result
    
    def _get_all_methods_in_hierarchy(self, pyclass, attr_name):
        superclasses = self._get_superclasses_defining_method(pyclass, attr_name)
        methods = set()
        for superclass in superclasses:
            methods.update(self._get_all_methods_in_subclasses(superclass, attr_name))
        return methods
    
    def _rename_module(self, pyobject, new_name):
        resource = pyobject.get_resource()
        if not resource.is_folder():
            new_name = new_name + '.py'
        parent_path = resource.get_parent().get_path()
        if parent_path == '':
            new_location = new_name
        else:
            new_location = parent_path + '/' + new_name
        return MoveResource(resource, new_location)


class RenameInModule(object):
    
    def __init__(self, pycore, old_pynames, old_name, new_name,
                 only_calls=False, replace_primary=False, imports=True):
        self.occurances_finder = rope.refactor.occurances.OccurrenceFinder(
            pycore, old_pynames, old_name, only_calls,
            replace_primary, imports)
        self.new_name = new_name
    
    def get_changed_module(self, resource=None, pymodule=None):
        source_code = self._get_source(resource, pymodule)
        result = []
        last_modified_char = 0
        for start, end in self.occurances_finder.find_occurances(resource, pymodule):
            result.append(source_code[last_modified_char:start]
                          + self.new_name)
            last_modified_char = end
        if last_modified_char != 0:
            result.append(source_code[last_modified_char:])
            return ''.join(result)
        return None
    
    def _get_source(self, resource, pymodule):
        if resource is not None:
            return resource.read()
        else:
            return pymodule.source_code

