import os.path
import shutil
import sys
import logging
logging.basicConfig(format='%(levelname)s:%(funcName)s:%(message)s',
                    level=logging.INFO)

import rope.base.project
from rope.contrib import generate


def sample_project(root=None, foldername=None, **kwds):
    if root is None:
        root = 'sample_project'
        if foldername:
            root = foldername
        # HACK: Using ``/dev/shm/`` for faster tests
        if os.name == 'posix':
            if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK):
                    root = '/dev/shm/' + root
            elif os.path.isdir('/tmp') and os.access('/tmp', os.W_OK):
                    root = '/tmp/' + root
    logging.debug("Using %s as root of the project.", root)
    # Using these prefs for faster tests
    prefs = {'save_objectdb': False, 'save_history': False,
             'validate_objectdb': False, 'automatic_soa': False,
             'ignored_resources': ['.ropeproject', '*.pyc'],
             'import_dynload_stdmods': False}
    prefs.update(kwds)
    remove_recursively(root)
    project = rope.base.project.Project(root, **prefs)
    return project

create_module = generate.create_module
create_package = generate.create_package


def remove_project(project):
    project.close()
    remove_recursively(project.address)


def remove_recursively(path):
    import time
    # windows sometimes raises exceptions instead of removing files
    if os.name == 'nt' or sys.platform == 'cygwin':
        for i in range(12):
            try:
                _remove_recursively(path)
            except OSError, e:
                if e.errno not in (13, 16, 32):
                    raise
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
    if sys.version_info >= (2, 5, 0):
        return func
    else:
        def do_nothing(self):
            pass
        return do_nothing


def only_for(version):
    """Should be used as a decorator for a unittest.TestCase test method"""
    def decorator(func):
        if sys.version >= version:
            return func
        else:
            def do_nothing(self):
                pass
            return do_nothing
    return decorator


def run_only_for_unix(func):
    """Should be used as a decorator for a unittest.TestCase test method"""
    if os.name == 'posix':
        return func
    else:
        def do_nothing(self):
            pass
        return do_nothing
