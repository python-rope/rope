import os
import os.path
import shutil
import sys

def remove_recursively(path):
    import time
    if os.name == 'nt':
        for i in range(12):
            try:
                _remove_recursively(path)
            except WindowsError:
                time.sleep(0.3)
            else:
                break
    else:
        _remove_recursively(path)

def _remove_recursively(path):
    if not os.path.exists(path):
        return
    if os.path.isfile(path):
        os.remove(path)
    else:
        shutil.rmtree(path)

def run_only_for_25(func):
    """Should be used as a decorator for a unittest.TestCase test method"""
    major = sys.version_info[0]
    minor = sys.version_info[1]
    if major > 2 or minor > 4:
        return func
    else:
        def do_nothing(self):
            pass
        return do_nothing


def assert_raises(exception_class):
    """Should be used as a decorator for a unittest.TestCase test method"""
    def _assert_raises(func):
        def call_func(self, *args, **kws):
            self.assertRaises(exception_class, func, self, *args, **kws)
        return call_func
    return _assert_raises
