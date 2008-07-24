import rope.base.codeanalyze
import rope.base.evaluate
from rope.base import worder, exceptions
from rope.base.codeanalyze import ArrayLinesAdapter, LogicalLineFinder


def get_pymodule(pycore, code, resource, maxfixes=1):
    """Get a `PyModule`"""
    commenter = None
    errors = []
    tries = 0
    while True:
        try:
            if tries == 0 and resource is not None and resource.read() == code:
                return pycore.resource_to_pyobject(resource, force_errors=True)
            return pycore.get_string_module(code, resource=resource,
                                            force_errors=True)
        except exceptions.ModuleSyntaxError, e:
            if tries < maxfixes:
                tries += 1
                if commenter is None:
                    lines = code.split('\n')
                    lines.append('\n')
                    commenter = _Commenter(lines)
                commenter.comment(e.lineno)
                code = '\n'.join(commenter.lines)
                errors.append('  * line %s: %s ... fixed' % (e.lineno,
                                                             e.message_))
            else:
                errors.append('  * line %s: %s ... raised!' % (e.lineno,
                                                               e.message_))
                new_message = ('\nSyntax errors in file %s:\n' % e.filename) \
                               + '\n'.join(errors)
                raise exceptions.ModuleSyntaxError(e.filename, e.lineno,
                                                   new_message)


def find_pyname_at(project, code, offset, pymodule, maxfixes):
    def old_pyname():
        word_finder = worder.Worder(code, True)
        expression = word_finder.get_primary_at(offset)
        expression = expression.replace('\\\n', ' ').replace('\n', ' ')
        lineno = code.count('\n', 0, offset)
        scope = pymodule.get_scope().get_inner_scope_for_line(lineno)
        return rope.base.evaluate.eval_str(scope, expression)
    def new_pyname():
        return rope.base.evaluate.eval_location(pymodule, offset)
    new_code = pymodule.source_code
    if new_code.startswith(code[:offset + 1]):
        return new_pyname()
    result = old_pyname()
    if result is None and offset < len(new_code):
        return new_pyname()
    return result


class _Commenter(object):

    def __init__(self, lines):
        self.lines = lines

    def comment(self, lineno):
        start = _logical_start(self.lines, lineno, check_prev=True) - 1
        end = self._get_block_end(start)
        indents = _get_line_indents(self.lines[start])
        if 0 < start:
            last_lineno = self._last_non_blank(start - 1)
            last_line = self.lines[last_lineno]
            if last_line.rstrip().endswith(':'):
                indents = _get_line_indents(last_line) + 4
        self.lines[start] = ' ' * indents + 'pass'
        for line in range(start + 1, end + 1):
            self.lines[line] = self.lines[start]
        self._fix_incomplete_try_blocks(lineno, indents)

    def _last_non_blank(self, start):
        while start > 0 and self.lines[start].strip() == '':
            start -= 1
        return start

    def _get_block_end(self, lineno):
        end_line = lineno
        base_indents = _get_line_indents(self.lines[lineno])
        for i in range(lineno + 1, len(self.lines)):
            if _get_line_indents(self.lines[i]) >= base_indents:
                end_line = i
            else:
                break
        return end_line

    def _fix_incomplete_try_blocks(self, lineno, indents):
        block_start = lineno
        last_indents = current_indents = indents
        while block_start > 0:
            block_start = rope.base.codeanalyze.get_block_start(
                ArrayLinesAdapter(self.lines), block_start) - 1
            if self.lines[block_start].strip().startswith('try:'):
                indents = _get_line_indents(self.lines[block_start])
                if indents > last_indents:
                    continue
                last_indents = indents
                block_end = self._find_matching_deindent(block_start)
                line = self.lines[block_end].strip()
                if not (line.startswith('finally:') or
                        line.startswith('except ') or
                        line.startswith('except:')):
                    self.lines.insert(block_end, ' ' * indents + 'finally:')
                    self.lines.insert(block_end + 1, ' ' * indents + '    pass')

    def _find_matching_deindent(self, line_number):
        indents = _get_line_indents(self.lines[line_number])
        current_line = line_number + 1
        while current_line < len(self.lines):
            line = self.lines[current_line]
            if not line.strip().startswith('#') and not line.strip() == '':
                # HACK: We should have used logical lines here
                if _get_line_indents(self.lines[current_line]) <= indents:
                    return current_line
            current_line += 1
        return len(self.lines) - 1

def _logical_start(lines, lineno, check_prev=False):
    logical_finder = LogicalLineFinder(ArrayLinesAdapter(lines))
    if check_prev:
        prev = lineno - 1
        while prev > 0:
            start, end = logical_finder.logical_line_in(prev)
            if end is None or start <= lineno < end:
                return start
            if start <= prev:
                break
            prev -= 1
    return logical_finder.logical_line_in(lineno)[0]


def _get_line_indents(line):
    return rope.base.codeanalyze.count_line_indents(line)
