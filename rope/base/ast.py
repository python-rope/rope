import ast
from ast import *

from rope.base import fscommands


def call_for_nodes(node, callback, recursive=False):
    """If callback returns `True` the child nodes are skipped"""
    result = callback(node)
    if recursive and not result:
        for child in ast.iter_child_nodes(node):
            call_for_nodes(child, callback, recursive)


class RopeNodeVisitor(ast.NodeVisitor):
    def visit(self, node):
        """Modified from ast.NodeVisitor to match rope's existing Visitor implementation"""
        method = "_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)
