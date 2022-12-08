"""Wrappers for stdlib.ast.parse and stdlib.ast.walk."""
import ast

from rope.base import astutils, fscommands


def parse(source, filename="<string>"):
    # NOTE: the raw string should be given to `compile` function
    if isinstance(source, str):
        source = fscommands.unicode_to_file_data(source)
    if b"\r" in source:
        source = source.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if not source.endswith(b"\n"):
        source += b"\n"
    try:
        return ast.parse(source, filename="<unknown>")
    except (TypeError, ValueError) as e:
        error = SyntaxError()
        error.lineno = 1
        error.filename = filename
        error.msg = str(e)
        raise error


def walk(node, walker) -> None:
    """Walk the syntax tree"""
    method_name = "_" + node.__class__.__name__
    method = getattr(walker, method_name, None)
    if method is not None:
        method(node)
        return
    for child in astutils.get_child_nodes(node):
        walk(child, walker)


