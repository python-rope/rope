import pathlib

import pytest

from ropetest import testutils


@pytest.fixture
def mod1(project):
    mod1 = testutils.create_module(project, "mod1")
    yield mod1


@pytest.fixture
def mod1_path(mod1):
    yield pathlib.Path(mod1.real_path)


@pytest.fixture
def typing_path():
    import typing

    yield pathlib.Path(typing.__file__)


@pytest.fixture
def example_external_package_module_path(external_fixturepkg):
    from external_fixturepkg import mod1
    yield pathlib.Path(mod1.__file__)


@pytest.fixture
def example_external_package_path(external_fixturepkg):
    import external_fixturepkg

    # Uses __init__.py so we need the parent

    yield pathlib.Path(external_fixturepkg.__file__).parent


@pytest.fixture
def compiled_lib():
    import _sqlite3

    yield "_sqlite3", pathlib.Path(_sqlite3.__file__)
