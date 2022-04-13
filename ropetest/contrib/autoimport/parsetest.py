from itertools import chain

from rope.contrib.autoimport import parse
from rope.contrib.autoimport.defs import PackageType, Source


def test_typing_names(typing_path):
    names = list(
        parse.get_names_from_file(
            typing_path, typing_path.stem, typing_path, Source.STANDARD
        )
    )
    print(names)
    assert "Dict" in chain(*names)


def test_get_typing_names(typing_path):
    names = parse.get_names(typing_path, typing_path.stem, typing_path, Source.STANDARD)
    assert "Dict" in chain(*names)


def test_find_all_typing_names(typing_path):
    names = parse.find_all_names_in_package(typing_path)
    assert "Dict" in chain(*names)


def test_find_sys():
    names = parse.get_names_from_compiled("sys", Source.BUILTIN)
    assert "exit" in chain(*names)


def test_find_underlined():
    names = parse.get_names_from_compiled("os", Source.BUILTIN, underlined=True)
    assert "_exit" in chain(*names)
