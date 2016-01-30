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

    def execfile(fn, global_vars=None, local_vars=None):
        with open(fn) as f:
            code = compile(f.read(), fn, 'exec')
            exec(code, global_vars or {}, local_vars or {})


else:  # PY2

    string_types = (basestring,)
    integer_types = (int, long)
    builtins = __import__('__builtin__')
    execfile = execfile


def get_param_name(param):
    if PY3 and isinstance(param, _ast.arg):
        return param.arg
    if isinstance(param, _ast.Name):
        return param.id
    raise ValueError('Unknown param type passed')

