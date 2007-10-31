# NOTE: This actually does not format anything.  It merely removes
#   extra blank lines and trailing white-spaces.  Now that
#   `rope.refactor.patchedast` has been added I think this can be
#   implemented.


class Formatter(object):

    def format(self, source_code):
        source_code = self._remove_extra_spaces(source_code)
        source_code = self._remove_extra_lines(source_code)
        source_code = self._correct_end_of_file_lines(source_code)
        return source_code

    def _remove_extra_spaces(self, source_code):
        result = []
        for line in source_code.splitlines():
            result.append(line.rstrip())
        if source_code.endswith('\n'):
            result.append('')
        return '\n'.join(result)

    def _remove_extra_lines(self, source_code):
        result = []
        blank_lines = 0
        for line in source_code.splitlines(True):
            if line.strip() == '':
                blank_lines += 1
                if blank_lines <= 2:
                    result.append(line)
            else:
                blank_lines = 0
                result.append(line)
        return ''.join(result)

    def _correct_end_of_file_lines(self, source_code):
        result = source_code.splitlines()
        while result and result[-1].strip() == '':
            del result[-1]
        if not result:
            result.append('')
        result.append('')
        return '\n'.join(result)
