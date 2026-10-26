import os
import subprocess
import sys
from textwrap import dedent

import pytest

from rope.base.exceptions import RefactoringError
from rope.base.project import Project
from rope.refactor.inline import create_inline

NAME_SOURCE = dedent("""\
    def run():
        try:
            target = missing
            print("body")
        except (NameError, TypeError, ValueError):
            print("caught")
    run()
    print("end")
""")


def _run(root):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-B", "-m", "main"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.returncode, result.stdout, result.stderr


def _exercise(tmp_path, sources, expected, refuse=False, selected=None, **options):
    for name, code in sources.items():
        (tmp_path / name).write_text(code, encoding="utf-8")
    (tmp_path / "sentinel.txt").write_text("untouched\n", encoding="utf-8")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    assert _run(tmp_path) == (0, expected, "")
    project = Project(
        tmp_path,
        save_history=False,
        save_objectdb=False,
        validate_objectdb=False,
        automatic_soa=False,
        import_dynload_stdmods=False,
    )
    try:
        resource = project.get_file("subject.py")
        code = resource.read()
        offset = code.index("target") + 1
        if selected == "last_read":
            offset = code.rindex("target") + 1
        if "resources" in options:
            options["resources"] = [
                project.get_file(name) for name in options["resources"]
            ]
        try:
            changes = create_inline(project, resource, offset).get_changes(**options)
        except RefactoringError:
            if not refuse:
                raise
            assert before == {name: (tmp_path / name).read_bytes() for name in before}
            assert _run(tmp_path) == (0, expected, "")
            return
        assert before == {name: (tmp_path / name).read_bytes() for name in before}
        project.do(changes)
        after = _run(tmp_path)
        changed = {
            name: (tmp_path / name).read_text(encoding="utf-8") for name in sources
        }
        assert after == (0, expected, ""), {"after": after, "sources": changed}
        assert not refuse, {"unsafe_removal_accepted": changed, "after": after}
        assert (tmp_path / "sentinel.txt").read_text() == "untouched\n"
        return changed
    finally:
        project.close()


def _single(tmp_path, code, expected, **options):
    return _exercise(
        tmp_path,
        {"subject.py": code, "main.py": "import subject\n"},
        expected,
        **options,
    )


def test_unused_unknown_name_removal_is_atomic(tmp_path):
    _single(tmp_path, NAME_SOURCE, "caught\nend\n", refuse=True)


def test_unused_unknown_name_remove_false_keeps_exception(tmp_path):
    changed = _single(tmp_path, NAME_SOURCE, "caught\nend\n", remove=False)
    assert changed["subject.py"] == NAME_SOURCE


@pytest.mark.parametrize("initializer", ["42", "[1, (-2, {'key': {1, 2}})]"])
def test_unused_literal_removal_preserves_execution(tmp_path, initializer):
    changed = _single(
        tmp_path, NAME_SOURCE.replace("missing", initializer), "body\nend\n"
    )
    assert "target =" not in changed["subject.py"]


@pytest.mark.parametrize("initializer", ["[missing]", "{[]: 42}"])
def test_unused_container_removal_keeps_lookup_or_hash_failure(tmp_path, initializer):
    _single(
        tmp_path,
        NAME_SOURCE.replace("missing", initializer),
        "caught\nend\n",
        refuse=True,
    )


def test_unused_shadowed_empty_set_call_is_not_a_literal(tmp_path):
    code = dedent("""\
        def set():
            print('called')
            return []
        target = set()
        print('end')
    """)
    _single(tmp_path, code, "called\nend\n", refuse=True)


def test_used_name_initializer_is_still_inlined(tmp_path):
    code = dedent("""\
        value = 42
        target = value
        print(target)
    """)
    changed = _single(tmp_path, code, "42\n")
    assert "target =" not in changed["subject.py"]
    assert "print(value)" in changed["subject.py"]


