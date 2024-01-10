import os
import pathlib
import sys
import typing
from inspect import getdoc
from os import _exit
from sys import exit

from rope.contrib.autoimport import parse
from rope.contrib.autoimport.defs import Name, NameType, PartialName, Source


def test_typing_names(typing_path):
    names = list(parse.get_names_from_file(typing_path))
    # No docs for typing, its docstrings are SUPER weird
    assert PartialName("Text", NameType.Variable, "", getdoc(typing)) in names


def test_docstring():
    names = list(
        node
        for node in parse.get_names_from_file(pathlib.Path(pathlib.__file__))
        if node.name == "Path"
    )
    assert (
        PartialName("Path", NameType.Class, getdoc(pathlib.Path), getdoc(pathlib) or "")
        in names
    )


def test_find_sys():
    names = list(parse.get_names_from_compiled("sys", Source.BUILTIN))
    print(names)
    assert (
        Name(
            "exit",
            "sys",
            "sys",
            Source.BUILTIN,
            NameType.Function,
            getdoc(exit),
            getdoc(sys),
        )
        in names
    )


def test_find_underlined():
    names = list(parse.get_names_from_compiled("os", Source.BUILTIN, underlined=True))
    assert (
        Name(
            "_exit",
            "os",
            "os",
            Source.BUILTIN,
            NameType.Function,
            getdoc(_exit),
            getdoc(os),
        )
        in names
    )
