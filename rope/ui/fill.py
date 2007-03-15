import re


class Fill(object):

    def __init__(self, width=70):
        self.width = width
        self.separators = re.compile('\\s+')

    def fill(self, text):
        lines = text.splitlines()
        indents = self._find_indents(lines)
        builder = _TextBuilder(self.width, indents)
        for line in lines:
            for word in self.separators.split(line):
                builder.add_word(word)
        return builder.get_text()

    def _find_indents(self, lines):
        indents = 0
        if lines:
            for c in lines[0]:
                if c.isspace():
                    indents += 1
                else:
                    return indents
        return indents


class _TextBuilder(object):

    def __init__(self, width, indents=0):
        self.lines = []
        self.current_line = ''
        self.width = width
        self.indents = indents
        self._new_line()

    def add_word(self, word):
        if (len(self.current_line) + 1 + len(word)) > self.width:
            self._end_line()
        if self.current_line.strip():
            self.current_line += ' '
        self.current_line += word

    def _end_line(self):
        if self.current_line.strip():
            self.lines.append(self.current_line)
            self._new_line()

    def _new_line(self):
        self.current_line = ' ' * self.indents

    def get_text(self):
        self._end_line()
        return '\n'.join(self.lines)
