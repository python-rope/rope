import re
import tokenize
import token

import rope.base.pyobjects
import rope.base.pynames
from rope.base import pyobjects, pynames
import rope.base.exceptions
from rope.base import ast, builtins, evaluate


class WordRangeFinder(object):

    def __init__(self, source_code):
        self.source_code = source_code

    def _find_word_start(self, offset):
        current_offset = offset
        while current_offset >= 0 and self._is_id_char(current_offset):
            current_offset -= 1;
        return current_offset + 1

    def _find_word_end(self, offset):
        current_offset = offset + 1
        while current_offset < len(self.source_code) and \
              self._is_id_char(current_offset):
            current_offset += 1;
        return current_offset - 1

    def _find_last_non_space_char(self, offset):
        if offset <= 0:
            return 0
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
        offset = self._get_fixed_offset(offset)
        return self.source_code[self._find_word_start(offset):
                                self._find_word_end(offset) + 1]

    def _get_fixed_offset(self, offset):
        if offset >= len(self.source_code):
            return offset - 1
        if not self._is_id_char(offset):
            if offset > 0 and self._is_id_char(offset - 1):
                return offset - 1
            if offset < len(self.source_code) - 1 and self._is_id_char(offset + 1):
                return offset + 1
        return offset

    def _is_id_char(self, offset):
        return self.source_code[offset].isalnum() or self.source_code[offset] == '_'

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
                current_offset = self._find_primary_start(current_offset)
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
        if self._is_id_char(offset):
            return self._find_word_start(offset)
        return old_offset

    def _find_primary_without_dot_start(self, offset):
        last_parens = offset
        current_offset = self._find_last_non_space_char(offset)
        while current_offset > 0 and self.source_code[current_offset] in ')]}':
            last_parens = self._find_parens_start(current_offset)
            current_offset = self._find_last_non_space_char(last_parens - 1)
        if self.source_code[last_parens] == '(' and self._is_id_char(current_offset):
            return self._find_primary_without_dot_start(current_offset)


        if current_offset > 0 and self.source_code[current_offset] in '\'"':
            return self._find_string_start(current_offset)
        elif current_offset > 0 and self._is_id_char(current_offset):
            return self._find_word_start(current_offset)
        return last_parens

    def _find_primary_start(self, offset):
        if offset >= len(self.source_code):
            offset = len(self.source_code) - 1
        current_offset = offset + 1
        if self.source_code[offset] != '.':
            current_offset = self._find_primary_without_dot_start(offset)
        while current_offset > 0 and \
              self.source_code[self._find_last_non_space_char(current_offset - 1)] == '.':
            dot_position = self._find_last_non_space_char(current_offset - 1)
            current_offset = self._find_primary_without_dot_start(dot_position - 1)

            if not self._is_id_char(current_offset):
                break

        return current_offset

    def get_primary_at(self, offset):
        offset = self._get_fixed_offset(offset)
        return self.source_code[self._find_primary_start(offset):
                                self._find_word_end(offset) + 1].strip()

    def get_splitted_primary_before(self, offset):
        """returns expression, starting, starting_offset

        This function is used in `rope.codeassist.assist` function.
        """
        if offset == 0:
            return ('', '', 0)
        end = offset - 1
        word_start = self._find_atom_start(end)
        real_start = self._find_primary_start(end)
        if self.source_code[word_start:offset].strip() == '':
            word_start = end
        if self.source_code[real_start:word_start].strip() == '':
            real_start = word_start
        if real_start == word_start == end and not self._is_id_char(end):
            return ('', '', offset)
        if real_start == word_start:
            return ('', self.source_code[word_start:offset], word_start)
        else:
            if self.source_code[end] == '.':
                return (self.source_code[real_start:end], '', offset)
            last_dot_position = word_start
            if self.source_code[word_start] != '.':
                last_dot_position = self._find_last_non_space_char(word_start - 1)
            last_char_position = self._find_last_non_space_char(last_dot_position - 1)
            return (self.source_code[real_start:last_char_position + 1],
                    self.source_code[word_start:offset], word_start)

    def _get_line_start(self, offset):
        while offset > 0 and self.source_code[offset] != '\n':
            offset -= 1
        return offset

    def _get_line_end(self, offset):
        while offset < len(self.source_code) and self.source_code[offset] != '\n':
            offset += 1
        return offset

    def _is_followed_by_equals(self, offset):
        while offset < len(self.source_code) and self.source_code[offset] in ' \\':
            if self.source_code[offset] == '\\':
                offset = self._get_line_end(offset)
            offset += 1
        if offset + 1 < len(self.source_code) and \
           self.source_code[offset] == '=' and self.source_code[offset + 1] != '=':
            return True
        return False

    def _is_name_assigned_in_class_body(self, offset):
        word_start = self._find_word_start(offset - 1)
        word_end = self._find_word_end(offset - 1) + 1
        if '.' in self.source_code[word_start:word_end]:
            return False
        line_start = self._get_line_start(word_start)
        line = self.source_code[line_start:word_start].strip()
        if line == '' and self._is_followed_by_equals(word_end):
            return True
        return False

    def is_a_class_or_function_name_in_header(self, offset):
        word_start = self._find_word_start(offset - 1)
        word_end = self._find_word_end(offset - 1) + 1
        line_start = self._get_line_start(word_start)
        prev_word = self.source_code[line_start:word_start].strip()
        return prev_word in ['def', 'class']

    def _find_first_non_space_char(self, offset):
        if offset >= len(self.source_code):
            return len(self.source_code)
        current_offset = offset
        while current_offset < len(self.source_code) and\
              self.source_code[current_offset] in ' \t\n':
            while current_offset < len(self.source_code) and \
                  self.source_code[current_offset] in ' \t\n':
                current_offset += 1
            if current_offset + 1 < len(self.source_code) and \
               self.source_code[current_offset] == '\\':
                current_offset += 2
        return current_offset

    def is_a_function_being_called(self, offset):
        word_start = self._find_word_start(offset - 1)
        word_end = self._find_word_end(offset - 1) + 1
        next_char = self._find_first_non_space_char(word_end)
        return next_char < len(self.source_code) and \
               self.source_code[next_char] == '(' and \
               not self.is_a_class_or_function_name_in_header(offset)
               

    def _find_import_pair_end(self, start):
        next_char = self._find_first_non_space_char(start)
        if self.source_code[next_char] == '(':
            try:
                return self.source_code.index(')', next_char) + 1
            except ValueError:
                return SyntaxError('Unmatched Parens')
        else:
            current_offset = next_char
            while current_offset < len(self.source_code):
                if self.source_code[current_offset] == '\n':
                    break
                if self.source_code[current_offset] == '\\':
                    current_offset += 1
                current_offset += 1
            return current_offset

    def is_import_statement(self, offset):
        try:
            last_import = self.source_code.rindex('import ', 0, offset)
        except ValueError:
            return False
        return self._find_import_pair_end(last_import + 7) >= offset

    def is_from_statement(self, offset):
        try:
            last_from = self.source_code.rindex('from ', 0, offset)
            from_import = self.source_code.index(' import ', last_from)
            from_names = from_import + 8
        except ValueError:
            return False
        return self._find_import_pair_end(from_names) >= offset

    def is_from_statement_module(self, offset):
        if offset >= len(self.source_code) - 1:
            return False
        stmt_start = self._find_primary_start(offset)
        line_start = self._get_line_start(stmt_start)
        prev_word = self.source_code[line_start:stmt_start].strip()
        return prev_word == 'from'

    def is_a_name_after_from_import(self, offset):
        try:
            last_from = self.source_code.rindex('from ', 0, offset)
            from_import = self.source_code.index(' import ', last_from)
            from_names = from_import + 8
        except ValueError:
            return False
        if from_names >= offset:
            return False
        return self._find_import_pair_end(from_names) >= offset

    def is_function_keyword_parameter(self, offset):
        word_end = self._find_word_end(offset)
        if word_end + 1 == len(self.source_code):
            return False
        next_char = self._find_first_non_space_char(word_end + 1)
        if next_char + 2 >= len(self.source_code) or \
           self.source_code[next_char] != '=' or \
           self.source_code[next_char + 1] == '=':
            return False
        word_start = self._find_word_start(offset)
        prev_char = self._find_last_non_space_char(word_start - 1)
        if prev_char - 1 < 0 or self.source_code[prev_char] not in ',(':
            return False
        return True

    def is_on_function_call_keyword(self, offset, stop_searching=0):
        current_offset = offset
        if self._is_id_char(current_offset):
            current_offset = self._find_word_start(current_offset) - 1
        current_offset = self._find_last_non_space_char(current_offset)
        if current_offset <= stop_searching or \
           self.source_code[current_offset] not in '(,':
            return False
        parens_start = self.find_parens_start_from_inside(offset, stop_searching)
        if stop_searching < parens_start:
            return True
        return False

    def find_parens_start_from_inside(self, offset, stop_searching=0):
        current_offset = offset
        opens = 1
        while current_offset > stop_searching:
            if self.source_code[current_offset] == '(':
                opens -= 1
            if opens == 0:
                break
            if self.source_code[current_offset] == ')':
                opens += 1
            current_offset -= 1
        return current_offset

    def is_assigned_here(self, offset):
        operation = self.get_assignment_type(offset)
        operations = ('=', '-=', '+=', '*=', '/=', '%=', '**=',
                      '>>=', '<<=', '&=', '^=', '|=')
        return operation in operations

    def get_assignment_type(self, offset):
        word_end = self._find_word_end(offset)
        next_char = self._find_first_non_space_char(word_end + 1)
        current_char = next_char
        while current_char + 1 < len(self.source_code) and \
              (self.source_code[current_char] != '=' or \
               self.source_code[current_char + 1] == '=') and \
              current_char < next_char + 3:
            current_char += 1
        operation = self.source_code[next_char:current_char + 1]
        return operation

    def get_primary_range(self, offset):
        offset = max(0, offset - 1)
        start = self._find_primary_start(offset)
        end = self._find_word_end(offset) + 1
        return (start, end)

    def get_word_range(self, offset):
        offset = max(0, offset - 1)
        start = self._find_word_start(offset)
        end = self._find_word_end(offset) + 1
        return (start, end)

    def get_word_parens_range(self, offset):
        if self.is_a_function_being_called(offset) or \
           self.is_a_class_or_function_name_in_header(offset):
            end = self._find_word_end(offset)
            start_parens = self.source_code.index('(', end)
            index = start_parens
            open_count = 0
            while index < len(self.source_code):
                if self.source_code[index] == '(':
                    open_count += 1
                if self.source_code[index] == ')':
                    open_count -= 1
                if open_count == 0:
                    return (start_parens, index + 1)
                index += 1
            return (start_parens, index)
        return (None, None)


