import os
import pathlib
import sys
from subprocess import check_call
from venv import EnvBuilder

import pytest

from rope.base import resources
from ropetest import testutils


@pytest.fixture(scope="session")
def session_venv(tmpdir_factory):
    path = tmpdir_factory.mktemp("venv")
    venv_path = pathlib.Path(path)

    builder = EnvBuilder(with_pip=True)
    builder.create(venv_path)

    yield venv_path


@pytest.fixture(scope="session")
def session_venv_pyvenv_cfg(session_venv):
    cfg = session_venv / "pyvenv.cfg"
    return dict(line.split(" = ") for line in cfg.read_text().splitlines())


@pytest.fixture(scope="session")
def session_venv_site_packages(session_venv, session_venv_pyvenv_cfg):
    if os.name == 'nt':
        return session_venv / f"Lib/site-packages"
    else:
        major, minor, patch = session_venv_pyvenv_cfg["version"].split(".")
        return session_venv / f"lib/python{major}.{minor}/site-packages"


@pytest.fixture(scope='session')
def session_venv_python_executable(session_venv):
    # Get the path to the Python executable inside the venv
    if os.name == 'nt':
        python_executable = session_venv / 'Scripts' / 'python.exe'
    else:
        python_executable = session_venv / 'bin' / 'python'

    # Yield the Python executable path
    yield python_executable


@pytest.fixture
def project(session_venv, session_venv_site_packages):
    project = testutils.sample_project(
        python_path=[str(session_venv_site_packages)],
    )
    yield project
    testutils.remove_project(project)


@pytest.fixture
def project_path(project):
    yield pathlib.Path(project.address)


@pytest.fixture
def project2(session_venv):
    project = testutils.sample_project(
        "sample_project2",
        python_path=[str(session_venv_site_packages)],
    )
    yield project
    testutils.remove_project(project)


"""
Standard project structure for pytest fixtures
/mod1.py            -- mod1
/pkg1/__init__.py   -- pkg1
/pkg1/mod2.py       -- mod2
"""

@pytest.fixture
def mod1(project) -> resources.File:
    return testutils.create_module(project, "mod1")


@pytest.fixture
def pkg1(project) -> resources.Folder:
    return testutils.create_package(project, "pkg1")


@pytest.fixture
def mod2(project, pkg1) -> resources.Folder:
    return testutils.create_module(project, "mod2", pkg1)


@pytest.fixture(scope="session")
def external_fixturepkg(session_venv, session_venv_python_executable):
    check_call([
        session_venv_python_executable,
        "-m",
        "pip",
        "install",
        "--force-reinstall",
        "ropetest-package-fixtures/external_fixturepkg/dist/external_fixturepkg-1.0.0-py3-none-any.whl",
    ])
    yield
    check_call([sys.executable, "-m", "pip", "uninstall", "--yes", "external-fixturepkg"])
