import pathlib
import tempfile
from textwrap import dedent
from unittest.mock import MagicMock

import pytest

from rope.base import libutils, pyobjectsdef, resources
from rope.base.project import Project
from rope.contrib import findit
from rope.contrib.autoimport import models
from rope.refactor import occurrences
from rope.refactor.importutils import importinfo
from ropetest import testutils


@pytest.fixture
def project():
    proj = testutils.sample_project()
    yield proj
    testutils.remove_project(proj)


@pytest.fixture
def mod1(project):
    testutils.create_package(project, "pkg1")
    return testutils.create_module(project, "pkg1.mod1")


def test_repr_project():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder).resolve()
        obj = testutils.sample_project(folder)
        assert isinstance(obj, Project)
        assert repr(obj) == f'<rope.base.project.Project "{folder}">'


def test_repr_file(project):
    obj = project.get_file("test/file.py")
    assert isinstance(obj, resources.File)
    assert repr(obj).startswith('<rope.base.resources.File "test/file.py" at 0x')


def test_repr_folder(project):
    obj = project.get_folder("test/folder")
    assert isinstance(obj, resources.Folder)
    assert repr(obj).startswith('<rope.base.resources.Folder "test/folder" at 0x')


def test_repr_pyobjectsdef_pymodule(project, mod1):
    obj = project.get_module("pkg1.mod1")
    assert isinstance(obj, pyobjectsdef.PyModule)
    assert repr(obj).startswith('<rope.base.pyobjectsdef.PyModule "pkg1.mod1" at 0x')


def test_repr_pyobjectsdef_pymodule_without_associated_resource(project):
    obj = pyobjectsdef.PyModule(project.pycore, "a = 1")
    assert isinstance(obj, pyobjectsdef.PyModule)
    assert repr(obj).startswith('<rope.base.pyobjectsdef.PyModule "" at 0x')


def test_repr_pyobjectsdef_pypackage(project, mod1):
    obj = project.get_module("pkg1")
    assert isinstance(obj, pyobjectsdef.PyPackage)
    assert repr(obj).startswith('<rope.base.pyobjectsdef.PyPackage "pkg1" at 0x')


def test_repr_pyobjectsdef_pypackage_without_associated_resource(project, mod1):
    obj = pyobjectsdef.PyPackage(project.pycore)
    assert isinstance(obj, pyobjectsdef.PyPackage)
    assert repr(obj).startswith('<rope.base.pyobjectsdef.PyPackage "" at 0x')


def test_repr_pyobjectsdef_pyfunction(project, mod1):
    code = """def func(arg): pass"""
    mod = libutils.get_string_module(project, code, mod1)
    obj = mod.get_attribute("func").pyobject
    assert isinstance(obj, pyobjectsdef.PyFunction)
    assert repr(obj).startswith(
        '<rope.base.pyobjectsdef.PyFunction "pkg1.mod1::func" at 0x'
    )


def test_repr_pyobjectsdef_pyfunction_without_associated_resource(project):
    code = """def func(arg): pass"""
    mod = libutils.get_string_module(project, code)
    obj = mod.get_attribute("func").pyobject
    assert isinstance(obj, pyobjectsdef.PyFunction)
    assert repr(obj).startswith('<rope.base.pyobjectsdef.PyFunction "::func" at 0x')


def test_repr_pyobjectsdef_pyclass(project, mod1):
    code = """class MyClass: pass"""
    mod = libutils.get_string_module(project, code, mod1)
    obj = mod.get_attribute("MyClass").pyobject
    assert isinstance(obj, pyobjectsdef.PyClass)
    assert repr(obj).startswith(
        '<rope.base.pyobjectsdef.PyClass "pkg1.mod1::MyClass" at 0x'
    )


def test_repr_pyobjectsdef_pyclass_without_associated_resource(project):
    code = """class MyClass: pass"""
    mod = libutils.get_string_module(project, code)
    obj = mod.get_attribute("MyClass").pyobject
    assert isinstance(obj, pyobjectsdef.PyClass)
    assert repr(obj).startswith('<rope.base.pyobjectsdef.PyClass "::MyClass" at 0x')


def test_repr_pyobjectsdef_pycomprehension(project, mod1):
    code = """[a for a in b]"""
    mod = libutils.get_string_module(project, code, mod1)
    mod._create_structural_attributes()
    assert len(mod.defineds) == 1
    obj = mod.defineds[0]
    assert isinstance(obj, pyobjectsdef.PyComprehension)
    assert repr(obj).startswith(
        '<rope.base.pyobjectsdef.PyComprehension "pkg1.mod1::<comprehension>" at 0x'
    )


def test_repr_pyobjectsdef_pycomprehension_without_associated_resource(project):
    code = """[a for a in b]"""
    mod = libutils.get_string_module(project, code)
    mod._create_structural_attributes()
    assert len(mod.defineds) == 1
    obj = mod.defineds[0]
    assert isinstance(obj, pyobjectsdef.PyComprehension)
    assert repr(obj).startswith(
        '<rope.base.pyobjectsdef.PyComprehension "::<comprehension>" at 0x'
    )


def test_repr_findit_location(project, mod1):
    code = dedent("""\
        a = 10
        b = 20
        c = 30
    """)
    mod1.write(code)

    occurrence = MagicMock(
        occurrences.Occurrence,
        resource=project.get_resource("pkg1/mod1.py"),
        lineno=2,
    )
    occurrence.get_word_range.return_value = (11, 13)
    occurrence.is_unsure.return_value = True

    obj = findit.Location(occurrence=occurrence)

    assert repr(obj).startswith(
        '<rope.contrib.findit.Location "pkg1/mod1.py:2 (11-13)" at 0x'
    )


def test_autoimport_models_query(project, mod1):
    expected_repr = '''Query("names WHERE module LIKE (?)", columns=['name', 'module', 'package', 'source', 'type'])'''
    obj = models.Name.search_module_like
    assert isinstance(obj, models.Query)
    assert repr(obj) == expected_repr


def test_autoimport_models_finalquery(project, mod1):
    expected_repr = '''FinalQuery("DELETE FROM packages WHERE package = ?")'''
    obj = models.Package.delete_by_package_name
    assert isinstance(obj, models.FinalQuery)
    assert repr(obj) == expected_repr


def test_repr_normal_import(project):
    obj = importinfo.NormalImport([("abc", None), ("ghi", "jkl")])
    expected_repr = '<NormalImport "import abc, ghi as jkl">'
    assert isinstance(obj, importinfo.NormalImport)
    assert repr(obj) == expected_repr


def test_repr_from_import(project):
    obj = importinfo.FromImport("pkg1.pkg2", 0, [("abc", None), ("ghi", "jkl")])
    expected_repr = '<FromImport "from pkg1.pkg2 import abc, ghi as jkl">'
    assert isinstance(obj, importinfo.FromImport)
    assert repr(obj) == expected_repr


def test_repr_from_import_with_level(project):
    obj = importinfo.FromImport("pkg1.pkg2", 3, [("abc", None), ("ghi", "jkl")])
    expected_repr = '<FromImport "from ...pkg1.pkg2 import abc, ghi as jkl">'
    assert isinstance(obj, importinfo.FromImport)
    assert repr(obj) == expected_repr