class ScopeNameFinder(object):

    def __init__(self, pymodule):
        self.source_code = pymodule.source_code
        self.module_scope = pymodule.get_scope()
        self.lines = SourceLinesAdapter(self.source_code)
        self.word_finder = WordRangeFinder(self.source_code)

    def _is_defined_in_class_body(self, holding_scope, offset, lineno):
        if lineno == holding_scope.get_start() and \
           holding_scope.parent is not None and \
           holding_scope.parent.get_kind() == 'Class' and \
           self.word_finder.is_a_class_or_function_name_in_header(offset):
            return True
        if lineno != holding_scope.get_start() and \
           holding_scope.get_kind() == 'Class' and \
           self.word_finder._is_name_assigned_in_class_body(offset):
            return True
        return False

    def _is_function_name_in_function_header(self, holding_scope, offset, lineno):
        if lineno == holding_scope.get_start() and \
           holding_scope.get_kind() == 'Function' and \
           self.word_finder.is_a_class_or_function_name_in_header(offset):
            return True
        return False

    def get_pyname_at(self, offset):
        return self.get_primary_and_pyname_at(offset)[1]

    def get_primary_and_pyname_at(self, offset):
        lineno = self.lines.get_line_number(offset)
        holding_scope = self.module_scope.get_inner_scope_for_line(lineno)
        # function keyword parameter
        if self.word_finder.is_function_keyword_parameter(offset):
            keyword_name = self.word_finder.get_word_at(offset)
            pyobject = self.get_enclosing_function(offset)
            if isinstance(pyobject, pyobjects.PyFunction):
                return (None, pyobject.get_parameters().get(keyword_name, None))

        # class body
        if self._is_defined_in_class_body(holding_scope, offset, lineno):
            class_scope = holding_scope
            if lineno == holding_scope.get_start():
                class_scope = holding_scope.parent
            name = self.word_finder.get_primary_at(offset).strip()
            try:
                return (None, class_scope.pyobject.get_attribute(name))
            except rope.base.exceptions.AttributeNotFoundError:
                return (None, None)
        # function header
        if self._is_function_name_in_function_header(holding_scope, offset, lineno):
            name = self.word_finder.get_primary_at(offset).strip()
            return (None, holding_scope.parent.get_name(name))
        # from statement module
        if self.word_finder.is_from_statement_module(offset):
            module = self.word_finder.get_primary_at(offset)
            module_pyname = self._find_module(module)
            return (None, module_pyname)
        name = self.word_finder.get_primary_at(offset)
        return self.get_primary_and_pyname_in_scope(holding_scope, name)

    def get_enclosing_function(self, offset):
        function_parens = self.word_finder.find_parens_start_from_inside(offset)
        try:
            function_pyname = self.get_pyname_at(function_parens - 1)
        except BadIdentifierError:
            function_pyname = None
        if function_pyname is not None:
            pyobject = function_pyname.get_object()
            if isinstance(pyobject, pyobjects.AbstractFunction):
                return pyobject
            elif isinstance(pyobject, pyobjects.AbstractClass) and \
                 '__init__' in pyobject.get_attributes():
                return pyobject.get_attribute('__init__').get_object()
            elif '__call__' in pyobject.get_attributes():
                return pyobject.get_attribute('__call__').get_object()
        return None

    def _find_module(self, module_name):
        current_folder = None
        if self.module_scope.pyobject.get_resource():
            current_folder = self.module_scope.pyobject.get_resource().parent
        dot_count = 0
        if module_name.startswith('.'):
            for c in module_name:
                if c == '.':
                    dot_count += 1
                else:
                    break
        return rope.base.pynames.ImportedModule(
            self.module_scope.pyobject, module_name[dot_count:], dot_count)

    @staticmethod
    def get_pyname_in_scope(holding_scope, name):
        return ScopeNameFinder.get_primary_and_pyname_in_scope(
            holding_scope, name)[1]

    # XXX: This might belong to `rope.base.evaluate` module
    @staticmethod
    def get_primary_and_pyname_in_scope(holding_scope, name):
        try:
            # parenthesizing for handling cases like 'a_var.\nattr'
            node = ast.parse('(%s)' % name)
        except SyntaxError:
            raise BadIdentifierError('Not a python identifier selected.')
        return evaluate.get_primary_and_result(holding_scope, node)


