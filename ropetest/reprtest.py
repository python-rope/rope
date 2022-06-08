import tempfile

import pytest

from rope.base import libutils, resources, pyobjectsdef
from rope.base.project import Project
from ropetest import testutils


@pytest.fixture
def project():
    proj = testutils.sample_project()
    yield proj
    testutils.remove_project(proj)


@pytest.fixture
def mod(project):
    return testutils.create_module(project, "mod")


@pytest.fixture
def mod1(project):
    testutils.create_package(project, "pkg1")
    return testutils.create_module(project, "pkg1.mod1")


def test_repr_project():
    with tempfile.TemporaryDirectory() as folder:
        obj = testutils.sample_project(folder)
        assert isinstance(obj, Project)
        assert repr(obj) == f'<rope.base.project.Project "{folder}">'


def test_repr_file(project):
    obj = project.get_file("test/file.py")
    assert isinstance(obj, resources.File)
    assert repr(obj) == '<rope.base.resources.File "test/file.py">'


def test_repr_folder(project):
    obj = project.get_folder("test/folder")
    assert isinstance(obj, resources.Folder)
    assert repr(obj) == '<rope.base.resources.Folder "test/folder">'


def test_repr_pyobjectsdef_pymodule(project, mod1):
    obj = project.get_module("pkg1.mod1")
    assert isinstance(obj, pyobjectsdef.PyModule)
    assert repr(obj) == '<rope.base.pyobjectsdef.PyModule "pkg1.mod1">'


def test_repr_pyobjectsdef_pymodule_without_associated_resource(project):
    obj = pyobjectsdef.PyModule(project.pycore, "a = 1")
    assert isinstance(obj, pyobjectsdef.PyModule)
    assert repr(obj) == '<rope.base.pyobjectsdef.PyModule "">'


def test_repr_pyobjectsdef_pypackage(project, mod1):
    obj = project.get_module("pkg1")
    assert isinstance(obj, pyobjectsdef.PyPackage)
    assert repr(obj) == '<rope.base.pyobjectsdef.PyPackage "pkg1">'


def test_repr_pyobjectsdef_pypackage_without_associated_resource(project, mod1):
    obj = pyobjectsdef.PyPackage(project.pycore)
    assert isinstance(obj, pyobjectsdef.PyPackage)
    assert repr(obj) == '<rope.base.pyobjectsdef.PyPackage "">'
