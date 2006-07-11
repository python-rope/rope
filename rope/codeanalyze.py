import compiler

class WordRangeFinder(object):

    def __init__(self, source_code):
        self.source_code = source_code
    
    def _find_word_start(self, offset):
        current_offset = offset
        while current_offset >= 0 and (self.source_code[current_offset].isalnum() or
                                       self.source_code[current_offset] in '_'):
            current_offset -= 1;
        return current_offset + 1
    
    def _find_word_end(self, offset):
        current_offset = offset + 1
        while current_offset < len(self.source_code) and \
              (self.source_code[current_offset].isalnum() or
               self.source_code[current_offset] in '_'):
            current_offset += 1;
        return current_offset - 1

    def _find_last_non_space_char(self, offset):
        current_offset = offset
        while current_offset >= 0 and self.source_code[current_offset] in ' \t\n':
            while current_offset >= 0 and self.source_code[current_offset] in ' \t':
                current_offset -= 1
            if current_offset >= 0 and self.source_code[current_offset] == '\n':
                current_offset -= 1
                if current_offset >= 0 and self.source_code[current_offset] == '\\':
                    current_offset -= 1
        return current_offset
    
    def get_word_before(self, offset):
        return self.source_code[self._find_word_start(offset - 1):offset]
    
    def get_word_at(self, offset):
        return self.source_code[self._find_word_start(offset - 1):self._find_word_end(offset - 1) + 1]
    
    def _find_string_start(self, offset):
        kind = self.source_code[offset]
        current_offset = offset - 1
        while self.source_code[current_offset] != kind:
            current_offset -= 1
        return current_offset
    
    def _find_parens_start(self, offset):
        current_offset = self._find_last_non_space_char(offset - 1)
        while current_offset >= 0 and self.source_code[current_offset] not in '[(':
            if self.source_code[current_offset] in ':,':
                pass
            else:
                current_offset = self._find_name_start(current_offset)
            current_offset = self._find_last_non_space_char(current_offset - 1)
        return current_offset

    def _find_atom_start(self, offset):
        old_offset = offset
        if self.source_code[offset] in '\n\t ':
            offset = self._find_last_non_space_char(offset)
        if self.source_code[offset] in '\'"':
            return self._find_string_start(offset)
        if self.source_code[offset] in ')]':
            return self._find_parens_start(offset)
        if self.source_code[offset].isalnum() or self.source_code[offset] == '_':
            return self._find_word_start(offset)
        return old_offset

    def _find_name_start(self, offset):
        current_offset = offset + 1
        if self.source_code[offset] != '.':
            current_offset = self._find_atom_start(offset)
        while current_offset > 0 and \
              self.source_code[self._find_last_non_space_char(current_offset - 1)] == '.':
            current_offset = self._find_last_non_space_char(current_offset - 1)
            current_offset = self._find_last_non_space_char(current_offset - 1)
            if self.source_code[current_offset].isalnum() or self.source_code[current_offset] == '_':
                current_offset = self._find_word_start(current_offset)
            elif self.source_code[current_offset] in '\'"':
                current_offset = self._find_string_start(current_offset)
            elif self.source_code[current_offset] in ')]':
                current_offset = self._find_parens_start(current_offset)
                if current_offset == 0:
                    break
                current_offset = self._find_last_non_space_char(current_offset - 1)
                if self.source_code[current_offset].isalnum() or \
                   self.source_code[current_offset] == '_':
                    current_offset = self._find_word_start(current_offset)
                else:
                    break
        return current_offset
    
    def get_name_at(self, offset):
        return self.source_code[self._find_name_start(offset - 1):
                                self._find_word_end(offset - 1) + 1].strip()

    def get_splitted_name_before(self, offset):
        """returns expression, starting, starting_offset"""
        if offset == 0:
            return ('', '', 0)
        word_start = self._find_atom_start(offset - 1)
        real_start = self._find_name_start(offset - 1)
        if self.source_code[word_start:offset].strip() == '':
            word_start = offset
        if self.source_code[real_start:offset].strip() == '':
            real_start = offset
        if real_start == word_start:
            return ('', self.source_code[word_start:offset], word_start)
        else:
            if self.source_code[offset - 1] == '.':
                return (self.source_code[real_start:offset - 1], '', offset)
            last_dot_position = word_start
            if self.source_code[word_start] != '.':
                last_dot_position = self._find_last_non_space_char(word_start - 1)
            last_char_position = self._find_last_non_space_char(last_dot_position - 1)
            return (self.source_code[real_start:last_char_position + 1],
                    self.source_code[word_start:offset], word_start)
        


class HoldingScopeFinder(object):

    def __init__(self, source_code):
        self.source_code = source_code
        self.lines = SourceLinesAdapter(source_code)
    
    def get_indents(self, lineno):
        indents = 0
        for char in self.lines.get_line(lineno):
            if char == ' ':
                indents += 1
            else:
                break
        return indents
    
    def get_location(self, offset):
        current_pos = 0
        lineno = 1
        while current_pos + len(self.lines.get_line(lineno)) < offset:
            current_pos += len(self.lines.get_line(lineno)) + 1
            lineno += 1
        return (lineno, offset - current_pos)

    def get_holding_scope(self, module_scope, lineno, line_indents=None):
        line_indents = line_indents
        if line_indents is None:
            line_indents = self.get_indents(lineno)
        scopes = [(module_scope, 0)]
        current_scope = module_scope
        while current_scope is not None and \
              (current_scope.get_kind() == 'Module' or
               self.get_indents(current_scope.get_lineno()) < line_indents):
            while len(scopes) > 1 and scopes[-1][1] >= self.get_indents(current_scope.get_lineno()):
                scopes.pop()
            scopes.append((current_scope, self.get_indents(current_scope.get_lineno())))
            new_scope = None
            for scope in current_scope.get_scopes():
                if scope.get_lineno() <= lineno:
                    new_scope = scope
                else:
                    break
            current_scope = new_scope
        min_indents = line_indents
        for l in range(scopes[-1][0].get_lineno() + 1, lineno):
            if self.lines.get_line(l).strip() != '' and \
               not self.lines.get_line(l).strip().startswith('#'):
                min_indents = min(min_indents, self.get_indents(l))
        while len(scopes) > 1 and min_indents <= scopes[-1][1]:
            scopes.pop()
        return scopes[-1][0]