class BadIdentifierError(rope.base.exceptions.RopeError):
    pass


def get_pyname_at(pycore, resource, offset):
    """Finds the pyname at the offset

    This function is inefficient for multiple calls because of the
    recalculation of initialization data.
    """
    return get_primary_and_pyname_at(pycore, resource, offset)[1]

def get_primary_and_pyname_at(pycore, resource, offset):
    """Finds the primary and pyname at offset

    See notes about `get_pyname_at`.
    """
    pymodule = pycore.resource_to_pyobject(resource)
    pyname_finder = rope.base.codeanalyze.ScopeNameFinder(pymodule)
    return pyname_finder.get_primary_and_pyname_at(offset)

def get_name_at(resource, offset):
    source_code = resource.read()
    word_finder = rope.base.codeanalyze.WordRangeFinder(source_code)
    name = word_finder.get_primary_at(offset).split('.')[-1]
    return name


class Lines(object):

    def get_line(self, line_number):
        pass

    def length(self):
        pass


class SourceLinesAdapter(Lines):
    """Adapts source_code to Lines interface

    Note: The creation of this class is expensive.
    """

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
        return self.source_code[self.line_starts[line_number - 1]:
                                self.line_starts[line_number] - 1]

    def length(self):
        return len(self.line_starts) - 1

    def get_line_number(self, offset):
        down = 0
        up = len(self.line_starts)
        current = (down + up) // 2
        while down <= current < up:
            if self.line_starts[current] <= offset < self.line_starts[current + 1]:
                return current + 1
            if offset < self.line_starts[current]:
                up = current - 1
            else:
                down = current + 1
            current = (down + up) // 2
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


