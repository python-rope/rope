import compiler

# NOTE: I've stopped developing a formatter for a few reasons:
#
#  * There has been many attempts for writing an AST
#    writer so I won't bother implementing one myself and
#    wait for a good one.
#  * Although formatting python source is a good feature
#    to add, right now I'll put more time in developing
#    core parts and give up writing a formatter.
#
#  So a formatter would be added some time in the future,
#  maybe by rope's contributing users.


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

    def _rewrite_ast(self, source_code):
        ast_node = compiler.parse(source_code)
        writer = _ASTWriter()
        compiler.walk(ast_node, writer)
        return writer.output


class _ASTWriter(object):

    def __init__(self):
        self.output = ''

    def visitAssName(self, node):
        self.output += node.name + ' = '

    def visitConst(self, node):
        self.output += str(node.value) + '\n'

