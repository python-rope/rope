"""Definitions of types for the Autoimport program."""
from enum import Enum
from typing import Tuple


class Source(Enum):
    """Describes the source of the package, for sorting purposes."""

    PROJECT = 0  # Obviously any project packages come first
    MANUAL = 1  # Placeholder since Autoimport classifies manually added modules 
    BUILTIN = 2
    STANDARD = 3  # We want to favor standard library items
    SITE_PACKAGE = 4
    UNKNOWN = 5


Name = Tuple[str, str, str, int]
Package = Tuple[str]


class PackageType(Enum):
    """Describes the type of package, to determine how to get the names from it."""

    BUILTIN = 0  # No file exists, compiled into python. IE: Sys
    STANDARD = 1  # Just a folder
    COMPILED = 2  # .so module
    SINGLE_FILE = 3  # a .py file
