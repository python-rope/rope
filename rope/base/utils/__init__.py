import os
import sys
import warnings
from typing import Callable, Concatenate, ParamSpec, TypeVar

_Self = TypeVar("_Self")
_Params = ParamSpec("_Params")
_Result = TypeVar("_Result")


def same_file_path(first, second):
    """Tell whether two filesystem paths name the same existing file.

    Runtime ``__file__`` values and project resource paths may spell one
    file differently (letter case on Windows: ``lib`` vs ``Lib``, links), so
    identity is the filesystem's.  A path that does not name an existing
    file (a frozen or zipped module) is not that source file.
    """
    if not isinstance(first, str) or not isinstance(second, str):
        return False
    try:
        return os.path.samefile(first, second)
    except (OSError, ValueError):
        return False


def saveit(
    func: Callable[Concatenate[_Self, _Params], _Result],
) -> Callable[Concatenate[_Self, _Params], _Result]:
    """A decorator that caches the return value of a function"""

    name = "_" + func.__name__

    def _wrapper(self: _Self, *args: _Params.args, **kwds: _Params.kwargs) -> _Result:
        if not hasattr(self, name):
            setattr(self, name, func(self, *args, **kwds))
        return getattr(self, name)

    return _wrapper


cacheit = saveit


def prevent_recursion(default):
    """A decorator that returns the return value of `default` in recursions"""

    def decorator(func):
        name = "_calling_%s_" % func.__name__

        def newfunc(self, *args, **kwds):
            if getattr(self, name, False):
                return default()
            setattr(self, name, True)
            try:
                return func(self, *args, **kwds)
            finally:
                setattr(self, name, False)

        return newfunc

    return decorator


def ignore_exception(exception_class):
    """A decorator that ignores `exception_class` exceptions"""

    def _decorator(func):
        def newfunc(*args, **kwds):
            try:
                return func(*args, **kwds)
            except exception_class:
                pass

        return newfunc

    return _decorator


def deprecated(message=None):
    """A decorator for deprecated functions"""

    def _decorator(func, message=message):
        if message is None:
            message = "%s is deprecated" % func.__name__

        def newfunc(*args, **kwds):
            warnings.warn(message, DeprecationWarning, stacklevel=2)
            return func(*args, **kwds)

        return newfunc

    return _decorator


def cached(size):
    """A caching decorator based on parameter objects"""

    def decorator(func):
        cached_func = _Cached(func, size)
        return cached_func

    return decorator


class _Cached:
    def __init__(self, func, count):
        self.func = func
        self.cache = []
        self.count = count

    def __call__(self, *args, **kwds):
        key = (args, kwds)
        for cached_key, cached_result in self.cache:
            if cached_key == key:
                return cached_result
        result = self.func(*args, **kwds)
        self.cache.append((key, result))
        if len(self.cache) > self.count:
            del self.cache[0]
        return result

    def __get__(self, instance, owner=None):
        # Decorating a method needs instance binding; otherwise the method's
        # ``self`` would be consumed as the first positional cache argument
        # and the real signature would lose a parameter.
        if instance is None:
            return self
        return _CachedBound(self, instance)


class _CachedBound:
    def __init__(self, cached, instance):
        self.cached = cached
        self.instance = instance

    def __call__(self, *args, **kwds):
        return self.cached(self.instance, *args, **kwds)


def resolve(str_or_obj):
    """Returns object from string"""
    if not isinstance(str_or_obj, str):
        return str_or_obj
    if "." not in str_or_obj:
        str_or_obj += "."
    mod_name, obj_name = str_or_obj.rsplit(".", 1)
    __import__(mod_name)
    mod = sys.modules[mod_name]
    return getattr(mod, obj_name) if obj_name else mod


def guess_def_lineno(module, node):
    """Find the line number for a function or class definition.

    `node` may be either an ast.FunctionDef, ast.AsyncFunctionDef, or ast.ClassDef

    Python 3.8 simply provides this to us, but in earlier versions the ast
    node.lineno points to the first decorator rather than the actual
    definition, so we try our best to find where the definitions are.

    This is to workaround bpo-33211 (https://bugs.python.org/issue33211)
    """

    def is_inline_body():
        # class Foo(object):
        #     def inline_body(): pass
        #     ^                  ^--- body_col_offset
        #     `--- indent_col_offset
        #     def not_inline_body():
        #         pass
        #         ^--- body_col_offset == indent_col_offset
        line = module.lines.get_line(node.body[0].lineno)
        indent_col_offset = len(line) - len(line.lstrip())
        body_col_offset = node.body[0].col_offset
        return indent_col_offset < body_col_offset

    if sys.version_info >= (3, 8) or not hasattr(node, "body"):
        return node.lineno

    possible_def_line = (
        node.body[0].lineno if is_inline_body() else node.body[0].lineno - 1
    )
    return module.logical_lines.logical_line_in(possible_def_line)[0]
