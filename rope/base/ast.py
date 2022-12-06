import ast
import sys
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
        v = sys.version_info
        print(
            f"\nSyntax error using Python {v.major}.{v.minor}.{v.micro}\n"
            "Is this version compatible with the code you are refactoring?\n"
        )
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
    for child in get_child_nodes(node):
        walk(child, walker)


def get_child_nodes(node):
    if isinstance(node, ast.Module):
        return node.body
    result = []
    if node._fields is not None:
        for name in node._fields:
            child = getattr(node, name)
            if isinstance(child, list):
                for entry in child:
                    if isinstance(entry, ast.AST):
                        result.append(entry)
            if isinstance(child, ast.AST):
                result.append(child)
    return result


def call_for_nodes(node, callback, recursive=False):
    """If callback returns `True` the child nodes are skipped"""
    result = callback(node)
    if recursive and not result:
        for child in get_child_nodes(node):
            call_for_nodes(child, callback, recursive)


def get_children(node):
    result = []
    if node._fields is not None:
        for name in node._fields:
            if name in ["lineno", "col_offset"]:
                continue
            child = getattr(node, name)
            result.append(child)
    return result
