import re

from rope.base import codeanalyze


class Statements(object):

    def __init__(self, source):
        self.source = source
        self.lines = codeanalyze.SourceLinesAdapter(source)
        self.logical_lines = codeanalyze.LogicalLineFinder(self.lines)

    def next(self, offset):
        if offset == len(self.source):
            return offset
        lineno = self.lines.get_line_number(offset)
        if offset == self.lines.get_line_end(lineno):
            lineno = self._next_nonblank(lineno, 1)
        start, end = self.logical_lines.get_logical_line_in(lineno)
        end_offset = self.lines.get_line_end(end)
        return end_offset

    def prev(self, offset):
        if offset == 0:
            return offset
        lineno = self.lines.get_line_number(offset)
        if self.lines.get_line_start(lineno) <= offset:
            diff = self.source[self.lines.get_line_start(lineno):offset]
            if not diff.strip():
                lineno = self._next_nonblank(lineno, -1)
        start, end = self.logical_lines.get_logical_line_in(lineno)
        start_offset = self.lines.get_line_start(start)
        return _next_char(self.source, start_offset)

    def _next_nonblank(self, lineno, direction=1):
        lineno += direction
        while lineno > 1 and lineno < self.lines.length() and \
              self.lines.get_line(lineno).strip() == '':
            lineno += direction
        return lineno


class Scopes(object):

    def __init__(self, source):
        self.source = source
        self.pattern = re.compile(r'^[ \t]*(def|class)\s', re.M)
        self.matches = None

    def next(self, offset):
        match = self.pattern.search(self.source, offset)
        if match is not None:
            if self.source[offset:match.start()].strip(' \t\r\n') == '':
                match = self.pattern.search(self.source, match.end())
        if match is not None:
            offset = match.start()
        else:
            offset = len(self.source)
        return self._prev_char(offset - 1)

    def _prev_char(self, offset):
        while 0 < offset and self.source[offset] in ' \t\r\n':
            offset -= 1
        return offset + 1

    def prev(self, offset):
        if self.matches is None:
            self.matches = list(self.pattern.finditer(self.source))
        prev_match = None
        for match in self.matches:
            if match.start() <= offset:
                prev_match = match
            else:
                break
        if prev_match is not None:
            start = prev_match.start()
            if self.source[start] == '\n':
                start += 1
            if self.source[start:offset].strip() == '':
                return self.prev(prev_match.start() - 1)
            return _next_char(self.source, start)
        return 0


def _next_char(source, offset):
    while offset < len(source) and \
          source[offset] in ' \t':
        offset += 1
    return offset
