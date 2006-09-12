import os
import os.path
import sys

def remove_recursively(file):
    if not os.path.exists(file):
        return
    for root, dirs, files in os.walk(file, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(file)


def run_only_for_25(func):
    """Should be used as a decorator for a unittest.TestCase test"""
    if sys.version.startswith('2.5'):
        return func
    else:
        def do_nothing(self):
            pass
        return do_nothing


def assert_raises(exception_class):
    """Should be used as a decorator for a unittest.TestCase test"""
    def _assert_raises(func):
        def call_func(self, *args, **kws):
            self.assertRaises(exception_class, func, self, *args, **kws)
        return call_func
    return _assert_raises
