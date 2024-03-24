import pathlib

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
    import _sqlite3

    return "_sqlite3", pathlib.Path(_sqlite3.__file__)
