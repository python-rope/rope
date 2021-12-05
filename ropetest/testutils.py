import os.path
import shutil
import sys
import logging

logging.basicConfig(format="%(levelname)s:%(funcName)s:%(message)s", level=logging.INFO)
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import rope.base.project
from rope.contrib import generate


def sample_project(root=None, foldername=None, **kwds):
    if root is None:
        root = "sample_project"
        if foldername:
            root = foldername
        # HACK: Using ``/dev/shm/`` for faster tests
        if os.name == "posix":
            if os.path.isdir("/dev/shm") and os.access("/dev/shm", os.W_OK):
                root = "/dev/shm/" + root
            elif os.path.isdir("/tmp") and os.access("/tmp", os.W_OK):
                root = "/tmp/" + root
    logging.debug("Using %s as root of the project.", root)
    # Using these prefs for faster tests
    prefs = {
        "save_objectdb": False,
        "save_history": False,
        "validate_objectdb": False,
        "automatic_soa": False,
        "ignored_resources": [".ropeproject", "*.pyc"],
        "import_dynload_stdmods": False,
    }
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
    if os.name == "nt" or sys.platform == "cygwin":
        for i in range(12):
            try:
                _remove_recursively(path)
            except OSError as e:
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


def parse_version(version):
    return tuple(map(int, version.split('.')))


def only_for(version):
    """Should be used as a decorator for a unittest.TestCase test method"""
    return unittest.skipIf(
        sys.version_info < parse_version(version),
        "This test requires at least {0} version of Python.".format(version),
    )


def only_for_versions_lower(version):
    """Should be used as a decorator for a unittest.TestCase test method"""
    return unittest.skipIf(
        sys.version_info > parse_version(version),
        "This test requires version of Python lower than {0}".format(version),
    )


def only_for_versions_higher(version):
    """Should be used as a decorator for a unittest.TestCase test method"""
    return unittest.skipIf(
        sys.version_info < parse_version(version),
        "This test requires version of Python higher than {0}".format(version),
    )


def skipNotPOSIX():
    return unittest.skipIf(os.name != "posix", "This test works only on POSIX")


def time_limit(timeout):
    if not any(procname in sys.argv[0] for procname in {"pytest", "py.test"}):
        # no-op when running tests without pytest
        return lambda *args, **kwargs: lambda func: func

    # do a local import so we don't import pytest when running without pytest
    import pytest

    # this prevents infinite loop/recursion from taking forever in CI
    return pytest.mark.time_limit(timeout)
