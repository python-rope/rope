
class LineOrientedSourceTools(object):

    def __init__(self, lines):
        self.lines = lines
    
    def get_indents(self, lineno):
        indents = 0
        for char in self.lines[lineno - 1]:
            if char == ' ':
                indents += 1
            else:
                break
        return indents
    
    def get_location(self, offset):
        current_pos = 0
        lineno = 1
        while current_pos + len(self.lines[lineno - 1]) < offset:
            current_pos += len(self.lines[lineno - 1]) + 1
            lineno += 1
        return (lineno, offset - current_pos)

    def get_name_at(self, offset):
        lineno, colno = self.get_location(offset)
        postfix = ''
        for c in self.lines[lineno - 1][colno:]:
            if c.isalnum() or c == '_':
                postfix += c
            else:
                break
        prefix = ''
        for c in reversed(self.lines[lineno - 1][0:colno]):
            if c.isalnum() or c in '._':
                prefix = c + prefix
            else:
                break
        return prefix + postfix
    
    def get_holding_scope(self, module_scope, lineno, line_indents=None):
        line_indents = line_indents
        if line_indents is None:
            line_indents = self.get_indents(lineno)
        current_scope = module_scope
        inner_scope = current_scope
        while current_scope is not None and \
              (current_scope.get_kind() == 'Module' or
               self.get_indents(current_scope.get_lineno()) < line_indents):
            inner_scope = current_scope
            new_scope = None
            for scope in current_scope.get_scopes():
                if scope.get_lineno() <= lineno:
                    new_scope = scope
                else:
                    break
            current_scope = new_scope
        return inner_scope


class Lines(object):

    def get_line(self, line_number):
        pass

    def length(self):
        pass


class ArrayLinesAdapter(object):

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

