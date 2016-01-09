import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
PY34 = sys.version_info[0:2] >= (3, 4)

try:
    str = unicode
except NameError:  # PY3

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
