import rope.codeanalyze
import rope.refactor.occurrences
from rope.refactor import sourcetools

from rope.refactor.rename import RenameInModule
from rope.refactor.change import ChangeSet, ChangeFileContents


class EncapsulateFieldRefactoring(object):
    
    def __init__(self, pycore, resource, offset):
        self.pycore = pycore
        self.resource = resource
        self.offset = offset
        self.name = rope.codeanalyze.get_name_at(self.resource, self.offset)
        self.pyname = rope.codeanalyze.get_pyname_at(self.pycore, self.resource, self.offset)
    
    def encapsulate_field(self):
        changes = ChangeSet()
        rename_in_module = GetterSetterRenameInModule(self.pycore, self.name,
                                                      [self.pyname])
        
        self._change_holding_module(changes, self.name)
        for file in self.pycore.get_python_files():
            if file == self.resource:
                continue
            result = rename_in_module.get_changed_module(file)
            if result is not None:
                changes.add_change(ChangeFileContents(file, result))
        return changes
    
    def _get_defining_class_scope(self, pyname):
        defining_pymodule, defining_line = pyname.get_definition_location()
        defining_scope = defining_pymodule.get_scope().get_inner_scope_for_line(defining_line)
        if defining_scope.get_kind() == 'Function':
            defining_scope = defining_scope.parent
        return defining_scope

    def _change_holding_module(self, changes, name):
        getter = '    def get_%s(self):\n        return self.%s' % (name, name)
        setter = '    def set_%s(self, value):\n        self.%s = value' % (name, name)
        pymodule = self.pycore.resource_to_pyobject(self.resource)
        new_source = sourcetools.add_methods(
            self.pyname.get_definition_location()[0],
            self._get_defining_class_scope(self.pyname), [getter, setter])
        changes.add_change(ChangeFileContents(pymodule.get_resource(), new_source))


class GetterSetterRenameInModule(object):
    
    def __init__(self, pycore, name, pynames):
        self.pycore = pycore
        self.name = name
        self.occurrences_finder = rope.refactor.occurrences.\
                                  FilteredOccurrenceFinder(pycore, name, pynames)
        self.getter = 'get_' + name
        self.setter = 'set_' + name
    
    def get_changed_module(self, resource=None, pymodule=None):
        return _FindChangesForModule(self, resource, pymodule).get_changed_module()


class _FindChangesForModule(object):
    
    def __init__(self, rename_in_module, resource, pymodule):
        self.pycore = rename_in_module.pycore
        self.occurrences_finder = rename_in_module.occurrences_finder
        self.getter = rename_in_module.getter
        self.setter = rename_in_module.setter
        self.resource = resource
        self.pymodule = pymodule
        self.source_code = None
        self.lines = None
        self.last_modified = 0
        self.last_set = None
        self.set_index = None
        
    def get_changed_module(self):
        result = []
        line_finder = None
        for occurrence in self.occurrences_finder.find_occurrences(self.resource,
                                                                   self.pymodule):
            start, end = occurrence.get_word_range()
            self._manage_writes(start, result)
            result.append(self._get_source()[self.last_modified:start])
            if occurrence.is_written():
                result.append(self.setter + '(')
                if line_finder is None:
                    line_finder = rope.codeanalyze.LogicalLineFinder(self._get_lines())
                current_line = self._get_lines().get_line_number(start)
                start_line, end_line = line_finder.get_logical_line_in(current_line)
                self.last_set = self._get_lines().get_line_end(end_line)                
                end = self._get_source().index('=', end) + 1
                self.set_index = len(result)
            else:
                result.append(self.getter + '()')
            self.last_modified = end
        if self.last_modified != 0:
            self._manage_writes(len(self._get_source()), result)
            result.append(self._get_source()[self.last_modified:])
            return ''.join(result)
        return None

    def _manage_writes(self, offset, result):
        if self.last_set is not None and self.last_set <= offset:
            result.append(self._get_source()[self.last_modified:self.last_set])
            set_value = ''.join(result[self.set_index:]).strip()
            del result[self.set_index:]
            result.append(set_value + ')')
            self.last_modified = self.last_set
            self.last_set = None
    
    def _get_source(self):
        if self.source_code is None:
            if self.resource is not None:
                self.source_code = self.resource.read()
            else:
                self.source_code = self.pymodule.source_code
        return self.source_code

    def _get_lines(self):
        if self.lines is None:
            if self.pymodule is None:
                self.pymodule = self.pycore.resource_to_pyobject(self.resource)
            self.lines = self.pymodule.lines
        return self.lines
