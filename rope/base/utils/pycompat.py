import sys
import _ast
# from rope.base import ast

PY2 = sys.version_info[0] == 2
PY27 = sys.version_info[0:2] >= (2, 7)
PY3 = sys.version_info[0] == 3
PY34 = sys.version_info[0:2] >= (3, 4)

try:
    str = unicode
except NameError:  # PY3

    str = str
    string_types = (str,)
    integer_types = (int,)
    import builtins
    ast_arg_type = _ast.arg

    def execfile(fn, global_vars=None, local_vars=None):
        with open(fn) as f:
            code = compile(f.read(), fn, 'exec')
            exec(code, global_vars or {}, local_vars)

    def get_ast_arg_arg(node):
        if isinstance(node, string_types):
            return node
        return node.arg


else:  # PY2

    string_types = (basestring,)
    integer_types = (int, long)
    builtins = __import__('__builtin__')
    ast_arg_type = _ast.Name
    execfile = execfile

    def get_ast_arg_arg(node):
        if isinstance(node, string_types):  # Python2 arguments.vararg, arguments.kwarg
            return node
        return node.id


def get_ast_with(node):
    # @todo fixmee - handle all withitems
    if PY2:
        return node
    return node.items[0]
