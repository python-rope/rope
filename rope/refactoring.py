import re

from rope.codeanalyze import (WordRangeFinder, ScopeNameFinder,
                              StatementRangeFinder, SourceLinesAdapter,
                              HoldingScopeFinder)

class Refactoring(object):

    def rename(self, source_code, offset, new_name):
        pass


class PythonRefactoring(Refactoring):

    def __init__(self, pycore):
        self.pycore = pycore
    
    def rename(self, source_code, offset, new_name):
        result = []
        module_scope = self.pycore.get_string_scope(source_code)
        word_finder = WordRangeFinder(source_code)
        old_name = word_finder.get_statement_at(offset)
        pyname_finder = ScopeNameFinder(source_code, module_scope)
        old_pyname = pyname_finder.get_pyname_at(offset)
        if old_pyname is None:
            return source_code
        pattern = re.compile('\\b' + old_name + '\\b')
        last_modified_char = 0
        scope_start, scope_end = self._get_scope_range(source_code, offset, module_scope,
                                                       old_pyname.get_definition_location()[1])
        for match in pattern.finditer(source_code[scope_start:scope_end]):
            match_start = scope_start + match.start()
            match_end = scope_start + match.end()
            new_pyname = None
            try:
                new_pyname = pyname_finder.get_pyname_at(match_start + 1)
            except SyntaxError:
                pass
            if new_pyname == old_pyname:
                result.append(source_code[last_modified_char:match_start] + new_name)
                last_modified_char = match_end
        result.append(source_code[last_modified_char:])
        return ''.join(result)

    def _get_scope_range(self, source_code, offset, module_scope, lineno):
        lines = SourceLinesAdapter(source_code)
        scope_finder = HoldingScopeFinder(source_code)
        holding_scope = scope_finder.get_holding_scope(module_scope, lineno)
        range_finder = StatementRangeFinder(lines, lineno)
        range_finder.analyze()
        start = lines.get_line_start(holding_scope.get_lineno())
        end = lines.get_line_end(range_finder.get_scope_end()) + 1
        return (start, end)

class NoRefactoring(Refactoring):

    def rename(self, source_code, offset, new_name):
        return source_code

