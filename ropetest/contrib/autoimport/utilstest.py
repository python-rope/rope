"""Tests for autoimport utility functions, written in pytest"""

import sys
import venv
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from rope.contrib.autoimport import utils
from rope.contrib.autoimport.defs import Package, PackageType, Source
from rope.contrib.autoimport.sqlite import AutoImport


def test_get_package_source(mod1_path, project):
    assert utils.get_package_source(mod1_path, project, "") == Source.PROJECT


def test_get_package_source_not_project(mod1_path):
    assert utils.get_package_source(mod1_path, None, "") == Source.UNKNOWN


def test_get_package_source_project_sibling(project):
    sibling = project.root.pathlib.with_name(project.root.pathlib.name + "-other")
    sibling.mkdir()
    module = sibling / "outside.py"
    module.touch()
    try:
        assert utils.get_package_source(module, project, "outside") == Source.UNKNOWN
        escaped = project.root.pathlib / ".." / sibling.name / module.name
        assert utils.get_package_source(escaped, project, "outside") == Source.UNKNOWN
    finally:
        module.unlink()
        sibling.rmdir()


def test_get_package_source_ignored_nested_resource(project):
    folder = project.root.pathlib / "ignored" / "nested"
    folder.mkdir(parents=True)
    module = folder / "outside.py"
    module.touch()
    project.prefs["ignored_resources"] += ["ignored/*"]
    assert utils.get_package_source(module, project, "outside") == Source.UNKNOWN


def test_get_package_source_precedence(project):
    folder = project.root.pathlib / "site-packages"
    folder.mkdir()
    module = folder / "typing.py"
    module.touch()
    assert utils.get_package_source(module, project, "typing") == Source.PROJECT
    assert utils.get_package_source(module, None, "typing") == Source.SITE_PACKAGE
    builtin = sys.builtin_module_names[0]
    assert utils.get_package_source(module, project, builtin) == Source.BUILTIN


def test_get_package_source_project_prefix_is_not_ancestry(project):
    sibling = Path(project.address + "-other") / "module.py"
    assert utils.get_package_source(sibling, project, "module") == Source.UNKNOWN


def test_get_package_source_pytest(example_external_package_path):
    # pytest is not installed as part of the standard library
    # but should be installed into site_packages,
    # so it should return Source.SITE_PACKAGE
    source = utils.get_package_source(example_external_package_path, None, "mod1")
    assert source == Source.SITE_PACKAGE


def test_get_package_source_venv_in_project_dir(example_external_package_path, project):
    # Many Python dev tools create .venv folders inside the project directory.
    # Modules in such folders should count as SITE_PACKAGE files despite
    # technically being inside the project folder.

    # Set up actual venv in project folder:
    project_venv_path = project.root.pathlib/".venv"
    venv.create(project_venv_path)

    # Crude approximation of a package installed into this venv:
    project_venv_site_packages_path = next(project_venv_path.glob("**/*site-packages"))
    project.prefs["python_path"].append(project_venv_site_packages_path)
    module_path = project_venv_site_packages_path / "foo.py"
    module_path.touch()

    # Such directories are normally part of `ignored_resources` (e.g. `.venv`
    # is in there by default):
    project.prefs["ignored_resources"] += [".venv"]

    source = utils.get_package_source(module_path, project, "foo")
    assert source == Source.SITE_PACKAGE


def test_get_package_source_typing(typing_path):
    assert utils.get_package_source(typing_path, None, "typing") == Source.STANDARD


def test_get_modname_project_no_add(mod1_path, project_path):
    assert utils.get_modname_from_path(mod1_path, project_path, False) == "mod1"


def test_get_modname_single_file(typing_path):
    assert utils.get_modname_from_path(typing_path, typing_path) == "typing"


@pytest.mark.parametrize("path_type", [PurePosixPath, PureWindowsPath])
def test_get_modname_path_components(path_type):
    root = path_type("runtime/Lib")
    assert utils.get_modname_from_path(root / "email" / "message.py", root) == (
        "Lib.email.message"
    )
    with pytest.raises(RuntimeError, match="No site-packages allowed here"):
        utils.get_modname_from_path(root / "site-packages" / "cfgv.py", root)


def test_get_modname_external(example_external_package_path):
    assert utils.get_modname_from_path(
        example_external_package_path,
        example_external_package_path,
    ) == "external_fixturepkg"


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


@pytest.mark.parametrize("underlined", [False, True])
def test_get_files_separate_site_packages(tmp_path, project, underlined):
    library = tmp_path / "runtime" / "Lib"
    site_packages = library / "site-packages"
    distribution = site_packages / "fixture_distribution"
    distribution.mkdir(parents=True)
    (library / "stdlib_fixture.py").write_text("stdlib_name = 1\n")
    (site_packages / "cfgv.py").write_text("cfgv_name = 1\n")
    (distribution / "__init__.py").write_text("distribution_name = 1\n")
    (distribution / "module.py").write_text("module_name = 1\n")

    package = utils.get_package_tuple(library)
    assert package.source == Source.UNKNOWN
    assert {module.modname for module in utils.get_files(package, underlined)} == {
        "Lib.stdlib_fixture"
    }
    external = utils.get_package_tuple(distribution)
    assert external.source == Source.SITE_PACKAGE
    assert {module.modname for module in utils.get_files(external, underlined)} == {
        "fixture_distribution",
        "fixture_distribution.module",
    }

    project.prefs["python_path"].extend([str(library.parent), str(site_packages)])
    with AutoImport(project, observe=False, memory=True) as autoimport:
        autoimport.generate_modules_cache(
            ["Lib", "cfgv", "fixture_distribution"],
            single_thread=True,
            underlined=underlined,
        )
        assert autoimport.get_modules("stdlib_name") == ["Lib.stdlib_fixture"]
        assert autoimport.get_modules("cfgv_name") == ["cfgv"]
        assert autoimport.get_modules("distribution_name") == ["fixture_distribution"]
        assert autoimport.get_modules("module_name") == ["fixture_distribution.module"]


def test_get_files_keeps_nested_installation_roots_separate(tmp_path):
    library = tmp_path / "Lib"
    installed = library / "site-packages"
    installed.mkdir(parents=True)
    (library / "stdlib_module.py").write_text("value = 1\n")
    (installed / "dependency.py").write_text("value = 2\n")
    package = utils.get_package_tuple(library)
    assert [module.modname for module in utils.get_files(package)] == [
        "Lib.stdlib_module"
    ]
    dependency = utils.get_package_tuple(installed / "dependency.py")
    assert [module.modname for module in utils.get_files(dependency)] == ["dependency"]
