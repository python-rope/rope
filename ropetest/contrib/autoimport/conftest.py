import importlib.machinery
import importlib.util
import pathlib
import sys

import pytest

from ropetest import testutils


@pytest.fixture
def mod1(project):
    mod1 = testutils.create_module(project, "mod1")
    return mod1


@pytest.fixture
def mod1_path(mod1):
    return pathlib.Path(mod1.real_path)


@pytest.fixture
def typing_path():
    import typing

    return pathlib.Path(typing.__file__)


@pytest.fixture
def example_external_package_module_path(
    session_venv,
    external_fixturepkg,
    session_venv_site_packages,
):
    return session_venv_site_packages / "external_fixturepkg/mod1.py"


@pytest.fixture
def example_external_package_path(
    session_venv,
    external_fixturepkg,
    session_venv_site_packages,
):
    return session_venv_site_packages / "external_fixturepkg"


@pytest.fixture
def compiled_lib():
    """Return one stdlib extension module that this interpreter loads from a file.

    Which modules are shared libraries depends on how the interpreter was
    built (python-build-standalone links _sqlite3 statically, so it has no
    ``__file__``), so the module is discovered from the import system instead
    of being hard-coded.
    """
    for name in sorted(sys.stdlib_module_names):
        spec = importlib.util.find_spec(name)
        if spec is not None and isinstance(
            spec.loader, importlib.machinery.ExtensionFileLoader
        ):
            return name, pathlib.Path(spec.origin)
    pytest.fail("this interpreter loads no stdlib extension module from a file")
