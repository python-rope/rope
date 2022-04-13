"""Utility functions for the autoimport code."""
import pathlib
import sys
from collections import OrderedDict
from typing import Generator, List, Optional, Tuple

from rope.base.project import Project

from .defs import ModuleCompiled, ModuleFile, ModuleInfo, Package, PackageType, Source


def get_package_tuple(
    package_path: pathlib.Path, project: Optional[Project] = None
) -> Optional[Package]:
    """
    Get package name and type from a path.

    Checks for common issues, such as not being a viable python module
    Returns None if not a viable package.
    """
    package_name = package_path.name
    package_source = get_package_source(package_path, project)
    if package_name.startswith(".") or package_name == "__pycache__":
        return None
    if package_path.is_file():
        if package_name.endswith(".so"):
            name = package_name.split(".")[0]
            return Package(name, package_source, package_path, PackageType.COMPILED)
        if package_name.endswith(".py"):
            stripped_name = package_path.stem
            return Package(
                stripped_name, package_source, package_path, PackageType.SINGLE_FILE
            )
        return None
    if package_name.endswith((".egg-info", ".dist-info")):
        return None
    return Package(package_name, package_source, package_path, PackageType.STANDARD)


def get_package_source(
    package: pathlib.Path, project: Optional[Project] = None
) -> Source:
    """Detect the source of a given package. Rudimentary implementation."""
    if project is not None and package.as_posix().__contains__(project.address):
        return Source.PROJECT
    if package.as_posix().__contains__("site-packages"):
        return Source.SITE_PACKAGE
    if package.as_posix().startswith(sys.prefix):
        return Source.STANDARD
    return Source.UNKNOWN


def get_modname_from_path(
    modpath: pathlib.Path, package_path: pathlib.Path, add_package_name: bool = True
) -> str:
    """Get module name from a path in respect to package."""
    package_name: str = package_path.stem
    rel_path_parts = modpath.relative_to(package_path).parts
    modname = ""
    if len(rel_path_parts) > 0:
        for part in rel_path_parts[:-1]:
            modname += part
            modname += "."
        if rel_path_parts[-1] == "__init__":
            modname = modname[:-1]
        else:
            modname = modname + modpath.stem
    if add_package_name:
        modname = package_name if modname == "" else package_name + "." + modname
    else:
        assert modname != "."
    return modname


def sort_and_deduplicate(results: List[Tuple[str, int]]) -> List[str]:
    """Sort and deduplicate a list of name, source entries."""
    if len(results) == 0:
        return []
    results.sort(key=lambda y: y[-1])
    results_sorted = list(zip(*results))[0]
    return list(OrderedDict.fromkeys(results_sorted))


def sort_and_deduplicate_tuple(
    results: List[Tuple[str, str, int]]
) -> List[Tuple[str, str]]:
    """Sort and deduplicate a list of name, module, source entries."""
    if len(results) == 0:
        return []
    results.sort(key=lambda y: y[-1])
    results_sorted = []
    for result in results:
        results_sorted.append(result[:-1])
    return list(OrderedDict.fromkeys(results_sorted))


def get_files(
    package: Package, underlined: bool = False
) -> Generator[ModuleInfo, None, None]:
    """Find all files to parse in a given path using __init__.py."""
    if package.type in (PackageType.COMPILED, PackageType.BUILTIN):
        yield ModuleCompiled(None, package.name, underlined, process_imports=True)
    elif package.type == PackageType.SINGLE_FILE:
        assert package.path
        assert package.path.suffix == ".py"
        yield ModuleFile(package.path, package.path.stem, underlined)
    else:
        assert package.path
        for file in package.path.glob("*.py"):
            if file.name == "__init__.py":
                yield ModuleFile(
                    file,
                    get_modname_from_path(file.parent, package.path),
                    underlined,
                    process_imports=True,
                )
            else:
                yield ModuleFile(
                    file,
                    get_modname_from_path(file, package.path),
                    underlined,
                )
