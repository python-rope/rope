import ast
from ast import *  # noqa: F401,F403
from typing import Callable

from rope.base import fscommands


def parse(source, filename="<string>", *args, **kwargs):  # type: ignore
    if isinstance(source, str):
        source = fscommands.unicode_to_file_data(source)
    if b"\r" in source:
        source = source.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if not source.endswith(b"\n"):
        source += b"\n"
    try:
        return ast.parse(source, filename=filename, *args, **kwargs)
    except (TypeError, ValueError) as e:
        error = SyntaxError()
        error.lineno = 1
        error.filename = filename
        error.msg = str(e)
        raise error


def call_for_nodes(node, callback: Callable) -> None:
    """
    Apply the callback to node.
    Return immediately if the callback returns a result.
    Otherwise, recursively call *all* of node's direct children.
    """
    if not callback(node):
        for child in ast.iter_child_nodes(node):
            call_for_nodes(child, callback)


class RopeNodeVisitor(ast.NodeVisitor):
    def visit(self, node):
        """Modified from ast.NodeVisitor to match rope's existing Visitor implementation"""
        method = "_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)
