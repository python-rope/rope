import re

from rope.codeanalyze import (WordRangeFinder, ScopeNameFinder,
                              StatementRangeFinder, SourceLinesAdapter)

class Refactoring(object):

    def local_rename(self, source_code, offset, new_name):
        """Returns the changed source_code or ``None`` if nothing has been changed"""
    
    def rename(self, resource, offset, new_name):
        pass


class PythonRefactoring(Refactoring):

    def __init__(self, pycore):
        self.pycore = pycore
        self.comment_pattern = PythonRefactoring.any("comment", [r"#[^\n]*"])
        sqstring = r"(\b[rR])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
        dqstring = r'(\b[rR])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
        sq3string = r"(\b[rR])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?"
        dq3string = r'(\b[rR])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?'
        self.string_pattern = PythonRefactoring.any("string",
                                                    [sq3string, dq3string, sqstring, dqstring])

    @staticmethod
    def any(name, list):
        return "(?P<%s>" % name + "|".join(list) + ")"

    def local_rename(self, source_code, offset, new_name):
        result = []
        module_scope = self.pycore.get_string_scope(source_code)
        word_finder = WordRangeFinder(source_code)
        old_name = word_finder.get_statement_at(offset).split('.')[-1]
        pyname_finder = ScopeNameFinder(source_code, module_scope)
        old_pyname = pyname_finder.get_pyname_at(offset)
        if old_pyname is None:
            return None
        pattern = self._get_occurance_pattern(old_name)
        last_modified_char = 0
        scope_start, scope_end = self._get_scope_range(source_code, offset, module_scope,
                                                       old_pyname.get_definition_location()[1])
        for match in pattern.finditer(source_code[scope_start:scope_end]):
            for key, value in match.groupdict().items():
                if value and key == "occurance":
                    match_start = scope_start + match.start(key)
                    match_end = scope_start + match.end(key)
                    new_pyname = None
                    try:
                        new_pyname = pyname_finder.get_pyname_at(match_start + 1)
                    except SyntaxError:
                        pass
                    if new_pyname == old_pyname:
                        result.append(source_code[last_modified_char:match_start] + new_name)
                        last_modified_char = match_end
        if last_modified_char == 0:
            return None
        result.append(source_code[last_modified_char:])
        return ''.join(result)
    
    def rename(self, resource, offset, new_name):
        module_scope = self.pycore.resource_to_pyobject(resource).get_scope()
        source_code = resource.read()
        word_finder = WordRangeFinder(source_code)
        old_name = word_finder.get_statement_at(offset).split('.')[-1]
        pyname_finder = ScopeNameFinder(source_code, module_scope)
        old_pyname = pyname_finder.get_pyname_at(offset)
        if old_pyname is None:
            return None
        pattern = self._get_occurance_pattern(old_name)
        changes = []
        for file_ in self.pycore.get_python_files():
            new_content = self._rename_occurance_in_file(file_, old_pyname, pattern, new_name)
            if new_content is not None:
                changes.append((file_, new_content))
        for file_, new_content in changes:
            file_.write(new_content)
    
    def _rename_occurance_in_file(self, resource, old_pyname, pattern, new_name):
        source_code = resource.read()
        result = []
        last_modified_char = 0
        pyname_finder = None
        for match in pattern.finditer(source_code):
            for key, value in match.groupdict().items():
                if value and key == "occurance":
                    match_start = match.start(key)
                    match_end = match.end(key)
                    if pyname_finder == None:
                        module_scope = self.pycore.resource_to_pyobject(resource).get_scope()
                        pyname_finder = ScopeNameFinder(source_code, module_scope)
                    new_pyname = pyname_finder.get_pyname_at(match_start + 1)
                    if self._are_pynames_the_same(old_pyname, new_pyname):
                        result.append(source_code[last_modified_char:match_start] + new_name)
                        last_modified_char = match_end
        if last_modified_char != 0:
            result.append(source_code[last_modified_char:])
            return ''.join(result)
        return None
    
    def _are_pynames_the_same(self, pyname1, pyname2):
        return pyname1 == pyname2 or \
               (pyname1 is not None and pyname2 is not None and 
                pyname1.get_object() == pyname2.get_object() and
                pyname1.get_definition_location() == pyname2.get_definition_location())
    
    def _get_occurance_pattern(self, name):
        occurance_pattern = PythonRefactoring.any('occurance', ['\\b' + name + '\\b'])
        pattern = re.compile(occurance_pattern + "|" + \
                             self.comment_pattern + "|" + self.string_pattern)
        return pattern

    def _get_scope_range(self, source_code, offset, module_scope, lineno):
        lines = SourceLinesAdapter(source_code)
        holding_scope = module_scope.get_inner_scope_for_line(lineno)
        range_finder = StatementRangeFinder(lines, lineno)
        range_finder.analyze()
        start = lines.get_line_start(holding_scope.get_start())
        end = lines.get_line_end(holding_scope.get_end()) + 1
        return (start, end)


class NoRefactoring(Refactoring):
    pass

