import logging
from types import SimpleNamespace

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


def test_names_from_relative_import(tmp_path):
    source = tmp_path / "mod.py"
    source.write_text("from .sub import helper\n", encoding="utf-8")
    names = list(
        parse.get_names_from_file(
            source, package_name="pkg", process_imports=True
        )
    )
    assert PartialName("helper", NameType.Variable) in names


def test_names_from_relative_import_with_asname(tmp_path):
    source = tmp_path / "mod.py"
    source.write_text("from .sub import helper as h\n", encoding="utf-8")
    names = list(
        parse.get_names_from_file(
            source, package_name="pkg", process_imports=True
        )
    )
    assert PartialName("h", NameType.Variable) in names


def test_names_from_relative_submodule_import(tmp_path):
    source = tmp_path / "mod.py"
    source.write_text("from .sub import thing\n", encoding="utf-8")
    names = list(
        parse.get_names_from_file(
            source, package_name="pkg", process_imports=True
        )
    )
    assert PartialName("thing", NameType.Variable) in names


def test_absolute_import_is_skipped(tmp_path):
    source = tmp_path / "mod.py"
    source.write_text("from os import path\n", encoding="utf-8")
    assert (
        list(
            parse.get_names_from_file(
                source, package_name="pkg", process_imports=True
            )
        )
        == []
    )


def test_same_package_import_is_skipped(tmp_path):
    source = tmp_path / "mod.py"
    source.write_text("from pkg import thing\n", encoding="utf-8")
    assert (
        list(
            parse.get_names_from_file(
                source, package_name="pkg", process_imports=True
            )
        )
        == []
    )


def test_underlined_import_name_is_skipped_by_default(tmp_path):
    source = tmp_path / "mod.py"
    source.write_text("from .sub import _private\n", encoding="utf-8")
    assert (
        list(
            parse.get_names_from_file(
                source, package_name="pkg", process_imports=True
            )
        )
        == []
    )
    names = list(
        parse.get_names_from_file(
            source, package_name="pkg", process_imports=True, underlined=True
        )
    )
    assert PartialName("_private", NameType.Variable) in names


def test_bare_relative_import_is_skipped(tmp_path):
    source = tmp_path / "mod.py"
    source.write_text("from . import helper\n", encoding="utf-8")
    assert (
        list(
            parse.get_names_from_file(
                source, package_name="pkg", process_imports=True
            )
        )
        == []
    )


def test_imports_ignored_without_process_imports(tmp_path):
    source = tmp_path / "mod.py"
    source.write_text("from . import helper\n", encoding="utf-8")
    assert list(parse.get_names_from_file(source, package_name="pkg")) == []


def test_names_from_importfrom_with_plain_name():
    # Defensive branch: names are normally ast.alias nodes, but a plain
    # name must pass through unchanged.
    node = SimpleNamespace(level=1, module="sub", names=["helper"])
    names = list(parse._names_from_importfrom(node, "pkg", False))
    assert PartialName("helper", NameType.Variable) in names