class LinesToReadline(object):

    def __init__(self, lines, start):
        self.lines = lines
        self.current = start

    def readline(self):
        if self.current <= self.lines.length():
            self.current += 1
            return self.lines.get_line(self.current - 1) + '\n'
        return ''

    def __call__(self):
        return self.readline()


class LogicalLineFinder(object):

    def __init__(self, lines):
        self.lines = lines

    def get_logical_line_in(self, line_number):
        block_start = get_block_start(
            self.lines, line_number,
            count_line_indents(self.lines.get_line(line_number)))
        readline = LinesToReadline(self.lines, block_start)
        last_line_start = block_start
        for current in tokenize.generate_tokens(readline):
            current_lineno = current[2][0] + block_start - 1
            if current[0] == token.NEWLINE:
                if current_lineno >= line_number:
                    return (self._get_first_non_empty_line(last_line_start),
                            current_lineno)
                last_line_start = current_lineno + 1
        return (last_line_start, self.lines.length())

    def _get_first_non_empty_line(self, line_number):
        current = line_number
        while current <= self.lines.length():
            line = self.lines.get_line(current)
            if line.strip() != '' and not line.startswith('#'):
                return current
            current += 1
        return current


class StatementRangeFinder(object):
    """A method object for finding the range of a statement"""

    def __init__(self, lines, lineno):
        self.lines = lines
        self.lineno = lineno
        self.in_string = ''
        self.open_count = 0
        self.explicit_continuation = False
        self.open_parens = []
        self._analyze()

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
                self.open_count += 1
                self.open_parens.append((current_line_number, i))
            if char in ')]}':
                self.open_count -= 1
                if self.open_parens:
                    self.open_parens.pop()
        if current_line.rstrip().endswith('\\'):
            self.explicit_continuation = True
        else:
            self.explicit_continuation = False

    def _analyze(self):
        last_statement = 1
        for current_line_number in range(get_block_start(self.lines,
                                                         self.lineno),
                                         self.lineno + 1):
            if not self.explicit_continuation and self.open_count == 0 and self.in_string == '':
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
        if not self.open_parens:
            return None
        return self.open_parens[-1]

    def is_line_continued(self):
        return self.open_count != 0 or self.explicit_continuation

    def get_line_indents(self, line_number):
        return count_line_indents(self.lines.get_line(line_number))

    _block_start_pattern = None