class _StatementEvaluator(object):

    def __init__(self, scope):
        self.scope = scope
        self.result = None

    def visitName(self, node):
        self.result = self.scope.lookup(node.name)
    
    def visitGetattr(self, node):
        pyname = _StatementEvaluator.get_statement_result(self.scope, node.expr)
        if pyname is not None:
            self.result = pyname.get_attributes().get(node.attrname, None)

    @staticmethod
    def get_statement_result(scope, node):
        evaluator = _StatementEvaluator(scope)
        compiler.walk(node, evaluator)
        return evaluator.result


class ScopeNameFinder(object):
    
    def __init__(self, source_code, module_scope):
        self.source_code = source_code
        self.module_scope = module_scope
        self.lines = source_code.split('\n')
        self.scope_finder = HoldingScopeFinder(source_code)
        self.word_finder = WordRangeFinder(source_code)
    
    def get_pyname_at(self, offset):
        name = self.word_finder.get_name_at(offset)
        lineno = self.scope_finder.get_location(offset)[0]
        holding_scope = self.scope_finder.get_holding_scope(self.module_scope, lineno)
        result = self.get_pyname_in_scope(holding_scope, name)
        # This occurs if renaming a function parameter
        if result is None and lineno < len(self.lines):
            next_scope = self.scope_finder.get_holding_scope(self.module_scope, lineno + 1)
            result = self.get_pyname_in_scope(next_scope, name)
        return result
    
    def get_pyname_in_scope(self, holding_scope, name):
        ast = compiler.parse(name)
        result = _StatementEvaluator.get_statement_result(holding_scope, ast)
        return result



class Lines(object):

    def get_line(self, line_number):
        pass

    def length(self):
        pass


class SourceLinesAdapter(Lines):
    
    def __init__(self, source_code):
        self.source_code = source_code
    
    def get_line(self, line_number):
        return self.source_code.split('\n')[line_number - 1]
    
    def length(self):
        return len(self.source_code.split('\n'))

    def get_line_number(self, offset):
        return len(self.source_code[:offset].split('\n'))

    
class ArrayLinesAdapter(Lines):

    def __init__(self, lines):
        self.lines = lines
    
    def get_line(self, line_number):
        return self.lines[line_number - 1]
    
    def length(self):
        return len(self.lines)


class StatementRangeFinder(object):
    """A method object for finding the range of a statement"""

    def __init__(self, lines, lineno):
        self.lines = lines
        self.lineno = lineno
        self.in_string = ''
        self.open_parens = 0
        self.explicit_continuation = False
        self.parens_openings = []

    def _analyze_line(self, current_line_number):
        current_line = self.lines.get_line(current_line_number)
        for i in range(len(current_line)):
            char = current_line[i]
            if char in '\'"':
                if self.in_string == '':
                    self.in_string = char
                    if char * 3 == current_line[i:i + 3]:
                        self.in_string = char * 3
                elif self.in_string == current_line[i:i + len(self.in_string)] and \
                     not (i > 0 and current_line[i - 1] == '\\' and
                          not (i > 1 and current_line[i - 2:i] == '\\\\')):
                    self.in_string = ''
            if self.in_string != '':
                continue
            if char == '#':
                break
            if char in '([{':
                self.open_parens += 1
                self.parens_openings.append((current_line_number, i))
            if char in ')]}':
                self.open_parens -= 1
                if self.parens_openings:
                    self.parens_openings.pop()
        if current_line.rstrip().endswith('\\'):
            self.explicit_continuation = True
        else:
            self.explicit_continuation = False


    def analyze(self):
        last_statement = 1
        for current_line_number in range(1, self.lineno + 1):
            if not self.explicit_continuation and self.open_parens == 0 and self.in_string == '':
                last_statement = current_line_number
            self._analyze_line(current_line_number)
        last_indents = self.get_line_indents(last_statement)
        end_line = self.lineno
        if True or self.lines.get_line(self.lineno).rstrip().endswith(':'):
            for i in range(self.lineno + 1, self.lines.length() + 1):
                if self.get_line_indents(i) >= last_indents:
                    end_line = i
                else:
                    break
        self.scope_end = end_line
        self.statement_start = last_statement

    def get_statement_start(self):
        return self.statement_start

    def get_scope_end(self):
        return self.scope_end

    def last_open_parens(self):
        if not self.parens_openings:
            return None
        return self.parens_openings[-1]

    def is_line_continued(self):
        return self.open_parens != 0 or self.explicit_continuation

    def get_line_indents(self, line_number):
        indents = 0
        for char in self.lines.get_line(line_number):
            if char == ' ':
                indents += 1
            else:
                break
        return indents

