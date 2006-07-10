import re

from rope.codeanalyze import (WordRangeFinder, ScopeNameFinder)

class Refactoring(object):

    def rename(self, source_code, offset, new_name):
        pass


class PythonRefactoring(Refactoring):

    def __init__(self, pycore):
        self.pycore = pycore
    
    def _get_previous_char(self, source_code, offset):
        offset -= 1
        while offset >= 0 and source_code[offset].isspace():
            if source_code[offset] == '\n':
                offset -= 1
                if offset >= 0 and source_code[offset] == '\\':
                    offset -= 1
            offset -= 1
        if offset > 0:
            return source_code[offset]
        else:
            return ''
        
    def rename(self, source_code, offset, new_name):
        result = []
        module_scope = self.pycore.get_string_scope(source_code)
        word_finder = WordRangeFinder(source_code)
        old_name = '.'.join(word_finder.get_name_list_at(offset))
        pyname_finder = ScopeNameFinder(source_code, module_scope)
        old_pyname = pyname_finder.get_pyname_at(offset)
        if old_pyname is None:
            return source_code
        pattern = re.compile('\\b' + old_name + '\\b')
        last_modified_char = 0
        for match in pattern.finditer(source_code):
            if self._get_previous_char(source_code, match.start()) == '.':
                continue
            new_pyname = None
            try:
                new_pyname = pyname_finder.get_pyname_at(match.start() + 1)
            except SyntaxError:
                pass
            if new_pyname == old_pyname:
                result.append(source_code[last_modified_char:match.start()] + new_name)
                last_modified_char = match.end()
        result.append(source_code[last_modified_char:])
        return ''.join(result)


class NoRefactoring(Refactoring):

    def rename(self, source_code, offset, new_name):
        return source_code

