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

else:  # PY2

    string_types = (basestring,)
    integer_types = (int, long)
    builtins = __import__('__builtin__')
