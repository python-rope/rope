import re

from rope.codeanalyze import LineOrientedSourceTools

class Refactoring(object):

    def rename(self, source_code, offset, new_name):
        pass


class PythonRefactoring(Refactoring):

    def __init__(self, pycore):
        self.pycore = pycore
    
    def _get_previous_char(self, lines, lineno, colno):
        colno -= 1
        while lineno >= 0 and (colno < 0 or lines[lineno][colno].isspace()):
            colno -= 1
            if colno < 0:
                lineno -= 1
                if lineno < 0:
                    break
                colno = len(lines[lineno]) - 1
                if lines[lineno][colno] == '\\':
                    colno -= 1
        if lineno > 0:
            return lines[lineno][colno]
        else:
            return ''
        
    def rename(self, source_code, offset, new_name):
        lines = source_code.split('\n')
        result = []
        line_tools = LineOrientedSourceTools(lines)
        module_scope = self.pycore.get_string_scope(source_code)
        old_name = line_tools.get_name_at(offset)
        old_pyname = self._get_pyname(module_scope, line_tools, old_name,
                                      line_tools.get_location(offset)[0])
        if old_pyname is None:
            return source_code
        pattern = re.compile('\\b' + old_name + '\\b')
        for lineno, line in enumerate(lines):
            new_line = ''
            last_modified_char = 0
            for match in pattern.finditer(line):
                if self._get_previous_char(lines, lineno, match.start()) == '.':
                    continue
                if self._get_pyname(module_scope, line_tools,
                                    old_name, lineno + 1) == old_pyname:
                    new_line += line[last_modified_char:match.start()] + new_name
                    last_modified_char = match.end()
            new_line += line[last_modified_char:]
            result.append(new_line)
        return '\n'.join(result)


    def _get_pyname(self, holding_scope, name):
        return holding_scope.lookup(name)

    def _get_pyname(self, module_scope, line_tools, name, lineno):
        holding_scope = line_tools.get_holding_scope(module_scope, lineno)
        result = holding_scope.lookup(name)
        # This occurs if renaming a function parameter
        if result is None:
            next_scope = line_tools.get_holding_scope(module_scope,
                                                      lineno + 1)
            result = next_scope.lookup(name)            
        return result


class NoRefactoring(Refactoring):

    def rename(self, source_code, offset, new_name):
        return source_code

