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
def example_external_package_module_path(example_external_package):
    from example_external_package import example_module
    yield pathlib.Path(example_module.__file__)


@pytest.fixture
def example_external_package_path(example_external_package):
    import example_external_package

    # Uses __init__.py so we need the parent

    yield pathlib.Path(example_external_package.__file__).parent


@pytest.fixture
def compiled_lib():
    import _sqlite3

    yield "_sqlite3", pathlib.Path(_sqlite3.__file__)
