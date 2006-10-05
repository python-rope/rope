import rope.codeanalyze
import rope.exceptions
import rope.pynames
from rope.refactor.change import ChangeSet, ChangeFileContents

class InlineRefactoring(object):
    
    def __init__(self, pycore):
        self.pycore = pycore
    
    def inline(self, resource, offset):
        pymodule = self.pycore.resource_to_pyobject(resource)
        pyname = rope.codeanalyze.get_pyname_at(self.pycore, resource, offset)
        name = rope.codeanalyze.get_name_at(resource, offset)
        if pyname is None or not isinstance(pyname, rope.pynames.AssignedName):
            raise rope.exceptions.RefactoringException(
                'Inline local variable should be performed on a local variable.')
        if len(pyname.assigned_asts) != 1:
            raise rope.exceptions.RefactoringException(
                'Local variable should be assigned Once.')
        definition_line = pyname.assigned_asts[0].lineno
        lines = rope.codeanalyze.SourceLinesAdapter(pymodule.source_code)
        line = lines.get_line(definition_line)
        definition = line[line.index('=') + 1:].strip()
        changed_source = rope.refactor.rename.RenameInModule(
            self.pycore, [pyname], name, definition).get_changed_module(pymodule=pymodule)
        if changed_source is None:
            changed_source = pymodule.source_code
        lines = rope.codeanalyze.SourceLinesAdapter(changed_source)
        source = changed_source[:lines.get_line_start(definition_line)] + \
                 changed_source[lines.get_line_end(definition_line) + 1:]
        changes = ChangeSet()
        changes.add_change(ChangeFileContents(resource, source))
        return changes
