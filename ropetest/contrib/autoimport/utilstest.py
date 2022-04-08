"""Tests for autoimport utility functions, written in pytest"""
import pathlib

from rope.contrib.autoimport import utils
from rope.contrib.autoimport.defs import PackageType, Source


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


def test_get_package_name_sample(project_path):
    package_name, package_type = utils.get_package_name_from_path(project_path)
    assert package_name == "sample_project"
    assert package_type == PackageType.STANDARD


def test_get_package_name_typing(typing_path):
    package_name, package_type = utils.get_package_name_from_path(typing_path)
    assert package_name == "typing"
    assert package_type == PackageType.SINGLE_FILE


def test_get_package_name_compiled(zlib_path):
    package_name, package_type = utils.get_package_name_from_path(zlib_path)
    assert package_name == "zlib"
    assert package_type == PackageType.COMPILED
