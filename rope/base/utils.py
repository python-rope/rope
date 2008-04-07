def cacheit(func):
    """A decorator that caches the return value of a function"""

    name = '_' + func.__name__
    def _wrapper(self, *args, **kwds):
        if not hasattr(self, name):
            setattr(self, name, func(self, *args, **kwds))
        return getattr(self, name)
    return _wrapper


def prevent_recursion(default):
    """A decorator that returns the return value of `default` in recursions"""
    def decorator(func):
        name = '_calling_%s_' % func.__name__
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
