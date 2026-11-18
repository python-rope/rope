"""Public resource contracts used by project consumers."""

import pytest

from rope.base.exceptions import ResourceNotFoundError
from rope.base.project import Project
from rope.base.resources import File, Folder


def test_public_package_and_module_resources(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (tmp_path / "module.py").write_text("")
    initializer_directory = tmp_path / "initializer_directory"
    initializer_directory.mkdir()
    (initializer_directory / "__init__.py").mkdir()
    missing_initializer = tmp_path / "missing_initializer"
    missing_initializer.mkdir()

    project = Project(tmp_path, ropefolder=None, source_folders=[""])
    try:
        package_resource = project.find_module("package")
        module_resource = project.find_module("module")
        assert isinstance(package_resource, Folder)
        assert isinstance(module_resource, File)
        assert package_resource.has_child("__init__.py")
        assert not package_resource.get_child("__init__.py").is_folder()
        assert not module_resource.is_folder()
        assert project.get_folder("initializer_directory").get_child(
            "__init__.py"
        ).is_folder()
        assert not project.get_folder("missing_initializer").has_child("__init__.py")
        assert project.find_module("absent_module") is None
        with pytest.raises(ResourceNotFoundError):
            package_resource.get_child("absent_child")
    finally:
        project.close()
    assert project.ropefolder is None
    assert not (tmp_path / ".ropeproject").exists()
