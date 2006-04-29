import re

class TextIndenter(object):
    '''A class for formatting texts'''
    def indent_line(self, index):
        '''indent the current line'''

class NullIndenter(TextIndenter):
    pass

class PythonCodeIndenter(TextIndenter):
    def __init__(self, editor):
        self.editor = editor

    def _get_line_start(self, index):
        while index != self.editor.get_start():
            index = self.editor.get_relative(index, -1)
            if self.editor.get(index) == '\n':
                return self.editor.get_relative(index, +1)
        return self.editor.get_start()

    def _get_prev_line_start(self, line_start):
        return self._get_line_start(self.editor.get_relative(line_start, -1))

    def _get_line_end(self, index):
        while index != self.editor.get_end():
            if self.editor.get(index) == '\n':
                return index
            index = self.editor.get_relative(index, +1)
        return self.editor.get_end()

    def _set_line_indents(self, line_start, indents):
        old_indents = self._count_line_indents(line_start)
        indent_diffs = indents - old_indents
        if indent_diffs == 0:
            return
        if indent_diffs > 0:
            self.editor.insert(line_start, ' ' * indent_diffs)
        else:
            self.editor.delete(line_start, self.editor.get_relative(line_start, -indent_diffs))

    def _get_line_contents(self, line_start):
        end = self._get_line_end(line_start)
        return self.editor.get(line_start, end)

    def _get_last_non_empty_line(self, line_start):
        current_line = self._get_prev_line_start(line_start)
        while current_line != self.editor.get_start() and \
                  self._get_line_contents(current_line).strip() == '':
            current_line = self._get_prev_line_start(current_line)
        return current_line

    def _count_line_indents(self, index):
        contents = self._get_line_contents(index)
        result = 0
        for x in contents:
            if x == ' ':
                result += 1
            else:
                break
        return result

    def _get_starting_backslash_line(self, line_start):
        current = line_start
        while current != self.editor.get_start():
            new_line = self._get_prev_line_start(current)
            if not self._get_line_contents(new_line).rstrip().endswith('\\'):
                return current
            current = new_line
        return self.editor.get_start()

    def _get_correct_indentation(self, line_start):
        if line_start == self.editor.get_start():
            return 0
        new_indent = self._get_base_indentation(line_start)

        prev_start = self._get_last_non_empty_line(line_start)
        prev_line = self._get_line_contents(prev_start)
        if prev_start == line_start or prev_line.strip() == '':
            new_indent = 0
        else:
            new_indent += self._get_indentation_changes_caused_by_prev_line(prev_line)
        current_line = self._get_line_contents(line_start)
        new_indent += self._get_indentation_changes_caused_by_current_line(current_line)
        return new_indent
        
    def _get_base_indentation(self, line_start):
        current_start = self._get_last_non_empty_line(line_start)
        current_line = self._get_line_contents(current_start)

        openings = 0
        while True:
            current_line = self._get_line_contents(current_start)
            current = len(current_line) - 1
            while current >= 0:
                if current_line[current] in list('([{'):
                    openings += 1
                if current_line[current] in list(')]}'):
                    openings -= 1
                if openings > 0:
                    return current + 1
                current -= 1
            if openings == 0:
                break
            if current_start == self.editor.get_start():
                break
            current_start = self._get_last_non_empty_line(current_start)

        if current_line.rstrip().endswith('\\'):
            real_start = self._get_starting_backslash_line(current_start)
            if (real_start == current_start):
                try:
                    return current_line.index(' = ') + 3
                except ValueError:
                    match = re.search('\\b ', current_line)
                    if match:
                        return match.start() + 1
                    else:
                        return len(current_line) + 1
        else:
            second_prev_start = self._get_prev_line_start(current_start)
            if second_prev_start != current_start and \
                   self._get_line_contents(second_prev_start).rstrip().endswith('\\'):
                real_start = self._get_starting_backslash_line(second_prev_start)
                return self._count_line_indents(real_start)
        return self._count_line_indents(current_start)


    def _is_line_continued(self, line_contents):
        if line_contents.endswith('\\'):
            return True
        current = len(line_contents) - 1
        openings = 0
        while current >= 0:
            if line_contents[current] in list('([{'):
                openings += 1
            if line_contents[current] in list(')]}'):
                openings -= 1
            if openings > 0:
                return True
            current -= 1
        return False


    def _get_indentation_changes_caused_by_prev_line(self, prev_line):
        new_indent = 0
        if prev_line.rstrip().endswith(':'):
            new_indent += 4
        if prev_line.strip() == 'pass':
            new_indent -= 4
        if (prev_line.lstrip().startswith('return ') or
            prev_line.lstrip().startswith('raise ')) and not self._is_line_continued(prev_line):
            new_indent -= 4
        if prev_line.strip() == 'break':
            new_indent -= 4
        if prev_line.strip() == 'continue':
            new_indent -= 4
        return new_indent
        
    def _get_indentation_changes_caused_by_current_line(self, current_line):
        new_indent = 0
        if current_line.strip() == 'else:':
            new_indent -= 4
        if current_line.strip() == 'finally:':
            new_indent -= 4
        if current_line.lstrip().startswith('except ') and current_line.rstrip().endswith(':'):
            new_indent -= 4
        return new_indent

    def indent_line(self, index):
        '''Correct the indentation of the line containing the given index'''
        start = self._get_line_start(index)
        self._set_line_indents(start, self._get_correct_indentation(start))

    def deindent(self, index):
        '''Deindent the line containing the given index'''
        start = self._get_line_start(index)
        indents = self._count_line_indents(start)
        new_indents = max(0, indents - 4)
        self._set_line_indents(start, new_indents)