def get_block_start(lines, lineno, maximum_indents=80):
    """Aproximate block start"""
    pattern = get_block_start_patterns()
    for i in range(lineno, 0, -1):
        match = pattern.search(lines.get_line(i))
        if match is not None and \
           count_line_indents(lines.get_line(i)) <= maximum_indents:
            striped = match.string.lstrip()
            # Maybe we're in a list comprehension or generator expression
            if i > 1 and striped.startswith('if') or striped.startswith('for'):
                bracs = 0
                for j in range(i, min(i + 5, lines.length() + 1)):
                    for c in lines.get_line(j):
                        if c == '#':
                            break
                        if c in '[(':
                            bracs += 1
                        if c in ')]':
                            bracs -= 1
                            if bracs < 0:
                                break
                    if bracs < 0:
                        break
                if bracs < 0:
                    continue
            return i
    return 1

def get_block_start_patterns():
    if not StatementRangeFinder._block_start_pattern:
        pattern = '^\\s*(((def|class|if|elif|except|for|while|with)\\s)|'\
                  '((try|else|finally|except)\\s*:))'
        StatementRangeFinder._block_start_pattern = re.compile(pattern, re.M)
    return StatementRangeFinder._block_start_pattern


# XXX: Should we use it
class xxxStatementRangeFinder(object):
    """A method object for finding the range of a statement"""

    def __init__(self, lines, lineno):
        self.lines = lines
        self.lineno = lineno
        self.block_start = StatementRangeFinder.get_block_start(lines, lineno)
        self.open_parens = []
        self.statement_start = self.block_start
        self.block_end = lineno
        self.continued = True

    def analyze(self):
        readline = LinesToReadline(self.lines, self.block_start)
        try:
            for current in tokenize.generate_tokens(readline):
                current_lineno = current[2][0] + self.block_start - 1
                if current_lineno < self.lineno:
                    if current[0] == token.NEWLINE:
                        self.statement_start = current_lineno + 1
                if current_lineno <= self.lineno:
                    if current[0] == token.OP and current[1] in '([{':
                        self.open_parens.append((current_lineno, current[2][1]))
                    if current[0] == token.OP and current[1] in ')]}':
                        self.open_parens.pop()

                if current_lineno == self.lineno:
                    if current[0] in (tokenize.NEWLINE, tokenize.COMMENT):
                        self.continued = False

                if current_lineno > self.lineno:
                    self.block_end = current_lineno - 1
                    if current[0] == token.DEDENT:
                        break
        except tokenize.TokenError:
            pass

    def get_statement_start(self):
        return self.statement_start

    def get_block_end(self):
        return self.block_end

    def last_open_parens(self):
        if not self.open_parens:
            return None
        return self.open_parens[-1]

    def is_line_continued(self):
        return self.continued

    def get_line_indents(self, line_number):
        indents = 0
        for char in self.lines.get_line(line_number):
            if char == ' ':
                indents += 1
            else:
                break
        return indents

def count_line_indents(line):
    indents = 0
    for index, char in enumerate(line):
        if char == ' ':
            indents += 1
        elif char == '\t':
            indents += 8
        else:
            return indents
    return 0


def get_string_pattern():
    start = r'(\b[uU]?[rR]?)?'
    return '|'.join([r"%s'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?" % start,
                     r'%s"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?' % start,
                     r"%s'[^'\\\n]*(\\.[^'\\\n]*)*'?" % start,
                     r'%s"[^"\\\n]*(\\.[^"\\\n]*)*"?' % start])

def get_comment_pattern():
    return r'#[^\n]*'
