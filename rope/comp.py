import sys
import _ast
# from rope.base import ast

PY2 = sys.version_info[0] == 2
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


else:  # PY2

    string_types = (basestring,)
    integer_types = (int, long)
    builtins = __import__('__builtin__')
    ast_arg_type = _ast.Name
    execfile = execfile


def get_ast_arg_arg(arg):
    if PY3 and isinstance(arg, _ast.arg):
        return arg.arg
    if isinstance(arg, _ast.Name):
        return arg.id
    if isinstance(arg, string_types):
        return arg
    raise ValueError('UnknownType Passed to get_ast_asg_arg')
