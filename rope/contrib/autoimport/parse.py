"""
Functions to find importable names.

Can extract names from source code of a python file, .so object, or builtin module.
"""

import ast
import inspect
import pathlib
from importlib import import_module
from typing import Generator, List, Optional, Tuple

from .defs import Name, NameType, PackageType, Source
from .utils import (get_modname_from_path, get_package_name_from_path,
                    get_package_source, submodules)


def get_names(
    modpath: pathlib.Path,
    modname: str,
    package_name: str,
    package_source: Source,
    underlined: bool = False,
) -> Generator[Name, None, None]:
    """Get all names in the `modname` module, located at modpath.

    `modname` is the name of a module.
    """
    if modpath.is_dir():
        names: List[Name]
        if (modpath / "__init__.py").exists():
            names = get_names_from_file(
                modpath / "__init__.py",
                modname,
                package_name,
                package_source,
                only_all=True,
            )
            if len(names) > 0:
                return names
        names = []
        for file in modpath.glob("*.py"):
            names.extend(
                get_names_from_file(
                    file,
                    modname + f".{file.stem}",
                    package_name,
                    package_source,
                    underlined=underlined,
                )
            )
        return names
    if modpath.suffix == ".py":
        return get_names_from_file(
            modpath, modname, package_name, package_source, underlined=underlined
        )


def parse_all(
    node: ast.Assign, modname: str, package: str, package_source: Source
) -> Generator[Name, None, None]:
    """Parse the node which contains the value __all__ and return its contents."""
    # I assume that the __all__ value isn't assigned via tuple
    assert isinstance(node.value, ast.List)
    for item in node.value.elts:
        assert isinstance(item, ast.Constant)
        name_type: NameType = NameType.Keyword
        # TODO somehow determine the actual value of this since every member of all is a string
        yield Name(str(item.value), modname, package, package_source, name_type)


def get_type_ast(node: ast.AST) -> NameType:
    """Get the lsp type of a node."""
    if isinstance(node, ast.ClassDef):
        return NameType.Class
    if isinstance(node, ast.FunctionDef):
        return NameType.Function
    if isinstance(node, ast.Assign):
        return NameType.Variable
    return NameType.Text  # default value


def find_all(root_node: ast.AST) -> Optional[List[str]]:
    """Find the contents of __all__."""
    for node in ast.iter_child_nodes(root_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                try:
                    assert isinstance(target, ast.Name)
                    if target.id == "__all__":
                        assert isinstance(node.value, ast.List)
                        return node.value.elts
                except (AttributeError, AssertionError):
                    # TODO handle tuple assignment
                    pass
    return None


def get_names_from_file(
    module: pathlib.Path,
    modname: str,
    package: str,
    package_source: Source,
    only_all: bool = False,
    underlined: bool = False,
) -> Generator[Name, None, None]:
    """
    Get all the names from a given file using ast.

    Parameters
    __________
    only_all: bool
        only use __all__ to determine the module's contents
    """
    with open(module, mode="rb") as file:
        try:
            root_node = ast.parse(file.read())
        except SyntaxError as error:
            print(error)
            return
    all = find_all(root_node)
    for node in ast.iter_child_nodes(root_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                try:
                    assert isinstance(target, ast.Name)
                    if underlined or not target.id.startswith("_"):
                        yield Name(
                            target.id,
                            modname,
                            package,
                            package_source,
                            get_type_ast(node),
                        )
                except (AttributeError, AssertionError):
                    # TODO handle tuple assignment
                    pass
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if underlined or not node.name.startswith("_"):
                yield Name(
                    node.name,
                    modname,
                    package,
                    package_source,
                    get_type_ast(node),
                )


def find_all_names_in_package(
    package_path: pathlib.Path,
    recursive=True,
    package_source: Source = None,
    underlined: bool = False,
) -> List[Name]:
    """
    Find all names in a package.

    Parameters
    ----------
    package_path : pathlib.Path
        path to the package
    recursive : bool
        scan submodules in addition to the root directory
    underlined : bool
        include underlined directories
    """
    package_tuple = get_package_name_from_path(package_path)
    if package_tuple is None:
        return []
    package_name, package_type = package_tuple
    if package_source is None:
        package_source = get_package_source(package_path)
    modules: List[Tuple[pathlib.Path, str]] = []
    if package_type is PackageType.SINGLE_FILE:
        modules.append((package_path, package_name))
    elif package_type is PackageType.COMPILED:
        return []
    elif recursive:
        for sub in submodules(package_path):
            modname = get_modname_from_path(sub, package_path)
            if underlined or modname.__contains__("_"):
                continue  # Exclude private items
            modules.append((sub, modname))
    else:
        modules.append((package_path, package_name))
    result: List[Name] = []
    for module in modules:
        result.extend(
            get_names(module[0], module[1], package_name, package_source, underlined)
        )
    return result


def get_type_object(object) -> NameType:
    if inspect.isclass(object):
        return NameType.Class
    if inspect.isfunction(object) or inspect.isbuiltin(object):
        return NameType.Function
    return NameType.Constant


def get_names_from_compiled(
    package: str,
    source: Source,
    underlined: bool = False,
) -> Generator[Name, None, None]:
    """
    Get the names from a compiled module.

    Instead of using ast, it imports the module.
    Parameters
    ----------
    package : str
        package to import. Must be in sys.path
    underlined : bool
        include underlined names
    """
    # builtins is banned because you never have to import it
    # python_crun is banned because it crashes python
    banned = ["builtins", "python_crun"]
    if package in banned or (package.startswith("_") and not underlined):
        return  # Builtins is redundant since you don't have to import it.
    try:
        module = import_module(str(package))
    except ImportError:
        # print(f"couldn't import {package}")
        return
    else:
        for name, value in inspect.getmembers(module):
            if underlined or not name.startswith("_"):
                if (
                    inspect.isclass(value)
                    or inspect.isfunction(value)
                    or inspect.isbuiltin(value)
                ):
                    yield Name(
                        str(name), package, package, source, get_type_object(value)
                    )
