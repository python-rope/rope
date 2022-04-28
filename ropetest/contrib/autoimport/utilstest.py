"""Tests for autoimport utility functions, written in pytest"""
import pathlib

from rope.contrib.autoimport import utils
from rope.contrib.autoimport.defs import Package, PackageType, Source


def test_get_package_source(mod1_path, project):
    assert utils.get_package_source(mod1_path, project) == Source.PROJECT


def test_get_package_source_not_project(mod1_path):
    assert utils.get_package_source(mod1_path) == Source.UNKNOWN


def test_get_package_source_pytest(build_path):
    # pytest is not installed as part of the standard library
    # but should be installed into site_packages,
    # so it should return Source.SITE_PACKAGE
    assert utils.get_package_source(build_path) == Source.SITE_PACKAGE


def test_get_package_source_typing(typing_path):

    assert utils.get_package_source(typing_path) == Source.STANDARD


def test_get_modname_project_no_add(mod1_path, project_path):

    assert utils.get_modname_from_path(mod1_path, project_path, False) == "mod1"


def test_get_modname_single_file(typing_path):

    assert utils.get_modname_from_path(typing_path, typing_path) == "typing"


def test_get_modname_folder(build_path, build_env_path):

    assert utils.get_modname_from_path(build_env_path, build_path) == "build.env"


def test_get_package_tuple_sample(project_path):
    assert Package(
        "sample_project", Source.UNKNOWN, project_path, PackageType.STANDARD
    ) == utils.get_package_tuple(project_path)


def test_get_package_tuple_typing(typing_path):

    assert Package(
        "typing", Source.STANDARD, typing_path, PackageType.SINGLE_FILE
    ) == utils.get_package_tuple(typing_path)


def test_get_package_tuple_compiled(zlib_path):
    assert Package(
        "zlib", Source.STANDARD, zlib_path, PackageType.COMPILED
    ) == utils.get_package_tuple(zlib_path)
