import rope.codeanalyze
import rope.exceptions
import rope.pynames
from rope.refactor.change import ChangeSet, ChangeFileContents

class InlineRefactoring(object):
    
    def __init__(self, pycore, resource, offset):
        self.pycore = pycore
        self.resource = resource
        self.pymodule = self.pycore.resource_to_pyobject(resource)
        self.pyname = rope.codeanalyze.get_pyname_at(self.pycore, resource, offset)
        self.name = rope.codeanalyze.get_name_at(resource, offset)
        self._check_exceptional_conditions()
    
    def inline(self):
        definition_line = self.pyname.assigned_asts[0].lineno
        lines = rope.codeanalyze.SourceLinesAdapter(self.pymodule.source_code)
        start, end = rope.codeanalyze.LogicalLineFinder(lines).\
                     get_logical_line_in(definition_line)
        definition_lines = []
        for line_number in range(start, end + 1):
            line = lines.get_line(line_number).strip()
            if line.endswith('\\'):
                line = line[:-1]
            definition_lines.append(line)
        definition_with_assignment = ' '.join(definition_lines)
        if self._is_tuple_assignment(definition_with_assignment):
            raise rope.exceptions.RefactoringException(
                'Cannot inline tuple assignments.')
        definition = definition_with_assignment[definition_with_assignment.\
                                                index('=') + 1:].strip()
        
        changed_source = rope.refactor.rename.RenameInModule(
            self.pycore, [self.pyname], self.name, definition).get_changed_module(pymodule=self.pymodule)
        if changed_source is None:
            changed_source = self.pymodule.source_code
        lines = rope.codeanalyze.SourceLinesAdapter(changed_source)
        source = changed_source[:lines.get_line_start(start)] + \
                 changed_source[lines.get_line_end(end) + 1:]
        changes = ChangeSet()
        changes.add_change(ChangeFileContents(self.resource, source))
        return changes
    
    def _is_tuple_assignment(self, line):
        try:
            comma = line.index(',')
            assign = line.index('=')
            return comma < assign
        except ValueError:
            return False

    def _check_exceptional_conditions(self):
        if self.pyname is None or not isinstance(self.pyname, rope.pynames.AssignedName):
            raise rope.exceptions.RefactoringException(
                'Inline local variable should be performed on a local variable.')
        if len(self.pyname.assigned_asts) != 1:
            raise rope.exceptions.RefactoringException(
                'Local variable should be assigned Once.')
