import compiler
import re

import rope.pycore


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
        return self.source_code[self._find_word_start(offset - 1):
                                self._find_word_end(offset - 1) + 1]
    
    def _find_string_start(self, offset):
        kind = self.source_code[offset]
        current_offset = offset - 1
        while self.source_code[current_offset] != kind:
            current_offset -= 1
        return current_offset
    
    def _find_parens_start(self, offset):
        current_offset = self._find_last_non_space_char(offset - 1)
        while current_offset >= 0 and self.source_code[current_offset] not in '[({':
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
        if self.source_code[offset] in ')]}':
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
            dot_position = self._find_last_non_space_char(current_offset - 1)
            current_offset = self._find_last_non_space_char(dot_position - 1)

            if self.source_code[current_offset].isalnum() or \
               self.source_code[current_offset] == '_':
                current_offset = self._find_word_start(current_offset)
            elif self.source_code[current_offset] in '\'"':
                current_offset = self._find_string_start(current_offset)
            elif self.source_code[current_offset] in ')]}':
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
    
    def get_statement_at(self, offset):
        return self.source_code[self._find_name_start(offset - 1):
                                self._find_word_end(offset - 1) + 1].strip()

    def get_splitted_statement_before(self, offset):
        """returns expression, starting, starting_offset
        
        This function is used in `rope.codeassist.assist` function.
        """
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


class StatementEvaluator(object):

    def __init__(self, scope):
        self.scope = scope
        self.result = None

    def visitName(self, node):
        self.result = self.scope.lookup(node.name)
    
    def visitGetattr(self, node):
        pyname = StatementEvaluator.get_statement_result(self.scope, node.expr)
        if pyname is not None:
            self.result = pyname.get_attributes().get(node.attrname, None)

    def visitCallFunc(self, node):
        pyname = StatementEvaluator.get_statement_result(self.scope, node.node)
        if pyname is None:
            return
        if pyname.get_type() == rope.pycore.PyObject.get_base_type('Type'):
            self.result = rope.pycore.PyName(object_=rope.pycore.PyObject(type_=pyname.get_object()))
        elif pyname.get_type() == rope.pycore.PyObject.get_base_type('Function'):
            self.result = rope.pycore.PyName(object_=pyname.get_object()._get_returned_object())
        elif '__call__' in pyname.get_object().get_attributes():
            call_function = pyname.get_object().get_attributes()['__call__']
            self.result = rope.pycore.PyName(object_=call_function.get_object()._get_returned_object())
    
    def visitAdd(self, node):
        pass

    def visitAnd(self, node):
        pass

    def visitBackquote(self, node):
        pass

    def visitBitand(self, node):
        pass

    def visitBitor(self, node):
        pass

    def visitXor(self, node):
        pass

    def visitCompare(self, node):
        pass
    
    def visitDict(self, node):
        pass
    
    def visitFloorDiv(self, node):
        pass
    
    def visitList(self, node):
        pass
    
    def visitListComp(self, node):
        pass

    def visitMul(self, node):
        pass
    
    def visitNot(self, node):
        pass
    
    def visitOr(self, node):
        pass
    
    def visitPower(self, node):
        pass
    
    def visitRightShift(self, node):
        pass
    
    def visitLeftShift(self, node):
        pass
    
    def visitSlice(self, node):
        pass
    
    def visitSliceobj(self, node):
        pass
    
    def visitTuple(self, node):
        pass
    
    def visitSubscript(self, node):
        pass

    @staticmethod
    def get_statement_result(scope, node):
        evaluator = StatementEvaluator(scope)
        compiler.walk(node, evaluator)
        return evaluator.result


class ScopeNameFinder(object):
    
    def __init__(self, source_code, module_scope):
        self.source_code = source_code
        self.module_scope = module_scope
        self.lines = source_code.split('\n')
        self.word_finder = WordRangeFinder(source_code)

    def _get_location(self, offset):
        lines = ArrayLinesAdapter(self.lines)
        current_pos = 0
        lineno = 1
        while current_pos + len(lines.get_line(lineno)) < offset:
            current_pos += len(lines.get_line(lineno)) + 1
            lineno += 1
        return (lineno, offset - current_pos)

    def get_pyname_at(self, offset):
        name = self.word_finder.get_statement_at(offset)
        lineno = self._get_location(offset)[0]
        holding_scope = self.module_scope.get_inner_scope_for_line(lineno)
        result = self.get_pyname_in_scope(holding_scope, name)
        return result
    
    def get_pyname_in_scope(self, holding_scope, name):
        ast = compiler.parse(name)
        result = StatementEvaluator.get_statement_result(holding_scope, ast)
        return result


class Lines(object):

    def get_line(self, line_number):
        pass

    def length(self):
        pass


class SourceLinesAdapter(Lines):
    
    def __init__(self, source_code):
        self.source_code = source_code
        self.line_starts = None
        self._initialize_line_starts()
    
    def _initialize_line_starts(self):
        self.line_starts = []
        self.line_starts.append(0)
        for i, c in enumerate(self.source_code):
            if c == '\n':
                self.line_starts.append(i + 1)
        self.line_starts.append(len(self.source_code) + 1)
    
    def get_line(self, line_number):
        return self.source_code[self.line_starts[line_number - 1]:self.line_starts[line_number] - 1]
    
    def length(self):
        return len(self.line_starts) - 1

    def get_line_number(self, offset):
        down = 0
        up = len(self.line_starts)
        current = (down + up) / 2
        while down <= current < up:
            if self.line_starts[current] <= offset < self.line_starts[current + 1]:
                return current + 1
            if offset < self.line_starts[current]:
                up = current - 1
            else:
                down = current + 1
            current = (down + up) / 2
        return current + 1

    def get_line_start(self, line_number):
        return self.line_starts[line_number - 1]

    def get_line_end(self, line_number):
        return self.line_starts[line_number] - 1


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
        for i, char in enumerate(current_line):
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

    def _get_block_start(self):
        """Aproximating block start for `analyze` method"""
        pattern = StatementRangeFinder.get_block_start_patterns()
        for i in reversed(range(1, self.lineno + 1)):
            if pattern.search(self.lines.get_line(i)) is not None:
                return i
        return 1

    def analyze(self):
        last_statement = 1
        for current_line_number in range(self._get_block_start(), self.lineno + 1):
            if not self.explicit_continuation and self.open_parens == 0 and self.in_string == '':
                last_statement = current_line_number
            self._analyze_line(current_line_number)
        last_indents = self.get_line_indents(last_statement)
        end_line = self.lineno
        for i in range(self.lineno + 1, self.lines.length() + 1):
            if self.get_line_indents(i) >= last_indents:
                end_line = i
            else:
                break
        self.block_end = end_line
        self.statement_start = last_statement

    def get_statement_start(self):
        return self.statement_start

    def get_block_end(self):
        return self.block_end

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
    
    @classmethod
    def get_block_start_patterns(cls):
        if not hasattr(cls, '__block_start_pattern'):
            pattern = '^\\s*(def|class|if|else|elif|try|except|for|while|with)\\s'
            cls.__block_start_pattern = re.compile(pattern, re.M)
        return cls.__block_start_pattern

