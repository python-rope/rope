import logging

from rope.contrib.autoimport import parse
from rope.contrib.autoimport.defs import Name, NameType, PartialName, Source


def test_typing_names(typing_path):
    names = list(parse.get_names_from_file(typing_path))
    assert PartialName("Text", NameType.Variable) in names


def test_invalid_source_file_is_skipped_without_writing_to_stdout(tmp_path, caplog, capsys):
    source = tmp_path / "invalid.py"
    source.write_text("€ = 2\n", encoding="utf-8")

    with caplog.at_level(logging.DEBUG, logger=parse.__name__):
        assert list(parse.get_names_from_file(source)) == []

    assert capsys.readouterr().out == ""
    assert f"Skipping invalid source file {source}" in caplog.text


def test_find_sys():
    names = list(parse.get_names_from_compiled("sys", Source.BUILTIN))
    assert Name("exit", "sys", "sys", Source.BUILTIN, NameType.Function) in names


def test_find_underlined():
    names = list(parse.get_names_from_compiled("os", Source.BUILTIN, underlined=True))
    assert Name("_exit", "os", "os", Source.BUILTIN, NameType.Function) in names
