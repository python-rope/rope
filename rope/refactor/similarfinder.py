"""This module can be used for finding similar code"""
import compiler.ast

from rope.refactor import patchedast


class SimilarFinder(object):
    """A class for finding similar expressions and statements"""

    def __init__(self, source, start=0, end=None):
        self.source = source
        self.start = start
        self.end = len(self.source)
        if end is not None:
            self.end = end
        self.ast = patchedast.get_patched_ast(self.source)

    def get_match_regions(self, code):
        wanted = self._create_pattern(code)
        matches = _ASTMatcher(self.ast, wanted).find_matches()
        for match in matches:
            start, end = match.get_region()
            if self.start <= start < end <= self.end:
                yield match.get_region()

    def _create_pattern(self, expression):
        ast = compiler.parse(expression)
        # Module.Stmt
        nodes = ast.node.nodes
        if len(nodes) == 1 and isinstance(nodes[0], compiler.ast.Discard):
            # Discard
            wanted = nodes[0].expr
        else:
            wanted = nodes
        return wanted

    def _does_match(self, node1, node2):
        if node1.__class__ != node2.__class__:
            return False
        children1 = node1.getChildren()
        children2 = node2.getChildren()
        if len(children1) != len(children2):
            return False
        for child1, child2 in zip(children1, children2):
            if isinstance(child1, compiler.ast.Node):
                if not self._does_match(child1, child2):
                    return False
            else:
                if child1 != child2:
                    return False
        return True


class _ASTMatcher(object):

    def __init__(self, body, pattern):
        """Searches the given pattern in the body AST.

        body is an AST node and pattern can be either an AST node or
        a list of ASTs nodes
        """
        self.body = body
        self.pattern = pattern
        self.matches = None

    def find_matches(self):
        if self.matches is None:
            self.matches = []
            patchedast.call_for_nodes(self.body, self._check_node,
                                      recursive=True)
        return self.matches

    def _check_node(self, node):
        if isinstance(self.pattern, list):
            self._match_statements(node)
        elif self._does_match(self.pattern, node):
            self.matches.append(ExpressionMatch(node))

    def _does_match(self, node1, node2):
        if node1.__class__ != node2.__class__:
            return False
        children1 = node1.getChildren()
        children2 = node2.getChildren()
        if len(children1) != len(children2):
            return False
        for child1, child2 in zip(children1, children2):
            if isinstance(child1, compiler.ast.Node):
                if not self._does_match(child1, child2):
                    return False
            else:
                if child1 != child2:
                    return False
        return True

    def _match_statements(self, node):
        if not isinstance(node, compiler.ast.Stmt):
            return
        for index in range(len(node.nodes)):
            if len(node.nodes) - index >= len(self.pattern):
                current_stmts = node.nodes[index:index + len(self.pattern)]
                if self._does_stmts_match(current_stmts):
                    self.matches.append(StatementMatch(current_stmts))

    def _does_stmts_match(self, current_stmts):
        if len(current_stmts) != len(self.pattern):
            return False
        for stmt, expected in zip(current_stmts, self.pattern):
            if not self._does_match(stmt, expected):
                return False
        return True


class Match(object):

    def get_region(self):
        """Returns match region"""

class ExpressionMatch(object):

    def __init__(self, ast):
        self.ast = ast

    def get_region(self):
        return self.ast.region


class StatementMatch(object):

    def __init__(self, ast_list):
        self.ast_list = ast_list

    def get_region(self):
        return self.ast_list[0].region[0], self.ast_list[-1].region[1]
