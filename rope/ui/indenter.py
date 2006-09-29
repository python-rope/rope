import re

from rope.codeanalyze import StatementRangeFinder


class TextIndenter(object):
    """A class for formatting texts"""

    def __init__(self, editor):
        self.editor = editor
        self.line_editor = editor.line_editor()

    def correct_indentation(self, lineno):
        """Correct the indentation of a line"""

    def deindent(self, lineno):
        """Deindent the a line"""
        current_indents = self._count_line_indents(lineno)
        new_indents = max(0, current_indents - 4)
        self._set_line_indents(lineno, new_indents)

    def indent(self, lineno):
        """Indents a line"""
        current_indents = self._count_line_indents(lineno)
        new_indents = current_indents + 4
        self._set_line_indents(lineno, new_indents)

    def entering_new_line(self, lineno):
        """Indents a line using `correct_indentation` and last line indents"""
        last_line = ""
        if lineno > 1:
            last_line = self.line_editor.get_line(lineno - 1)
        if last_line.strip() == '':
            self._set_line_indents(lineno, len(last_line))
        else:
            self.correct_indentation(lineno)
    
    def insert_tab(self, index):
        """Inserts a tab in the given index"""
        self.editor.insert(index, ' ' * 4)

    def _set_line_indents(self, lineno, indents):
        old_indents = self._count_line_indents(lineno)
        indent_diffs = indents - old_indents
        self.line_editor.indent_line(lineno, indent_diffs)

    def _count_line_indents(self, lineno):
        contents = self.line_editor.get_line(lineno)
        result = 0
        for x in contents:
            if x == ' ':
                result += 1
            else:
                break
        return result


class NormalIndenter(TextIndenter):

    def __init__(self, editor):
        super(NormalIndenter, self).__init__(editor)

    def correct_indentation(self, lineno):
        prev_indents = 0
        if lineno > 1:
            prev_indents = self._count_line_indents(lineno - 1)
        self._set_line_indents(lineno, prev_indents)
        

class PythonCodeIndenter(TextIndenter):
    def __init__(self, editor):
        super(PythonCodeIndenter, self).__init__(editor)

    def _get_last_non_empty_line(self, lineno):
        current_line = lineno - 1
        while current_line != 1 and \
                  self.line_editor.get_line(current_line).strip() == '':
            current_line -= 1
        return current_line

    def _get_starting_backslash_line(self, lineno):
        current = lineno
        while current != 1:
            new_line = current - 1
            if not self.line_editor.get_line(new_line).rstrip().endswith('\\'):
                return current
            current = new_line
        return 1

    def _get_correct_indentation(self, lineno):
        if lineno == 1:
            return 0
        new_indent = self._get_base_indentation(lineno)

        prev_lineno = self._get_last_non_empty_line(lineno)
        prev_line = self.line_editor.get_line(prev_lineno)
        if prev_lineno == lineno or prev_line.strip() == '':
            new_indent = 0
        current_line = self.line_editor.get_line(lineno)
        new_indent += self._get_indentation_changes_caused_by_current_stmt(current_line)
        return new_indent

    def _get_base_indentation(self, lineno):
        range_finder = StatementRangeFinder(self.line_editor,
                                            self._get_last_non_empty_line(lineno))
        range_finder.analyze()
        start = range_finder.get_statement_start()
        if not range_finder.is_line_continued():
            changes = self._get_indentation_changes_caused_by_prev_stmt(
                (start, self._get_last_non_empty_line(lineno)))
            return self._count_line_indents(start) + changes

        if range_finder.last_open_parens():
            open_parens = range_finder.last_open_parens()
            if self.line_editor.get_line(open_parens[0])[open_parens[1] + 1:].strip() == '':
                if len(range_finder.parens_openings) > 1:
                    return range_finder.parens_openings[-2][1] + 1
                else:
                    return self._count_line_indents(start) + 4
            return range_finder.last_open_parens()[1] + 1

        start_line = self.line_editor.get_line(start)
        if start == lineno - 1:
            try:
                equals_index = start_line.index(' = ') + 1
                if start_line[equals_index + 1:].strip() == '\\':
                    return self._count_line_indents(start) + 4
                return equals_index + 2
            except ValueError:
                match = re.search(r'(\b )|(\.)', start_line)
                if match:
                    return match.start() + 1
                else:
                    return len(start_line) + 1
        else:
            return self._count_line_indents(self._get_last_non_empty_line(lineno))


    def _get_indentation_changes_caused_by_prev_stmt(self, stmt_range):
        first_line = self.line_editor.get_line(stmt_range[0])
        last_line = self.line_editor.get_line(stmt_range[1])
        new_indent = 0
        if last_line.rstrip().endswith(':'):
            new_indent += 4
        if last_line.strip() == 'pass':
            new_indent -= 4
        if first_line.lstrip().startswith('return ') or \
           first_line.lstrip().startswith('raise '):
            new_indent -= 4
        if first_line.strip() == 'break':
            new_indent -= 4
        if first_line.strip() == 'continue':
            new_indent -= 4
        return new_indent

    def _get_indentation_changes_caused_by_current_stmt(self, current_line):
        new_indent = 0
        if current_line.strip() == 'else:':
            new_indent -= 4
        if current_line.strip() == 'finally:':
            new_indent -= 4
        if current_line.strip().startswith('elif '):
            new_indent -= 4
        if current_line.lstrip().startswith('except ') and \
           current_line.rstrip().endswith(':'):
            new_indent -= 4
        return new_indent

    def correct_indentation(self, lineno):
        """Correct the indentation of the line containing the given index"""
        self._set_line_indents(lineno, self._get_correct_indentation(lineno))

