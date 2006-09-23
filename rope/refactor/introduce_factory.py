import rope.codeanalyze
import rope.exceptions
import rope.pyobjects
import rope.refactor.rename

from rope.refactor.change import (ChangeSet, ChangeFileContents)


class IntroduceFactoryRefactoring(object):
    
    def __init__(self, pycore, resource, offset, factory_name):
        self.pycore = pycore
        self.resource = resource
        self.offset = offset
        self.factory_name = factory_name
        self.pymodule = self.pycore.resource_to_pyobject(self.resource)
        module_scope = self.pymodule.get_scope()
        source_code = self.pymodule.source_code
        word_finder = rope.codeanalyze.WordRangeFinder(source_code)
        self.old_name = word_finder.get_primary_at(offset).split('.')[-1]
        pyname_finder = rope.codeanalyze.ScopeNameFinder(source_code, module_scope)
        self.old_pyname = pyname_finder.get_pyname_at(offset)
        if self.old_pyname is None:
            return None
        if self.old_pyname.get_object().get_type() != rope.pyobjects.PyObject.get_base_type('Type'):
            raise rope.exceptions.RefactoringException(
                'Encapsulate field should be performed on a class.')

    def introduce_factory(self):
        changes = ChangeSet()
        class_scope = self.old_pyname.get_object().get_scope()
        self._change_occurances_in_other_modules(changes)
    
        rename_in_module = rope.refactor.rename.RenameInModule(
            self.pycore, [self.old_pyname], self.old_name, self._get_new_function_name(), True)
        source_code2 = rename_in_module.get_changed_module(pymodule=self.pymodule)
        if source_code2 is None:
            source_code2 = self.pymodule.source_code
        lines = source_code2.splitlines(True)
        start = class_scope.get_end()
        if class_scope.get_scopes():
            start = class_scope.get_scopes()[-1].get_end()
        result = lines[:start]
        result.append('\n')
        result.append('    @staticmethod\n')
        result.append('    def %s(*args, **kws):\n' % self.factory_name)
        result.append('        return %s(*args, **kws)\n' % self.old_name)
        result.extend(lines[start:])
        changes.add_change(ChangeFileContents(self.resource, ''.join(result)))
        return changes

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
