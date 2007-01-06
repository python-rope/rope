import rope.base.codeanalyze
import rope.base.pynames
import rope.base.pyobjects
import rope.base.exceptions
from rope.refactor import occurrences
from rope.refactor import sourceutils
from rope.refactor.change import ChangeSet, ChangeContents, MoveResource


class RenameRefactoring(object):

    def __init__(self, pycore, resource, offset=None):
        """If `offset` is None `resource` will be renamed"""
        self.pycore = pycore
        self.resource = resource
        if offset is not None:
            self.old_name = rope.base.codeanalyze.get_name_at(self.resource, offset)
            self.old_pyname = rope.base.codeanalyze.get_pyname_at(self.pycore, resource,
                                                                  offset)
            if self.old_pyname is None:
                raise rope.base.exceptions.RefactoringException(
                    'Rename refactoring should be performed on python identifiers.')
        else:
            if not resource.is_folder() and resource.get_name() == '__init__.py':
                resource = resource.get_parent()
            dummy_pymodule = self.pycore.get_string_module('')
            self.old_pyname = rope.base.pynames.ImportedModule(dummy_pymodule, resource=resource)
            if resource.is_folder():
                self.old_name = resource.get_name()
            else:
                self.old_name = resource.get_name()[:-3]

    def get_old_name(self):
        return self.old_name

    def get_changes(self, new_name, in_file=False):
        old_pynames = self._get_old_pynames(in_file)
        if not old_pynames:
            return None
        # HACK: Do a local rename for names defined in function scopes.
        # XXX: This might cause problems for global keyword usages.
        if not in_file and len(old_pynames) == 1 and \
           self._is_renaming_a_function_local_name():
            in_file = True
        files = self._get_interesting_files(in_file)
        changes = ChangeSet()
        for file_ in files:
            occurance_finder = occurrences.FilteredOccurrenceFinder(self.pycore, self.old_name, old_pynames)
            new_content = rename_in_module(occurance_finder, new_name, resource=file_)
            if new_content is not None:
                changes.add_change(ChangeContents(file_, new_content))

        if self._is_renaming_a_module():
            changes.add_change(self._rename_module(old_pynames[0].get_object(), new_name))
        return changes

    def _is_renaming_a_function_local_name(self):
        module, lineno = self.old_pyname.get_definition_location()
        if lineno is None:
            return False
        scope = module.get_scope().get_inner_scope_for_line(lineno)
        if isinstance(self.old_pyname, rope.base.pynames.DefinedName) and \
           scope.get_kind() in ('Function', 'Class'):
            scope = scope.parent
        return scope.get_kind() == 'Function' and \
               self.old_pyname in scope.get_names().values() and \
               isinstance(self.old_pyname, rope.base.pynames.AssignedName)

    def _is_renaming_a_module(self):
        if self.old_pyname.get_object().get_type() == rope.base.pycore.PyObject.get_base_type('Module'):
            return True
        return False

    def _get_old_pynames(self, in_file):
        if self.old_pyname is None:
            return []
        if self._is_a_class_method() and not in_file:
            return self._get_all_methods_in_hierarchy(self.old_pyname.get_object().
                                                      parent, self.old_name)
        else:
            return [self.old_pyname]

    def _get_interesting_files(self, in_file):
        if not in_file:
            return self.pycore.get_python_files()
        return [self.resource]

    def _is_a_class_method(self):
        pyname = self.old_pyname
        return isinstance(pyname, rope.base.pynames.DefinedName) and \
               pyname.get_object().get_type() == rope.base.pyobjects.PyObject.get_base_type('Function') and \
               pyname.get_object().parent.get_type() == rope.base.pyobjects.PyObject.get_base_type('Type')

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


def rename_in_module(occurrences_finder, new_name, resource=None,
                     pymodule=None, replace_primary=False):
    if resource is not None:
        source_code = resource.read()
    else:
        source_code = pymodule.source_code
    change_collector = sourceutils.ChangeCollector(source_code)
    for occurrence in occurrences_finder.find_occurrences(resource, pymodule):
        if replace_primary and occurrence.is_a_fixed_primary():
            continue
        if replace_primary:
            start, end = occurrence.get_primary_range()
        else:
            start, end = occurrence.get_word_range()
        change_collector.add_change(start, end, new_name)
    return change_collector.get_changed()
