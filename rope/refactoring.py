import re

from rope.codeanalyze import LineOrientedSourceTools

class Refactoring(object):

    def __init__(self, pycore):
        self.pycore = pycore
    
    def rename(self, source_code, offset, new_name):
        lines = source_code.split('\n')
        result = []
        line_tools = LineOrientedSourceTools(lines)
        module_scope = self.pycore.get_string_scope(source_code)
        holding_scope = line_tools.get_holding_scope(module_scope,
                                                     line_tools.get_location(offset)[0])
        old_name = line_tools.get_name_at(offset)
        old_pyname = self._get_pyname(holding_scope, old_name)
        pattern = re.compile('\\b' + old_name + '\\b')
        for lineno, line in enumerate(lines):
            line_scope = line_tools.get_holding_scope(module_scope, lineno + 1)
            new_line = ''
            last_modified_char = 0
            for match in pattern.finditer(line):
                if match.start() != 0 and line[match.start() - 1] == '.':
                    continue
                if self._get_pyname(line_scope, old_name) == old_pyname:
                    new_line += line[last_modified_char:match.start()] + new_name
                    last_modified_char = match.end()
            new_line += line[last_modified_char:]
            result.append(new_line)
        return '\n'.join(result)


    def _get_pyname(self, holding_scope, name):
        return holding_scope.lookup(name)

