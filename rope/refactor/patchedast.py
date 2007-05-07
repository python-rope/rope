import compiler


def get_patched_ast(source):
    """Adds `region` and `sorted_children` fields to nodes"""
    ast = compiler.parse(source)
    call_for_nodes(ast, _PatchingASTWalker(source))
    return ast


def call_for_nodes(ast, callback, recursive=False):
    """If callback returns `True` the child nodes are skipped"""
    result = callback(ast)
    if recursive and not result:
        for child in ast.getChildNodes():
            call_for_nodes(child, callback, recursive)


class _PatchingASTWalker(object):

    def __init__(self, source):
        self.source = _Source(source)

    def __call__(self, node):
        method = getattr(self, 'visit' + node.__class__.__name__, None)
        if method is not None:
            return method(node)
        # ???: Unknown node; What should we do here?
        raise RuntimeError('Unknown node type <%s>' %
                           type(node).__name__)

    def visitAssign(self, node):
        children = []
        start = self.source.offset
        offset = self.source.offset
        for child in node.nodes:
            call_for_nodes(child, self)
            children.append(self.source.get(offset, child.region[0]))
            children.append(child)
            children.append(self.source.till_token('='))
            self.source.consume('=')
            children.append('=')
            offset = self.source.offset
        call_for_nodes(node.expr, self)
        children.append(self.source.get(offset, node.expr.region[0]))
        children.append(node.expr)
        node.sorted_children = children
        node.region = (start, self.source.offset)

    def visitAssName(self, node):
        name = str(node.name)
        node.region = self.source.consume(name)
        node.sorted_children = [name]

    def visitConst(self, node):
        value = str(node.value)
        node.region = self.source.consume(value)
        node.sorted_children = [value]

    def visitModule(self, node):
        call_for_nodes(node.node, self)

    def visitStmt(self, node):
        for child in node.nodes:
            call_for_nodes(child, self)


class _Source(object):

    def __init__(self, source):
        self.source = source
        self.offset = 0

    def consume(self, token):
        new_offset = self.source.index(token, self.offset)
        self.offset = new_offset + len(token)
        return (new_offset, self.offset)

    def till_token(self, token):
        new_offset = self.source.index(token, self.offset)
        return self.get(self.offset, new_offset)

    def get(self, start, end):
        return self.source[start:end]

    def from_offset(self, offset):
        return self.get(offset, self.offset)
