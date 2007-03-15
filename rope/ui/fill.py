import re

from rope.base import codeanalyze


class Fill(object):

    def __init__(self, width=70):
        self.width = width
        self.separators = re.compile('\\S+\\s*')

    def fill(self, text):
        lines = text.splitlines()
        indents = self._find_indents(lines)
        builder = _TextBuilder(self.width, indents)
        for line in lines:
            for match in self.separators.finditer(line):
                matched = match.group()
                word = matched.strip()
                builder.add_word(word)
                if word.endswith('.') and \
                   (matched.endswith('  ') or matched.endswith('.')):
                    builder.end_line()
        return builder.get_text()

    def fill_paragraph(self, text, offset):
        lines = codeanalyze.SourceLinesAdapter(text)
        current_line = lines.get_line_number(offset)
        start = self._find_block_start(lines, current_line)
        end = self._find_block_end(lines, current_line)
        return (start, end, self.fill(text[start:end]))

    def _find_block_start(self, lines, lineno):
        result = 1
        for i in range(lineno - 1, 0, -1):
            if lines.get_line(i).strip() == '':
                result = i + 1
                break
        return lines.get_line_start(result)

    def _find_block_end(self, lines, lineno):
        result = lines.length()
        for i in range(lineno + 1, lines.length()):
            if lines.get_line(i).strip() == '':
                result = i - 1
                break
        return lines.get_line_end(result)

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
        self._line = False

    def add_word(self, word):
        if (len(self.current_line) + 1 + len(word)) > self.width:
            self._end_line()
        self.current_line += self._get_prefix() + word
        self._line = False

    def _get_prefix(self):
        if self.current_line:
            if self._line:
                return '  '
            else:
                return ' '
        else:
            return ' ' * self.indents

    def end_line(self):
        self._line = True

    def _end_line(self):
        if self.current_line:
            self.lines.append(self.current_line)
            self.current_line = ''

    def get_text(self):
        self._end_line()
        return '\n'.join(self.lines)
