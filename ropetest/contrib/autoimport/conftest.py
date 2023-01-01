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
def build_env_path():
    from build import env

    yield pathlib.Path(env.__file__)


@pytest.fixture
def build_path():
    import build

    # Uses __init__.py so we need the parent

    yield pathlib.Path(build.__file__).parent


@pytest.fixture
def compiled_lib():
    import _sqlite3

    yield "_sqlite3", pathlib.Path(_sqlite3.__file__)
