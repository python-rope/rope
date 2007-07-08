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
        return self._next_char(start_offset)

    def _next_nonblank(self, lineno, direction=1):
        lineno += direction
        while lineno > 1 and lineno < self.lines.length() and \
              self.lines.get_line(lineno).strip() == '':
            lineno += direction
        return lineno

    def _next_char(self, offset):
        while offset < len(self.source) and \
              self.source[offset] in ' \t':
            offset += 1
        return offset
