from rope.contrib.autoimport import parse
from rope.contrib.autoimport.defs import Name, NameType, PartialName, Source


def test_typing_names(typing_path):
    names = list(parse.get_names_from_file(typing_path))
    assert PartialName("Text", NameType.Variable) in names


def test_find_sys():
    names = list(parse.get_names_from_compiled("sys", Source.BUILTIN))
    assert Name("exit", "sys", "sys", Source.BUILTIN, NameType.Function) in names


def test_find_underlined():
    names = list(parse.get_names_from_compiled("os", Source.BUILTIN, underlined=True))
    assert Name("_exit", "os", "os", Source.BUILTIN, NameType.Function) in names
