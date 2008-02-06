import re
import token
import tokenize

import rope.base.ast


class WordRangeFinder(object):
    """A class for finding boundaries of words and expressions

    Note that in these methods, offset should be the index of the
    character not the index of the character after it.

    """

    # XXX: many of these methods fail on comments
    # TODO: make disabled tests run

    def __init__(self, source_code):
        self.source = source_code

    def _find_word_start(self, offset):
        current_offset = offset
        while current_offset >= 0 and self._is_id_char(current_offset):
            current_offset -= 1;
        return current_offset + 1

    def _find_word_end(self, offset):
        while offset + 1 < len(self.source) and self._is_id_char(offset + 1):
            offset += 1;
        return offset

    def _find_last_non_space_char(self, offset):
        if offset <= 0:
            return 0
        while offset >= 0 and self.source[offset] in ' \t\n':
            if self.source[offset - 1:offset + 1] == '\\\n':
                offset -= 1
            offset -= 1
        return offset

    def get_word_at(self, offset):
        offset = self._get_fixed_offset(offset)
        return self.source[self._find_word_start(offset):
                           self._find_word_end(offset) + 1]

    def _get_fixed_offset(self, offset):
        if offset >= len(self.source):
            return offset - 1
        if not self._is_id_char(offset):
            if offset > 0 and self._is_id_char(offset - 1):
                return offset - 1
            if offset < len(self.source) - 1 and self._is_id_char(offset + 1):
                return offset + 1
        return offset

    def _is_id_char(self, offset):
        return self.source[offset].isalnum() or self.source[offset] == '_'

    def _find_string_start(self, offset):
        kind = self.source[offset]
        offset -= 1
        while self.source[offset] != kind:
            offset -= 1
        return offset

    def _find_parens_start(self, offset):
        offset = self._find_last_non_space_char(offset - 1)
        while offset >= 0 and self.source[offset] not in '[({':
            if self.source[offset] in ':,':
                pass
            else:
                offset = self._find_primary_start(offset)
            offset = self._find_last_non_space_char(offset - 1)
        return offset

    def _find_atom_start(self, offset):
        old_offset = offset
        if self.source[offset] in '\n\t ':
            offset = self._find_last_non_space_char(offset)
        if self.source[offset] in '\'"':
            return self._find_string_start(offset)
        if self.source[offset] in ')]}':
            return self._find_parens_start(offset)
        if self._is_id_char(offset):
            return self._find_word_start(offset)
        return old_offset

    def _find_primary_without_dot_start(self, offset):
        """It tries to find the undotted primary start

        It is different from `self._get_atom_start()` in that it
        follows function calls, too; such as in ``f(x)``.

        """
        last_atom = offset
        offset = self._find_last_non_space_char(last_atom)
        while offset > 0 and self.source[offset] in ')]':
            last_atom = self._find_parens_start(offset)
            offset = self._find_last_non_space_char(last_atom - 1)
        if offset >= 0 and (self.source[offset] in '"\'})]' or
                                   self._is_id_char(offset)):
            return self._find_atom_start(offset)
        return last_atom

    def _find_primary_start(self, offset):
        if offset >= len(self.source):
            offset = len(self.source) - 1
        if self.source[offset] != '.':
            offset = self._find_primary_without_dot_start(offset)
        else:
            offset = offset + 1
        while offset > 0:
            prev = self._find_last_non_space_char(offset - 1)
            if offset <= 0 or self.source[prev] != '.':
                break
            offset = self._find_primary_without_dot_start(prev - 1)
            if not self._is_id_char(offset):
                break

        return offset

    def get_primary_at(self, offset):
        offset = self._get_fixed_offset(offset)
        return self.source[self._find_primary_start(offset):
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
        if self.source[word_start:offset].strip() == '':
            word_start = end
        if self.source[end].isspace():
            word_start = end
        if self.source[real_start:word_start].strip() == '':
            real_start = word_start
        if real_start == word_start == end and not self._is_id_char(end):
            return ('', '', offset)
        if real_start == word_start:
            return ('', self.source[word_start:offset], word_start)
        else:
            if self.source[end] == '.':
                return (self.source[real_start:end], '', offset)
            last_dot_position = word_start
            if self.source[word_start] != '.':
                last_dot_position = self._find_last_non_space_char(word_start - 1)
            last_char_position = self._find_last_non_space_char(last_dot_position - 1)
            if self.source[word_start].isspace():
                word_start = offset
            return (self.source[real_start:last_char_position + 1],
                    self.source[word_start:offset], word_start)

    def _get_line_start(self, offset):
        while offset > 0 and self.source[offset] != '\n':
            offset -= 1
        return offset

    def _get_line_end(self, offset):
        while offset < len(self.source) and self.source[offset] != '\n':
            offset += 1
        return offset

    def _is_followed_by_equals(self, offset):
        while offset < len(self.source) and self.source[offset] in ' \\':
            if self.source[offset] == '\\':
                offset = self._get_line_end(offset)
            offset += 1
        if offset + 1 < len(self.source) and \
           self.source[offset] == '=' and self.source[offset + 1] != '=':
            return True
        return False

    def _is_name_assigned_in_class_body(self, offset):
        word_start = self._find_word_start(offset - 1)
        word_end = self._find_word_end(offset) + 1
        if '.' in self.source[word_start:word_end]:
            return False
        line_start = self._get_line_start(word_start)
        line = self.source[line_start:word_start].strip()
        if line == '' and self._is_followed_by_equals(word_end):
            return True
        return False

    def is_a_class_or_function_name_in_header(self, offset):
        word_start = self._find_word_start(offset - 1)
        line_start = self._get_line_start(word_start)
        prev_word = self.source[line_start:word_start].strip()
        return prev_word in ['def', 'class']

    def _find_first_non_space_char(self, offset):
        if offset >= len(self.source):
            return len(self.source)
        while offset < len(self.source):
            if offset + 1 < len(self.source) and \
               self.source[offset] == '\\':
                offset += 2
            elif self.source[offset] in ' \t\n':
                offset += 1
            else:
                break
        return offset

    def is_a_function_being_called(self, offset):
        word_end = self._find_word_end(offset) + 1
        next_char = self._find_first_non_space_char(word_end)
        return next_char < len(self.source) and \
               self.source[next_char] == '(' and \
               not self.is_a_class_or_function_name_in_header(offset)

    def _find_import_pair_end(self, start):
        next_char = self._find_first_non_space_char(start)
        if next_char >= len(self.source):
            return len(self.source)
        if self.source[next_char] == '(':
            try:
                return self.source.index(')', next_char) + 1
            except ValueError:
                return SyntaxError('Unmatched Parens')
        else:
            offset = next_char
            while offset < len(self.source):
                if self.source[offset] == '\n':
                    break
                if self.source[offset] == '\\':
                    offset += 1
                offset += 1
            return offset

    def is_import_statement(self, offset):
        try:
            last_import = self.source.rindex('import ', 0, offset)
        except ValueError:
            return False
        return self._find_import_pair_end(last_import + 7) >= offset

    def is_from_statement(self, offset):
        try:
            last_from = self.source.rindex('from ', 0, offset)
            from_import = self.source.index(' import ', last_from)
            from_names = from_import + 8
        except ValueError:
            return False
        from_names = self._find_first_non_space_char(from_names)
        return self._find_import_pair_end(from_names) >= offset

    def is_from_statement_module(self, offset):
        if offset >= len(self.source) - 1:
            return False
        stmt_start = self._find_primary_start(offset)
        line_start = self._get_line_start(stmt_start)
        prev_word = self.source[line_start:stmt_start].strip()
        return prev_word == 'from'

    def is_a_name_after_from_import(self, offset):
        try:
            # XXX: what if there is the char after from or around
            # import is not space?
            last_from = self.source.rindex('from ', 0, offset)
            from_import = self.source.index(' import ', last_from)
            from_names = from_import + 8
        except ValueError:
            return False
        if from_names - 1 > offset:
            return False
        return self._find_import_pair_end(from_names) >= offset

    def get_from_module(self, offset):
        try:
            last_from = self.source.rindex('from ', 0, offset)
            import_offset = self.source.index(' import ', last_from)
            end = self._find_last_non_space_char(import_offset)
            return self.get_primary_at(end)
        except ValueError:
            pass

    def is_from_aliased(self, offset):
        if not self.is_a_name_after_from_import(offset):
            return False
        try:
            end = self._find_word_end(offset)
            as_end = self._find_word_end(end + 1)
            as_start = self._find_word_start(as_end)
            if self.source[as_start:as_end + 1] == 'as':
                return True
        except ValueError:
            return False

    def get_from_aliased(self, offset):
        try:
            end = self._find_word_end(offset)
            as_ = self._find_word_end(end + 1)
            alias = self._find_word_end(as_ + 1)
            start = self._find_word_start(alias)
            return self.source[start:alias + 1]
        except ValueError:
            pass

    def is_function_keyword_parameter(self, offset):
        word_end = self._find_word_end(offset)
        if word_end + 1 == len(self.source):
            return False
        next_char = self._find_first_non_space_char(word_end + 1)
        if next_char + 2 >= len(self.source) or \
           self.source[next_char] != '=' or \
           self.source[next_char + 1] == '=':
            return False
        word_start = self._find_word_start(offset)
        prev_char = self._find_last_non_space_char(word_start - 1)
        if prev_char - 1 < 0 or self.source[prev_char] not in ',(':
            return False
        return True

    def is_on_function_call_keyword(self, offset, stop_searching=0):
        if self._is_id_char(offset):
            offset = self._find_word_start(offset) - 1
        offset = self._find_last_non_space_char(offset)
        if offset <= stop_searching or \
           self.source[offset] not in '(,':
            return False
        parens_start = self.find_parens_start_from_inside(offset, stop_searching)
        if stop_searching < parens_start:
            return True
        return False

    def find_parens_start_from_inside(self, offset, stop_searching=0):
        opens = 1
        while offset > stop_searching:
            if self.source[offset] == '(':
                opens -= 1
            if opens == 0:
                break
            if self.source[offset] == ')':
                opens += 1
            offset -= 1
        return offset

    def is_assigned_here(self, offset):
        operation = self.get_assignment_type(offset)
        operations = ('=', '-=', '+=', '*=', '/=', '%=', '**=',
                      '>>=', '<<=', '&=', '^=', '|=')
        return operation in operations

    def get_assignment_type(self, offset):
        word_end = self._find_word_end(offset)
        next_char = self._find_first_non_space_char(word_end + 1)
        current_char = next_char
        while current_char + 1 < len(self.source) and \
              (self.source[current_char] != '=' or \
               self.source[current_char + 1] == '=') and \
              current_char < next_char + 3:
            current_char += 1
        operation = self.source[next_char:current_char + 1]
        return operation

    def get_primary_range(self, offset):
        offset = max(0, offset)
        start = self._find_primary_start(offset)
        end = self._find_word_end(offset) + 1
        return (start, end)

    def get_word_range(self, offset):
        offset = max(0, offset)
        start = self._find_word_start(offset)
        end = self._find_word_end(offset) + 1
        return (start, end)

    def get_word_parens_range(self, offset):
        if self.is_a_function_being_called(offset) or \
           self.is_a_class_or_function_name_in_header(offset):
            end = self._find_word_end(offset)
            start_parens = self.source.index('(', end)
            index = start_parens
            open_count = 0
            while index < len(self.source):
                if self.source[index] == '(':
                    open_count += 1
                if self.source[index] == ')':
                    open_count -= 1
                if open_count == 0:
                    return (start_parens, index + 1)
                index += 1
            return (start_parens, index)
        return (None, None)


def get_name_at(resource, offset):
    source_code = resource.read()
    word_finder = WordRangeFinder(source_code)
    return word_finder.get_word_at(offset)


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
        try:
            i = -1
            while True:
                i = self.source_code.index('\n', i + 1)
                self.line_starts.append(i + 1)
        except ValueError:
            pass
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


class _CachingLogicalLineFinder(object):

    def __init__(self, lines):
        self.lines = lines

    _starts = None
    @property
    def starts(self):
        if self._starts is None:
            self._init_logicals()
        return self._starts

    _ends = None
    @property
    def ends(self):
        if self._ends is None:
            self._init_logicals()
        return self._ends

    def _init_logicals(self):
        """Should initialize _starts and _ends attributes"""

    def logical_line_in(self, line_number):
        start = line_number
        while start > 0 and not self.starts[start]:
            start -= 1
        if start == 0:
            try:
                start = self.starts.index(True, line_number)
            except ValueError:
                return (line_number, line_number)
        return (start, self.ends.index(True, start))

    def generate_starts(self, start_line=1, end_line=None):
        if end_line is None:
            end_line = self.lines.length()
        for index in range(start_line, end_line):
            if self.starts[index]:
                yield index


class TokenizerLogicalLineFinder(_CachingLogicalLineFinder):

    def __init__(self, lines):
        super(TokenizerLogicalLineFinder, self).__init__(lines)
        self.logical_lines = LogicalLineFinder(lines)

    def _init_logicals(self):
        self._starts = [False] * (self.lines.length() + 1)
        self._ends = [False] * (self.lines.length() + 1)
        for start, end in self.logical_lines.generate_regions():
            self._starts[start] = True
            self._ends[end] = True


class ASTLogicalLineFinder(_CachingLogicalLineFinder):

    def __init__(self, node, lines):
        self.node = node
        super(ASTLogicalLineFinder, self).__init__(lines)
        self._min_ends = {}

    def _init_logicals(self):
        self._starts = [False] * (self.lines.length() + 1)
        self._ends = [False] * (self.lines.length() + 1)
        rope.base.ast.call_for_nodes(self.node, self.__analyze_node, True)
        current = self.lines.length()
        while current > 0:
            while current > 0:
                line = self.lines.get_line(current)
                if line.strip() == '' or line.startswith('#'):
                    current -= 1
                else:
                    break
            last_end = current
            while current > 0:
                if self._starts[current]:
                    if last_end >= self._min_ends.get(current, 0):
                        self._ends[last_end] = True
                    break
                current -= 1
            current -= 1

    _last_stmt = None
    def __analyze_node(self, node):
        if isinstance(node, rope.base.ast.stmt):
            line = self.lines.get_line(node.lineno)
            offset = node.col_offset
            if offset > 0 and not line[:node.col_offset].isspace():
                self.__update_last_min(node.lineno)
            self._last_stmt = node
            self._starts[node.lineno] = True
            return False
        if isinstance(node, rope.base.ast.expr):
            self.__update_last_min(node.lineno)
            return True

    def __update_last_min(self, lineno):
        if self._last_stmt is None:
            return
        start = self._last_stmt.lineno
        if lineno > start:
            last_min = self._min_ends.get(start, 0)
            min_end = max(last_min, lineno)
            self._min_ends[start] = min_end


class CustomLogicalLineFinder(_CachingLogicalLineFinder):
    """A method object for finding the range of a statement"""

    def __init__(self, lines):
        super(CustomLogicalLineFinder, self).__init__(lines)
        self.in_string = ''
        self.open_count = 0
        self.explicit_continuation = False

    def _init_logicals(self):
        size = self.lines.length()
        self._starts = [False] * (size + 1)
        self._ends = [False] * (size + 1)
        i = 1
        while i <= size:
            while i <= size and self.lines.get_line(i).strip() == '':
                i += 1
            if i <= size:
                self._starts[i] = True
                self._analyze_line(i)
                while (self.explicit_continuation
                       or self.open_count or self.in_string):
                    i += 1
                    self._analyze_line(i)
                self._ends[i] = True
                i += 1

    _main_chars = re.compile(r'[\'|"|#|\\|\[|\]|\{|\}|\(|\)]')
    def _analyze_line(self, lineno):
        current_line = self.lines.get_line(lineno)
        char = None
        for match in self._main_chars.finditer(current_line):
            char = match.group()
            i = match.start()
            if char in '\'"':
                if not self.in_string:
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
            if char in ')]}':
                self.open_count -= 1
        if current_line and char != '#' and current_line.endswith('\\'):
            self.explicit_continuation = True
        else:
            self.explicit_continuation = False


class LogicalLineFinder(object):

    def __init__(self, lines):
        self.lines = lines

    def logical_line_in(self, line_number):
        indents = count_line_indents(self.lines.get_line(line_number))
        tries = 0
        while True:
            block_start = get_block_start(self.lines, line_number, indents)
            try:
                return self._block_logical_line(block_start, line_number)
            except IndentationError, e:
                tries += 1
                if tries == 5:
                    raise e
                lineno = e.lineno + block_start - 1
                indents = count_line_indents(self.lines.get_line(lineno))

    def generate_starts(self, start_line=1, end_line=None):
        for start, end in self.generate_regions(start_line, end_line):
            yield start

    def generate_regions(self, start_line=1, end_line=None):
        # XXX: `block_start` should be at a better position!
        block_start = 1
        readline = LinesToReadline(self.lines, block_start)
        shifted = start_line - block_start + 1
        try:
            for start, end in self._logical_lines(readline):
                real_start = start + block_start - 1
                real_start = self._first_non_blank(real_start)
                if end_line is not None and real_start >= end_line:
                    break
                real_end = end + block_start - 1
                if real_start >= start_line:
                    yield (real_start, real_end)
        except tokenize.TokenError, e:
            pass

    def get_logical_line_in(self, line_number):
        warnings.warn('Use `LogicalLineFinder.logical_line_in()` instead',
                      DeprecationWarning, stacklevel=2)
        return self.logical_line_in(line_number)

    def _block_logical_line(self, block_start, line_number):
        readline = LinesToReadline(self.lines, block_start)
        shifted = line_number - block_start + 1
        region = self._calculate_logical(readline, shifted)
        start = self._first_non_blank(region[0] + block_start - 1)
        if region[1] is None:
            end = self.lines.length()
        else:
            end = region[1] + block_start - 1
        return start, end

    def _calculate_logical(self, readline, line_number):
        last_end = 1
        try:
            for start, end in self._logical_lines(readline):
                if line_number <= end:
                    return (start, end)
                last_end = end + 1
        except tokenize.TokenError, e:
            current = e.args[1][0]
            return (last_end, current)
        return (last_end, None)

    def _logical_lines(self, readline):
        last_end = 1
        for current_token in tokenize.generate_tokens(readline):
            current = current_token[2][0]
            if current_token[0] == token.NEWLINE:
                yield (last_end, current)
                last_end = current + 1

    def _first_non_blank(self, line_number):
        current = line_number
        while current < self.lines.length():
            line = self.lines.get_line(current).strip()
            if line != '' and not line.startswith('#'):
                return current
            current += 1
        return current


def get_block_start(lines, lineno, maximum_indents=80):
    """Approximate block start"""
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


_block_start_pattern = None

def get_block_start_patterns():
    global _block_start_pattern
    if not _block_start_pattern:
        pattern = '^\\s*(((def|class|if|elif|except|for|while|with)\\s)|'\
                  '((try|else|finally|except)\\s*:))'
        _block_start_pattern = re.compile(pattern, re.M)
    return _block_start_pattern


def count_line_indents(line):
    indents = 0
    for char in line:
        if char == ' ':
            indents += 1
        elif char == '\t':
            indents += 8
        else:
            return indents
    return 0


def get_string_pattern():
    start = r'(\b[uU]?[rR]?)?'
    longstr = r'%s"""(\\.|"(?!"")|\\\n|[^"\\])*"""' % start
    shortstr = r'%s"(\\.|[^"\\\n])*"' % start
    return '|'.join([longstr, longstr.replace('"', "'"),
                     shortstr, shortstr.replace('"', "'")])

def get_comment_pattern():
    return r'#[^\n]*'
