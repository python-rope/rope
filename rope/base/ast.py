from _ast import *
import _ast


def parse(source, filename='<string>'):
    # NOTE: the raw string should be given to `compile` function
    if isinstance(source, unicode):
        source = source.encode('utf-8')
    return compile(source, filename, 'exec', _ast.PyCF_ONLY_AST)


def walk(node, walker):
    method_name = '_' + node.__class__.__name__
    method = getattr(walker, method_name, None)
    if method is not None:
        return method(node)
    for child in get_child_nodes(node):
        walk(child, walker)


def get_child_nodes(node):
    result = []
    if node._fields is not None:
        for name in node._fields:
            child = getattr(node, name)
            if isinstance(child, list):
                for entry in child:
                    result.append(entry)
            if isinstance(child, _ast.AST):
                result.append(child)
    return result