def test_only_current_remove_false_keeps_other_read_and_definition(tmp_path):
    code = "target = 42\nprint(target)\nprint(target)\n"
    changed = _single(
        tmp_path,
        code,
        "42\n42\n",
        selected="last_read",
        only_current=True,
        remove=False,
    )
    assert changed["subject.py"] == "target = 42\nprint(target)\nprint(42)\n"


def test_only_current_removal_with_another_read_is_atomic(tmp_path):
    code = "target = 42\nprint(target)\nprint(target)\n"
    _single(
        tmp_path, code, "42\n42\n", selected="last_read", only_current=True, refuse=True
    )


def test_only_current_removal_with_one_read_is_still_supported(tmp_path):
    changed = _single(
        tmp_path,
        "target = 42\nprint(target)\n",
        "42\n",
        selected="last_read",
        only_current=True,
    )
    assert changed["subject.py"] == "print(42)\n"


def _imported_sources():
    return {
        "subject.py": "value = 42\ntarget = value\n",
        "main.py": "from subject import target\nprint(target)\n",
    }


def test_actual_importer_read_allows_name_initializer_removal(tmp_path):
    changed = _exercise(tmp_path, _imported_sources(), "42\n")
    assert "target =" not in changed["subject.py"]


def test_resources_excluding_a_read_cannot_remove_definition(tmp_path):
    _exercise(
        tmp_path, _imported_sources(), "42\n", resources=["subject.py"], refuse=True
    )


def test_resources_excluding_definition_leave_initializer_in_place(tmp_path):
    sources = _imported_sources()
    changed = _exercise(tmp_path, sources, "42\n", resources=["main.py"])
    assert changed["subject.py"] == sources["subject.py"]


@pytest.mark.parametrize("annotation", ["missing", "record()"])
def test_module_annotation_cannot_be_discarded_with_literal_initializer(
    tmp_path, annotation
):
    code = dedent("""\
        def record():
            print('annotation')
            return int
        try:
            target: ANNOTATION = 42
            print('body')
        except NameError:
            print('caught')
    """).replace("ANNOTATION", annotation)
    main = dedent("""\
        import subject
        try:
            print(subject.__annotations__['target'])
        except (NameError, KeyError):
            print('annotation caught')
    """)
    # Read the actual annotation dictionary, including lazy annotations on 3.14.
    if annotation == "missing":
        expected = (
            "caught\nannotation caught\n"
            if sys.version_info < (3, 14)
            else "body\nannotation caught\n"
        )
    else:
        expected = (
            "annotation\nbody\n<class 'int'>\n"
            if sys.version_info < (3, 14)
            else "body\nannotation\n<class 'int'>\n"
        )
    _exercise(tmp_path, {"subject.py": code, "main.py": main}, expected, refuse=True)


def test_function_local_annotation_does_not_block_pure_unused_initializer(tmp_path):
    code = NAME_SOURCE.replace("target = missing", "target: missing = 42")
    changed = _single(tmp_path, code, "body\nend\n")
    assert "target:" not in changed["subject.py"]


def test_docs_occurrence_is_not_a_runtime_read(tmp_path):
    code = NAME_SOURCE.replace('print("body")', 'print("body")  # target')
    _single(tmp_path, code, "caught\nend\n", docs=True, refuse=True)


@pytest.mark.parametrize("remove", [True, False])
def test_dormant_load_does_not_erase_initializer_evaluation(tmp_path, remove):
    code = dedent("""\
        def run():
            try:
                target = missing
                if False:
                    print(target)
                print("body")
            except (NameError, TypeError, ValueError):
                print("caught")
        run()
        print("end")
    """)
    _single(tmp_path, code, "caught\nend\n", remove=remove, refuse=remove)


def test_used_unknown_name_keeps_exception_before_intervening_print(tmp_path):
    code = NAME_SOURCE.replace('print("body")', 'print("body")\n        print(target)')
    _single(tmp_path, code, "caught\nend\n", refuse=True)


def test_used_module_annotation_keeps_observed_effect(tmp_path):
    code = dedent("""\
        import sys
        import typing
        def record():
            print('annotation')
            return int
        target: record() = 42
        print(target)
        typing.get_type_hints(sys.modules[__name__])
        print('end')
    """)
    expected = (
        "annotation\n42\nend\n"
        if sys.version_info < (3, 14)
        else "42\nannotation\nend\n"
    )
    _single(tmp_path, code, expected, refuse=True)


