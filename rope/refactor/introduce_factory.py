import rope.codeanalyze
import rope.exceptions
import rope.pyobjects
import rope.refactor.rename

from rope.refactor.change import (ChangeSet, ChangeFileContents)
from rope.refactor import sourcetools


class IntroduceFactoryRefactoring(object):
    
    def __init__(self, pycore, resource, offset, factory_name):
        self.pycore = pycore
        self.offset = offset
        self.factory_name = factory_name
        
        current_pymodule = self.pycore.resource_to_pyobject(resource)
        module_scope = current_pymodule.get_scope()
        source_code = current_pymodule.source_code
        word_finder = rope.codeanalyze.WordRangeFinder(source_code)
        self.old_name = word_finder.get_primary_at(offset).split('.')[-1]
        pyname_finder = rope.codeanalyze.ScopeNameFinder(source_code, module_scope)
        self.old_pyname = pyname_finder.get_pyname_at(offset)
        if self.old_pyname is None:
            return None
        if self.old_pyname.get_object().get_type() != rope.pyobjects.PyObject.get_base_type('Type'):
            raise rope.exceptions.RefactoringException(
                'Encapsulate field should be performed on a class.')
        self.pymodule = self.old_pyname.get_object().get_module()
        self.resource = self.pymodule.get_resource()

    def introduce_factory(self):
        changes = ChangeSet()
        class_scope = self.old_pyname.get_object().get_scope()
        self._change_occurances_in_other_modules(changes)
    
        rename_in_module = rope.refactor.rename.RenameInModule(
            self.pycore, [self.old_pyname], self.old_name, self._get_new_function_name(), True)
        source_code = rename_in_module.get_changed_module(pymodule=self.pymodule)
        if source_code is None:
            source_code = self.pymodule.source_code
        lines = rope.codeanalyze.SourceLinesAdapter(source_code)
        start_line = class_scope.get_end()
        if class_scope.get_scopes():
            start_line = class_scope.get_scopes()[-1].get_end()
        start = lines.get_line_end(start_line) + 1
        result = source_code[:start]
        result += '\n'
        unindented_factory = ('@staticmethod\n' +
                              'def %s(*args, **kws):\n' % self.factory_name +
                              '    return %s(*args, **kws)\n' % self.old_name)
        indented_factory = sourcetools.indent_lines(unindented_factory,
                                                    self._get_scope_indents(lines, class_scope) + 4)
        result+= indented_factory
        result += source_code[start:]
        changes.add_change(ChangeFileContents(self.resource, result))
        return changes
    
    def _get_scope_indents(self, lines, scope):
        return sourcetools.get_indents(lines, scope.get_start())

    def _get_new_function_name(self):
        return self.old_name + '.' + self.factory_name
    
    def _change_occurances_in_other_modules(self, changes):
        for file_ in self.pycore.get_python_files():
            if file_ == self.resource:
                continue
            rename_in_module = rope.refactor.rename.RenameInModule(
                self.pycore, [self.old_pyname], self.old_name,
                self._get_new_function_name(), True)
            changed_code = rename_in_module.get_changed_module(resource=file_)
            if changed_code is not None:
                changes.add_change(ChangeFileContents(file_, changed_code))
