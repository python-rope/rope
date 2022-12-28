import logging
import os.path
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import rope.base.project
from rope.contrib import generate

logging.basicConfig(format="%(levelname)s:%(funcName)s:%(message)s", level=logging.INFO)

RUN_TMP_DIR = tempfile.mkdtemp(prefix="ropetest-run-")


def sample_project(foldername=None, **kwds):
    root = Path(tempfile.mkdtemp(prefix="project-", dir=RUN_TMP_DIR))
    root /= foldername if foldername else "sample_project"
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
    return tuple(map(int, version.split(".")))


def only_for(version):
    """Should be used as a decorator for a unittest.TestCase test method"""
    return unittest.skipIf(
        sys.version_info < parse_version(version),
        f"This test requires at least {version} version of Python.",
    )


def only_for_versions_lower(version):
    """Should be used as a decorator for a unittest.TestCase test method"""
    return unittest.skipIf(
        sys.version_info > parse_version(version),
        f"This test requires version of Python lower than {version}",
    )


def only_for_versions_higher(version):
    """Should be used as a decorator for a unittest.TestCase test method"""
    return unittest.skipIf(
        sys.version_info < parse_version(version),
        f"This test requires version of Python higher than {version}",
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
