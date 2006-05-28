

class StatementRangeFinder(object):
    """A method object for finding the range of a statement"""

    def __init__(self, lines, lineno):
        self.lines = lines
        self.lineno = lineno
        self.in_string = ''
        self.open_parens = 0
        self.explicit_continuation = False

    def _analyze_line(self, current_line):
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
            if char in ')]}':
                self.open_parens -= 1
        if current_line.rstrip().endswith('\\'):
            self.explicit_continuation = True
        else:
            self.explicit_continuation = False


    def get_range(self):
        last_statement = 0
        for current_line_number in range(0, self.lineno + 1):
            if not self.explicit_continuation and self.open_parens == 0 and self.in_string == '':
                last_statement = current_line_number
            current_line = self.lines[current_line_number]
            self._analyze_line(current_line)
        last_indents = self.get_line_indents(last_statement)
        end_line = self.lineno
        if True or self.lines[self.lineno].rstrip().endswith(':'):
            for i in range(self.lineno + 1, len(self.lines)):
                if self.get_line_indents(i) >= last_indents:
                    end_line = i
                else:
                    break
        return (last_statement, end_line)

    def get_line_indents(self, line_number):
        indents = 0
        for char in self.lines[line_number]:
            if char == ' ':
                indents += 1
            else:
                break
        return indents

