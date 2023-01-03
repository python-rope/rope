import ast
import sys
from ast import *  # noqa: F401,F403

from rope.base import fscommands

try:
    from ast import _const_node_type_names
except ImportError:
    # backported from stdlib `ast`
    _const_node_type_names = {
        bool: "NameConstant",  # should be before int
        type(None): "NameConstant",
        int: "Num",
        float: "Num",
        complex: "Num",
        str: "Str",
        bytes: "Bytes",
        type(...): "Ellipsis",
    }


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


class RopeNodeVisitor(ast.NodeVisitor):
    def visit(self, node):
        """Modified from ast.NodeVisitor to match rope's existing Visitor implementation"""
        method = "_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)


def get_const_subtype_name(node):
    """Get pre-3.8 ast node name"""
    # fmt: off
    assert sys.version_info >= (3, 8), "This should only be called in Python 3.8 and above"
    # fmt: on
    assert isinstance(node, ast.Constant)
    return _const_node_type_names[type(node.value)]


def get_node_type_name(node):
    return (
        get_const_subtype_name(node)
        if isinstance(node, ast.Constant)
        else node.__class__.__name__
    )
