import rope.codeanalyze
import rope.exceptions
import rope.pyobjects
import rope.refactor.rename
import rope.importutils

from rope.refactor.change import (ChangeSet, ChangeFileContents)
from rope.refactor import sourcetools

class IntroduceFactoryRefactoring(object):
    
    def __init__(self, pycore, resource, offset, factory_name, global_factory=False):
        self.pycore = pycore
        self.offset = offset
        self.factory_name = factory_name
        self.global_factory = global_factory
        
        self.old_pyname = \
            rope.codeanalyze.get_pyname_at(self.pycore, resource, offset)
        if self.old_pyname is None or \
           self.old_pyname.get_object().get_type() != rope.pyobjects.PyObject.get_base_type('Type'):
            raise rope.exceptions.RefactoringException(
                'Introduce factory should be performed on a class.')
        self.old_name = self.old_pyname.get_object()._get_ast().name
        self.pymodule = self.old_pyname.get_object().get_module()
        self.resource = self.pymodule.get_resource()

    def introduce_factory(self):
        changes = ChangeSet()
        self._change_occurances_in_other_modules(changes)
    
        self._change_resource(changes)
        return changes

    def _change_resource(self, changes):
        class_scope = self.old_pyname.get_object().get_scope()
        rename_in_module = rope.refactor.rename.RenameInModule(
            self.pycore, [self.old_pyname], self.old_name, self._get_new_function_name(), True)
        source_code = rename_in_module.get_changed_module(pymodule=self.pymodule)
        if source_code is None:
            source_code = self.pymodule.source_code
        lines = rope.codeanalyze.SourceLinesAdapter(source_code)
        start = self._get_insertion_offset(class_scope, lines)
        result = source_code[:start]
        result += self._get_factory_method(lines, class_scope)
        result += source_code[start:]
        changes.add_change(ChangeFileContents(self.resource, result))

    def _get_insertion_offset(self, class_scope, lines):
        start_line = class_scope.get_end()
        if class_scope.get_scopes():
            start_line = class_scope.get_scopes()[-1].get_end()
        start = lines.get_line_end(start_line) + 1
        return start

    def _get_factory_method(self, lines, class_scope):
        if self.global_factory:
            if self._get_scope_indents(lines, class_scope) > 0:
                raise rope.exceptions.RefactoringException(
                    'Cannot make global factory method for nested classes.')
            return ('\ndef %s(*args, **kwds):\n    return %s(*args, **kwds)\n' %
                    (self.factory_name, self.old_name))
        unindented_factory = ('@staticmethod\n' +
                              'def %s(*args, **kwds):\n' % self.factory_name +
                              '    return %s(*args, **kwds)\n' % self.old_name)
        return '\n' + sourcetools.indent_lines(
            unindented_factory, self._get_scope_indents(lines, class_scope) + 4)
    
    def _get_scope_indents(self, lines, scope):
        return sourcetools.get_indents(lines, scope.get_start())

    def _get_new_function_name(self):
        if self.global_factory:
            return self.factory_name
        else:
            return self.old_name + '.' + self.factory_name
    
    def _change_occurances_in_other_modules(self, changes):
        changed_name = self._get_new_function_name()
        import_tools = rope.importutils.ImportTools(self.pycore)
        new_import = import_tools.get_import_for_module(self.pymodule)
        if self.global_factory:
            changed_name = new_import.names_and_aliases[0][0] + '.' + self.factory_name
        
        for file_ in self.pycore.get_python_files():
            if file_ == self.resource:
                continue
            rename_in_module = rope.refactor.rename.RenameInModule(
                self.pycore, [self.old_pyname], self.old_name, changed_name,
                only_calls=True, replace_primary=self.global_factory)
            changed_code = rename_in_module.get_changed_module(resource=file_)
            if changed_code is not None:
                if self.global_factory:
                    new_pymodule = self.pycore.get_string_module(changed_code, self.resource)
                    module_with_imports = import_tools.get_module_with_imports(new_pymodule)
                    module_with_imports.add_import(new_import)
                    changed_code = module_with_imports.get_changed_source()
                changes.add_change(ChangeFileContents(file_, changed_code))
