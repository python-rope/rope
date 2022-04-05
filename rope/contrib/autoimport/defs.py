"""Definitions of types for the Autoimport program"""
from enum import Enum
from typing import Tuple


class Source(Enum):
    PROJECT = 0  # Obviously any project packages come first
    MANUAL = 1  # Any packages manually added are probably important to the user
    BUILTIN = 2
    STANDARD = 3  # We want to favor standard library items
    SITE_PACKAGE = 4
    UNKNOWN = 5


Name = Tuple[str, str, str, int]


class PackageType(Enum):
    BUILTIN = 0
    STANDARD = 1  # Just a folder
    COMPILED = 2  # .so module
    SINGLE_FILE = 3  # a .py file
