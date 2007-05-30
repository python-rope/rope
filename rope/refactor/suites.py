from rope.base import ast


def source_suite_tree(source):
    return ast_suite_tree(ast.parse(source))

def ast_suite_tree(ast):
    return Suite(ast.body, 1)


class Suite(object):

    def __init__(self, child_nodes, lineno, parent=None):
        self.parent = parent
        self.lineno = lineno
        self.child_nodes = child_nodes
        self._children = None

    def get_start(self):
        return self.lineno

    def get_children(self):
        if self._children is None:
            walker = _SuiteWalker(self)
            for child in self.child_nodes:
                ast.walk(child, walker)
            self._children = walker.suites
        return self._children


class _SuiteWalker(object):

    def __init__(self, suite):
        self.suite = suite
        self.suites = []

    def _If(self, node):
        self._add_if_like_node(node)

    def _For(self, node):
        self._add_if_like_node(node)

    def _While(self, node):
        self._add_if_like_node(node)

    def _With(self, node):
        self.suites.append(Suite(node.body, node.lineno, self.suite))

    def _TryFinally(self, node):
        if len(node.finalbody) == 1 and \
           isinstance(node.body[0], ast.TryExcept):
            self._TryExcept(node.body[0])
        else:
            self.suites.append(Suite(node.body, node.lineno, self.suite))
        self.suites.append(Suite(node.finalbody, node.lineno, self.suite))

    def _TryExcept(self, node):
        self.suites.append(Suite(node.body, node.lineno, self.suite))
        for handler in node.handlers:
            self.suites.append(Suite(handler.body, node.lineno, self.suite))
        if node.orelse:
            self.suites.append(Suite(node.orelse, node.lineno, self.suite))

    def _add_if_like_node(self, node):
        self.suites.append(Suite(node.body, node.lineno, self.suite))
        if node.orelse:
            self.suites.append(Suite(node.orelse, node.lineno, self.suite))

    def _FunctionDef(self, node):
        pass

    def _ClassDef(self, node):
        pass
