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
        ast_node = compiler.parse(source_code)
        return self.write_ast(ast_node)

    def write_ast(self, ast_node):
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

