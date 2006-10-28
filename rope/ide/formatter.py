import compiler

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

