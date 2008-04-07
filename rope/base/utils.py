def cacheit(func):
    name = '_' + func.__name__
    def _wrapper(self, *args, **kwds):
        if not hasattr(self, name):
            setattr(self, name, func(self, *args, **kwds))
        return getattr(self, name)
    return _wrapper
