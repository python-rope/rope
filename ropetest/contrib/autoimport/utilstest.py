"""Tests for autoimport utility functions, written in pytest"""

from pathlib import Path

from rope.contrib.autoimport import utils
from rope.contrib.autoimport.defs import Package, PackageType, Source


def test_get_package_source(mod1_path, project):
    assert utils.get_package_source(mod1_path, project, "") == Source.PROJECT


def test_get_package_source_not_project(mod1_path):
    assert utils.get_package_source(mod1_path, None, "") == Source.UNKNOWN


def test_get_package_source_pytest(example_external_package_path):
    # pytest is not installed as part of the standard library
    # but should be installed into site_packages,
    # so it should return Source.SITE_PACKAGE
    source = utils.get_package_source(example_external_package_path, None, "mod1")
    assert source == Source.SITE_PACKAGE


def test_get_package_source_typing(typing_path):
    assert utils.get_package_source(typing_path, None, "typing") == Source.STANDARD


def test_get_modname_project_no_add(mod1_path, project_path):
    assert utils.get_modname_from_path(mod1_path, project_path, False) == "mod1"


def test_get_modname_single_file(typing_path):
    assert utils.get_modname_from_path(typing_path, typing_path) == "typing"


def test_get_modname_folder(
    example_external_package_path,
    example_external_package_module_path,
):
    modname = utils.get_modname_from_path(
        example_external_package_module_path,
        example_external_package_path,
    )
    assert modname == "external_fixturepkg.mod1"


def test_get_package_tuple_sample(project_path):
    assert Package(
        "sample_project", Source.UNKNOWN, project_path, PackageType.STANDARD
    ) == utils.get_package_tuple(project_path)


def test_get_package_tuple_typing(typing_path):

    assert Package(
        "typing", Source.STANDARD, typing_path, PackageType.SINGLE_FILE
    ) == utils.get_package_tuple(typing_path)


def test_get_package_tuple_compiled(compiled_lib):
    lib_name, lib_path = compiled_lib
    assert Package(
        lib_name, Source.STANDARD, lib_path, PackageType.COMPILED
    ) == utils.get_package_tuple(lib_path)


def test_get_files(project, mod1, pkg1, mod2):
    root: Package = utils.get_package_tuple(project.root.pathlib)
    paths = [m.filepath.relative_to(project.root.pathlib) for m in utils.get_files(root)]
    assert set(paths) == {
        Path("mod1.py"),
        Path("pkg1/__init__.py"),
        Path("pkg1/mod2.py"),
    }
