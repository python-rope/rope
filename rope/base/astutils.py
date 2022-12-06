import ast
from rope.base import fscommands


class _NodeNameCollector:
    def __init__(self, levels=None):
        self.names = []
        self.levels = levels
        self.index = 0

    def _add_node(self, node):
        new_levels = []
        if self.levels is not None:
            new_levels = list(self.levels)
            new_levels.append(self.index)
        self.index += 1
        self._added(node, new_levels)

    def _added(self, node, levels):
        if hasattr(node, "id"):
            self.names.append((node.id, levels))

    def _Name(self, node):
        self._add_node(node)

    def _ExceptHandler(self, node):
        self.names.append((node.name, []))

    def _Tuple(self, node):
        new_levels = []
        if self.levels is not None:
            new_levels = list(self.levels)
            new_levels.append(self.index)
        self.index += 1
        visitor = _NodeNameCollector(new_levels)
        for child in get_child_nodes(node):
            walk(child, visitor)
        self.names.extend(visitor.names)

    def _Subscript(self, node):
        self._add_node(node)

    def _Attribute(self, node):
        self._add_node(node)

    def _Slice(self, node):
        self._add_node(node)


def get_name_levels(node):
    """Return a list of ``(name, level)`` tuples for assigned names

    The `level` is `None` for simple assignments and is a list of
    numbers for tuple assignments for example in::

      a, (b, c) = x

    The levels for for `a` is ``[0]``, for `b` is ``[1, 0]`` and for
    `c` is ``[1, 1]``.

    """
    visitor = _NodeNameCollector()
    walk(node, visitor)
    return visitor.names


def call_for_nodes(node, callback, recursive=False):
    """If callback returns `True` the child nodes are skipped"""
    result = callback(node)
    if recursive and not result:
        for child in get_child_nodes(node):
            call_for_nodes(child, callback, recursive)


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


def get_children(node):
    result = []
    if node._fields is not None:
        for name in node._fields:
            if name in ["lineno", "col_offset"]:
                continue
            child = getattr(node, name)
            result.append(child)
    return result


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
    for child in get_child_nodes(node):
        walk(child, walker)
