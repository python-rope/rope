"""Utility functions for the autoimport code"""
import pathlib
import sys
from collections import OrderedDict
from typing import List, Optional, Set, Tuple

from rope.base.project import Project

from .defs import PackageType, Source


def _get_package_name_from_path(
    package_path: pathlib.Path,
) -> Optional[Tuple[str, PackageType]]:
    package_name = package_path.name
    if package_name.endswith(".egg-info"):
        return None
    if package_name.endswith(".so"):
        name = package_name.split(".")[0]
        return (name, PackageType.COMPILED)
        # TODO add so handling
    if package_name.endswith(".py"):
        stripped_name = package_name.removesuffix(".py")
        return (stripped_name, PackageType.SINGLE_FILE)
    return (package_name, PackageType.STANDARD)


def _get_modname_from_path(modpath: pathlib.Path, package_path: pathlib.Path) -> str:
    package_name: str = package_path.name
    modname = (
        modpath.relative_to(package_path)
        .as_posix()
        .removesuffix(".py")
        .replace("/", ".")
    )
    modname = package_name if modname == "." else package_name + "." + modname
    return modname


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
    else:
        return Source.UNKNOWN


def _sort_and_deduplicate(results: List[Tuple[str, int]]) -> List[str]:
    if len(results) == 0:
        return []
    results.sort(key=lambda y: y[-1])
    results_sorted = list(zip(*results))[0]
    return list(OrderedDict.fromkeys(results_sorted))


def _sort_and_deduplicate_tuple(
    results: List[Tuple[str, str, int]]
) -> List[Tuple[str, str]]:
    if len(results) == 0:
        return []
    results.sort(key=lambda y: y[-1])
    results_sorted = []
    for result in results:
        results_sorted.append(result[:-1])
    return list(OrderedDict.fromkeys(results_sorted))


def _submodules(mod: pathlib.Path) -> Set[pathlib.Path]:
    """Simple submodule finder that doesn't try to import anything"""
    result = set()
    if mod.is_dir() and (mod / "__init__.py").exists():
        result.add(mod)
        for child in mod.iterdir():
            result |= _submodules(child)
    return result
    return result
