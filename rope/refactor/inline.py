from rope.base import codeanalyze
import rope.base.exceptions
import rope.base.pynames
import rope.base.pyobjects
import rope.refactor.sourceutils
from rope.refactor.change import ChangeSet, ChangeContents


class InlineRefactoring(object):
    
    def __init__(self, pycore, resource, offset):
        self.pycore = pycore
        self.pyname = codeanalyze.get_pyname_at(self.pycore, resource, offset)
        self.name = codeanalyze.get_name_at(resource, offset)
        if self.name is None:
            raise rope.base.exceptions.RefactoringException(
                'Inline refactoring should be performed on a method/local variable.')
        if self._is_variable():
            self.performer = _VariableInliner(pycore, self.name, self.pyname)
        elif self._is_method():
            self.performer = _MethodInliner(pycore, self.name, self.pyname)
        else:
            raise rope.base.exceptions.RefactoringException(
                'Inline refactoring should be performed on a method/local variable.')
        self.performer.check_exceptional_conditions()
    
    def get_changes(self):
        return self.performer.get_changes()
    
    def _is_variable(self):
        return isinstance(self.pyname, rope.base.pynames.AssignedName)

    def _is_method(self):
        return isinstance(self.pyname.get_object(), rope.base.pyobjects.PyFunction)


class _Inliner(object):
    
    def __init__(self, pycore, name, pyname):
        self.pycore = pycore
        self.name = name
        self.pyname = pyname

    def check_exceptional_conditions(self):
        pass

    def get_changes(self):
        pass


class _MethodInliner(_Inliner):
    
    def __init__(self, *args, **kwds):
        super(_MethodInliner, self).__init__(*args, **kwds)
    
    def get_changes(self):
        changes = ChangeSet()
        self._change_defining_file(changes)
        self._change_other_files(changes)
        return changes

    def _change_defining_file(self, changes):
        pyfunction = self.pyname.get_object()
        pymodule = pyfunction.get_module()
        resource = pyfunction.get_module().get_resource()
        scope = pyfunction.get_scope()
        source = pymodule.source_code
        lines = pymodule.lines
        start_offset = lines.get_line_start(scope.get_start())
        end_offset = lines.get_line_end(scope.get_end())
        result = source[:start_offset] + source[end_offset + 1:]
        changes.add_change(ChangeContents(resource, result))
    
    def _get_definition(self):
        pyfunction = self.pyname.get_object()
        pymodule = pyfunction.get_module()
        resource = pyfunction.get_module().get_resource()
        scope = pyfunction.get_scope()
        source = pymodule.source_code
        lines = pymodule.lines
        start_line = codeanalyze.LogicalLineFinder(lines).\
                     get_logical_line_in(scope.get_start())[1] + 1
        start_offset = lines.get_line_start(start_line)
        end_offset = lines.get_line_end(min(scope.get_end() + 1, len(source)))
        result = source[start_offset:end_offset]
        return result
    
    def _change_other_files(self, changes):
        occurrence_finder = rope.refactor.occurrences.FilteredOccurrenceFinder(
            self.pycore, self.name, [self.pyname], only_calls=True)
        for file in self.pycore.get_python_files():
            result = []
            last_changed = 0
            source = file.read()
            pymodule = None
            lines = None
            for occurrence in occurrence_finder.find_occurrences(file):
                if lines is None:
                    pymodule = self.pycore.resource_to_pyobject(file)
                    lines = pymodule.lines
                start, end = occurrence.get_primary_range()
                end_parens = self._find_end_parens(source, source.index('(', end))
                lineno = lines.get_line_number(start)
                start_line, end_line = codeanalyze.LogicalLineFinder(lines).\
                                       get_logical_line_in(lineno)
                line_start = lines.get_line_start(start_line)
                line_end = lines.get_line_end(end_line)
                result.append(source[last_changed:line_start])
                scope = pymodule.get_scope().get_inner_scope_for_line(start_line)
                result.append(rope.refactor.sourceutils.
                              indent_statements_for_scope(scope, self._get_definition()))
                last_changed = line_end + 1
            if result:
                result.append(source[last_changed:])
                changes.add_change(ChangeContents(file, ''.join(result)))
    
    def _find_end_parens(self, source, start):
        index = start
        open_count = 0
        while start < len(source):
            if start == '(':
                open_count += 1
            if start == ')':
                open_count -= 1
            if open_count == 0:
                return index
        return index


class _VariableInliner(_Inliner):
    
    def check_exceptional_conditions(self):
        if len(self.pyname.assigned_asts) != 1:
            raise rope.base.exceptions.RefactoringException(
                'Local variable should be assigned once or inlining.')

    def get_changes(self):
        pymodule = self.pyname.get_definition_location()[0]
        resource = pymodule.get_resource()
        definition_line = self.pyname.assigned_asts[0].lineno
        lines = pymodule.lines
        start, end = codeanalyze.LogicalLineFinder(lines).\
                     get_logical_line_in(definition_line)
        definition_lines = []
        for line_number in range(start, end + 1):
            line = lines.get_line(line_number).strip()
            if line.endswith('\\'):
                line = line[:-1]
            definition_lines.append(line)
        definition_with_assignment = ' '.join(definition_lines)
        if self._is_tuple_assignment(definition_with_assignment):
            raise rope.base.exceptions.RefactoringException(
                'Cannot inline tuple assignments.')
        definition = definition_with_assignment[definition_with_assignment.\
                                                index('=') + 1:].strip()
        
        changed_source = rope.refactor.rename.RenameInModule(
            self.pycore, [self.pyname], self.name, definition, replace_primary=True).\
            get_changed_module(pymodule=pymodule)
        if changed_source is None:
            changed_source = pymodule.source_code
        lines = codeanalyze.SourceLinesAdapter(changed_source)
        source = changed_source[:lines.get_line_start(start)] + \
                 changed_source[lines.get_line_end(end) + 1:]
        changes = ChangeSet()
        changes.add_change(ChangeContents(resource, source))
        return changes
    
    def _is_tuple_assignment(self, line):
        try:
            comma = line.index(',')
            assign = line.index('=')
            return comma < assign
        except ValueError:
            return False
