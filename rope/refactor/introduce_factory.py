import rope.base.codeanalyze
import rope.base.exceptions
import rope.base.pyobjects
import rope.refactor.importutils
from rope.refactor import rename
from rope.refactor import occurrences
from rope.refactor import sourceutils

from rope.refactor.change import (ChangeSet, ChangeContents)


class IntroduceFactoryRefactoring(object):
    
    def __init__(self, pycore, resource, offset):
        self.pycore = pycore
        self.offset = offset
        
        self.old_pyname = \
            rope.base.codeanalyze.get_pyname_at(self.pycore, resource, offset)
        if self.old_pyname is None or \
           self.old_pyname.get_object().get_type() != rope.base.pyobjects.PyObject.get_base_type('Type'):
            raise rope.base.exceptions.RefactoringException(
                'Introduce factory should be performed on a class.')
        self.old_name = self.old_pyname.get_object()._get_ast().name
        self.pymodule = self.old_pyname.get_object().get_module()
        self.resource = self.pymodule.get_resource()

    def get_changes(self, factory_name, global_factory=False):
        changes = ChangeSet()
        self._change_occurrences_in_other_modules(changes, factory_name,
                                                  global_factory)
        self._change_resource(changes, factory_name, global_factory)
        return changes

    def _change_resource(self, changes, factory_name, global_factory):
        class_scope = self.old_pyname.get_object().get_scope()
        occurrence_finder = occurrences.FilteredOccurrenceFinder(
            self.pycore, self.old_name, [self.old_pyname], only_calls=True)
        source_code = rename.rename_in_module(
            occurrence_finder, self._get_new_function_name(factory_name, global_factory),
            pymodule=self.pymodule)
        if source_code is None:
            source_code = self.pymodule.source_code
        lines = self.pymodule.lines
        start = self._get_insertion_offset(class_scope, lines)
        result = source_code[:start]
        result += self._get_factory_method(lines, class_scope,
                                           factory_name, global_factory)
        result += source_code[start:]
        changes.add_change(ChangeContents(self.resource, result))

    def _get_insertion_offset(self, class_scope, lines):
        start_line = class_scope.get_end()
        if class_scope.get_scopes():
            start_line = class_scope.get_scopes()[-1].get_end()
        start = lines.get_line_end(start_line) + 1
        return start

    def _get_factory_method(self, lines, class_scope,
                            factory_name, global_factory):
        if global_factory:
            if self._get_scope_indents(lines, class_scope) > 0:
                raise rope.base.exceptions.RefactoringException(
                    'Cannot make global factory method for nested classes.')
            return ('\ndef %s(*args, **kwds):\n    return %s(*args, **kwds)\n' %
                    (factory_name, self.old_name))
        unindented_factory = ('@staticmethod\n' +
                              'def %s(*args, **kwds):\n' % factory_name +
                              '    return %s(*args, **kwds)\n' % self.old_name)
        return '\n' + sourceutils.indent_lines(
            unindented_factory, self._get_scope_indents(lines, class_scope) + 4)
    
    def _get_scope_indents(self, lines, scope):
        return sourceutils.get_indents(lines, scope.get_start())

    def _get_new_function_name(self, factory_name, global_factory):
        if global_factory:
            return factory_name
        else:
            return self.old_name + '.' + factory_name
    
    def _change_occurrences_in_other_modules(self, changes,
                                             factory_name, global_factory):
        changed_name = self._get_new_function_name(factory_name, global_factory)
        import_tools = rope.refactor.importutils.ImportTools(self.pycore)
        new_import = import_tools.get_import_for_module(self.pymodule)
        if global_factory:
            changed_name = new_import.names_and_aliases[0][0] + '.' + factory_name
        
        for file_ in self.pycore.get_python_files():
            if file_ == self.resource:
                continue
            occurrence_finder = occurrences.FilteredOccurrenceFinder(
                self.pycore, self.old_name, [self.old_pyname], only_calls=True)
            changed_code = rename.rename_in_module(occurrence_finder, changed_name, resource=file_,
                                                   replace_primary=global_factory)
            if changed_code is not None:
                if global_factory:
                    new_pymodule = self.pycore.get_string_module(changed_code, self.resource)
                    module_with_imports = import_tools.get_module_with_imports(new_pymodule)
                    module_with_imports.add_import(new_import)
                    changed_code = module_with_imports.get_changed_source()
                changes.add_change(ChangeContents(file_, changed_code))
