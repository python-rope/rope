import re

from rope.base import codeanalyze


class Fill(object):

    def __init__(self, width=70):
        self.width = width
        self.word_pattern = re.compile('\\S+\\s*')

    def fill(self, text):
        lines = text.splitlines()
        first_indents, indents = self._find_indents(lines)
        is_list = self._is_list(text)
        break_first = first_indents != indents
        if is_list:
            indents = first_indents + 2
            break_first = False

        builder = _TextBuilder(self.width, indents, first_indents)
        for line in lines:
            for match in self.word_pattern.finditer(line):
                matched = match.group()
                word = matched.strip()
                builder.add_word(word)
                if word.endswith('.') and \
                   (matched.endswith('  ') or matched.endswith('.')):
                    builder.end_sentence()
            if break_first:
                builder.end_line()
                break_first = False
        return builder.get_text()

    def fill_paragraph(self, text, offset):
        lines = codeanalyze.SourceLinesAdapter(text)
        current_line = lines.get_line_number(offset)
        start = self._find_block_start(lines, current_line)
        end = self._find_block_end(lines, current_line)
        return (start, end, self.fill(text[start:end]))

    def _find_block_start(self, lines, lineno):
        result = 1
        for i in range(lineno, -1, -1):
            line = lines.get_line(i).strip()
            if line == '':
                result = i + 1
                break
            if  self._is_list(line):
                result = i
                break
        return lines.get_line_start(result)

    def _find_block_end(self, lines, lineno):
        result = lines.length()
        for i in range(lineno + 1, lines.length()):
            line = lines.get_line(i).strip()
            if line == '' or self._is_list(line):
                result = i - 1
                break
        return lines.get_line_end(result)

    def _find_indents(self, lines):
        first_indents = 0
        indents = None
        if lines:
            first_indents = self._get_indents_for_line(lines[0])
            if len(lines) > 1:
                indents = self._get_indents_for_line(lines[1])
        return first_indents, indents

    def _get_indents_for_line(self, line):
        result = 0
        for c in line:
            if c.isspace():
                result += 1
            else:
                return result
        return result

    def _is_list(self, line):
        for mark in '*-+':
            if line.lstrip().startswith('%s ' % mark):
                return True
        return False


class _TextBuilder(object):

    def __init__(self, width, indents=0, first_indents=None):
        self.lines = []
        self.current_line = ''
        self.width = width
        if indents is None:
            indents = first_indents
        self.indents = indents
        self.first_indents = first_indents
        self._line = False

    def add_word(self, word):
        if (len(self.current_line) + 1 + len(word)) > self.width:
            self.end_line()
        self.current_line += self._get_prefix(word) + word
        self._line = False

    def _get_prefix(self, word):
        if self.current_line:
            if self._line:
                return '  '
            else:
                return ' '
        else:
            if not self.lines:
                return ' ' * self.first_indents
            return ' ' * self.indents

    def end_sentence(self):
        self._line = True

    def end_line(self):
        if self.current_line:
            self.lines.append(self.current_line)
            self.current_line = ''

    def get_text(self):
        self.end_line()
        return '\n'.join(self.lines)
