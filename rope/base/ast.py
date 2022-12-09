import ast
from ast import *

from rope.base import fscommands


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


def walk_visitor(node, visitor) -> None:
    """Walk the syntax tree using a visitor class"""
    method_name = "_" + node.__class__.__name__
    method = getattr(visitor, method_name, None)
    if method is not None:
        method(node)
        return
    for child in ast.iter_child_nodes(node):
        walk_visitor(child, visitor)


def call_for_nodes(node, callback, recursive=False):
    """If callback returns `True` the child nodes are skipped"""
    result = callback(node)
    if recursive and not result:
        for child in ast.iter_child_nodes(node):
            call_for_nodes(child, callback, recursive)


def get_children(node):
    return [child for field, child in ast.iter_fields(node)]