def test_used_name_bound_in_outer_module_is_still_inlined(tmp_path):
    code = dedent("""\
        value = 42
        def run():
            target = value
            print(target)
        run()
    """)
    changed = _single(tmp_path, code, "42\n")
    assert "target =" not in changed["subject.py"]
    assert "print(value)" in changed["subject.py"]


def test_unused_bound_name_can_be_removed_without_discarding_an_effect(tmp_path):
    code = "value = 42\ntarget = value\nprint('end')\n"
    changed = _single(tmp_path, code, "end\n")
    assert changed["subject.py"] == "value = 42\nprint('end')\n"


def test_deleted_outer_name_cannot_be_discarded_with_unused_initializer(tmp_path):
    code = dedent("""\
        value = 42
        def run():
            try:
                target = value
                print('body')
            except NameError:
                print('caught')
        del value
        run()
        print('end')
    """)
    _single(tmp_path, code, "caught\nend\n", refuse=True)


def test_unrelated_local_deletion_does_not_block_outer_name_initializer(tmp_path):
    code = dedent("""\
        value = 42
        def unrelated():
            value = 0
            del value
        def run():
            target = value
            print(target)
        unrelated()
        run()
    """)
    changed = _single(tmp_path, code, "42\n")
    assert "target =" not in changed["subject.py"]
    assert "print(value)" in changed["subject.py"]


def test_builtin_name_alias_is_still_inlined(tmp_path):
    code = "target = len\nprint(target([1, 2]))\n"
    changed = _single(tmp_path, code, "2\n")
    assert changed["subject.py"] == "print(len([1, 2]))\n"
    assert changed["main.py"] == "import subject\n"


def test_function_parameter_alias_is_still_inlined(tmp_path):
    code = dedent("""\
        def run(value):
            target = value
            print(target)
        run(42)
    """)
    changed = _single(tmp_path, code, "42\n")
    assert changed["subject.py"] == dedent("""\
        def run(value):
            print(value)
        run(42)
    """)
    assert changed["main.py"] == "import subject\n"


def test_same_module_function_alias_is_still_inlined(tmp_path):
    code = dedent("""\
        def value():
            return 42
        target = value
        print(target())
    """)
    changed = _single(tmp_path, code, "42\n")
    assert changed["subject.py"] == dedent("""\
        def value():
            return 42
        print(value())
    """)
    assert changed["main.py"] == "import subject\n"


def test_imported_module_alias_is_still_inlined(tmp_path):
    code = "import math as value\ntarget = value\nprint(target.sqrt(4))\n"
    changed = _single(tmp_path, code, "2.0\n")
    assert changed["subject.py"] == "import math as value\nprint(value.sqrt(4))\n"
    assert changed["main.py"] == "import subject\n"


def test_imported_value_alias_is_still_inlined(tmp_path):
    code = "from math import pi as value\ntarget = value\nprint(target)\n"
    changed = _single(tmp_path, code, "3.141592653589793\n")
    assert changed["subject.py"] == "from math import pi as value\nprint(value)\n"
    assert changed["main.py"] == "import subject\n"


def test_outer_name_remains_bound_across_unrelated_literal_and_pass(tmp_path):
    code = dedent("""\
        value = 42
        unrelated = 0
        pass
        def run():
            target = value
            print(target)
        run()
    """)
    changed = _single(tmp_path, code, "42\n")
    assert changed["subject.py"] == dedent("""\
        value = 42
        unrelated = 0
        pass
        def run():
            print(value)
        run()
    """)
    assert changed["main.py"] == "import subject\n"


def test_class_name_alias_removal_is_conservatively_atomic(tmp_path):
    code = dedent("""\
        class Box:
            value = 42
            target = value
            print(target)
        print(Box.value)
    """)
    _single(tmp_path, code, "42\n42\n", refuse=True)
