import json
import os
import subprocess
import sys
from textwrap import dedent

import pytest

from rope.base import evaluate, pyobjects
from rope.base.project import Project
from rope.refactor.rename import Rename

OWNER = dedent("""\
    class Owner:
        def __init__(self):
            self.field = 1
""")
OTHER = dedent("""\
    class Other:
        def __init__(self):
            self.field = 2
""")
MODULE_FUNCTION = dedent("""\
    def module_callback(self, item):
        return self
""")
CLASS_ALIAS = "    callback = module_callback\n"
PRINT_RESULT = "print(result.field)\n"


def _fixtures():
    stored = MODULE_FUNCTION + OWNER + CLASS_ALIAS + OTHER
    return {
        "direct_instance": (
            stored + "result = Owner().callback(Other())\n" + PRINT_RESULT,
            "Owner",
            "1\n",
        ),
        "saved_bound": (
            stored
            + "saved = Owner().callback\nresult = saved(Other())\n"
            + PRINT_RESULT,
            "Owner",
            "1\n",
        ),
        "class_unbound": (
            stored + "result = Owner.callback(Owner(), Other())\n" + PRINT_RESULT,
            "Owner",
            "1\n",
        ),
        "instance_own_function": (
            stored
            + "instance = Owner()\ninstance.callback = module_callback\n"
            + "result = instance.callback(Other(), Owner())\n"
            + PRINT_RESULT,
            "Other",
            "2\n",
        ),
        "ordinary_method": (
            OWNER
            + "    def callback(self, item):\n        return self\n"
            + OTHER
            + "result = Owner().callback(Other())\n"
            + PRINT_RESULT,
            "Owner",
            "1\n",
        ),
        "lexical_global": (
            OTHER
            + "GLOBAL = Other()\n"
            + "def module_callback(self, item):\n    return GLOBAL\n"
            + OWNER
            + CLASS_ALIAS
            + "result = Owner().callback(Other())\n"
            + PRINT_RESULT,
            "Other",
            "2\n",
        ),
    }


def _run(code, directory):
    compile((directory / "subject.py").read_bytes(), "subject.py", "exec")
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-B", "subject.py"],
        cwd=directory,
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
    )
    return result.returncode, result.stdout, result.stderr


def _project(directory, code):
    directory.mkdir()
    (directory / "subject.py").write_text(code, encoding="utf-8")
    (directory / "sentinel.txt").write_text("untouched\n", encoding="utf-8")
    project = Project(
        directory,
        ropefolder=None,
        save_history=False,
        save_objectdb=False,
        perform_doa=False,
        automatic_soa=False,
    )
    return project, project.get_file("subject.py")


def _query(directory, code, expected_class):
    project, resource = _project(directory, code)
    try:
        module = project.get_pymodule(resource)
        scope = module.get_scope()
        expected_type = scope.lookup(expected_class).get_object()
        other_type = scope.lookup(
            "Other" if expected_class == "Owner" else "Owner"
        ).get_object()
        result = scope.lookup("result").get_object()
        result_type = result.get_type()
        finder = evaluate.ScopeNameFinder(module)
        read = finder.get_pyname_at(
            code.index("print(result.field)") + len("print(result.") + 1
        )
        expected_field = expected_type.get_attribute("field")
        return {
            "expected_class": expected_class,
            "result_unknown": result is pyobjects.get_unknown(),
            "result_type_expected": result_type is expected_type,
            "result_type_other": result_type is other_type,
            "field_is_expected_binding": read is expected_field,
            "field_unknown": read is None
            or read.get_object() is pyobjects.get_unknown(),
        }
    finally:
        project.close()


@pytest.mark.parametrize("fixture_name", list(_fixtures()))
@pytest.mark.parametrize("selected", ["Owner", "Other"])
def test_class_stored_function_field_rename_preserves_execution(
    tmp_path, fixture_name, selected
):
    code, expected_class, expected_stdout = _fixtures()[fixture_name]
    query = _query(tmp_path / "separate-query", code, expected_class)
    project, resource = _project(tmp_path / "cold-rename", code)
    directory = tmp_path / "cold-rename"
    original = {
        path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()
    }
    offset = (
        code.index("self.field = " + ("1" if selected == "Owner" else "2"))
        + len("self.")
        + 1
    )
    evidence = {
        "fixture": fixture_name,
        "selected": selected,
        "query": query,
        "before_source": code,
        "offset": offset,
        "new_name": "changed",
        "cold_project_has_no_query_before_rename": True,
        "original_file_bytes_hex": {
            name: data.hex() for name, data in original.items()
        },
    }
    try:
        before = _run(code, directory)
        evidence["before"] = before
        assert before == (0, expected_stdout, "")
        changes = Rename(project, resource, offset).get_changes("changed")
        assert original == {name: (directory / name).read_bytes() for name in original}
        evidence["changeset_description"] = changes.get_description()
        project.do(changes)
        after_code = resource.read()
        after = _run(after_code, directory)
        evidence.update(
            after_source=after_code,
            after=after,
            actual_source_change=after_code != code,
        )
        assert (directory / "sentinel.txt").read_bytes() == original["sentinel.txt"]
        assert after_code != code
        changed_definition = "self.changed = " + ("1" if selected == "Owner" else "2")
        assert changed_definition in after_code
        evidence["runtime_preserved"] = after == before
        assert after == before, evidence
        expected_read = (
            "print(result.changed)"
            if selected == expected_class
            else "print(result.field)"
        )
        assert expected_read in after_code
        # A known wrong public value is an error; unknown alone is not a red case.
        assert not query["result_type_other"], query
    finally:
        project.close()
        (tmp_path / "evidence.json").write_text(
            json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
        )


@pytest.mark.parametrize("selected", ["class_slot", "module_function"])
def test_class_stored_function_name_rename_preserves_identity(tmp_path, selected):
    code, _, expected_stdout = _fixtures()["direct_instance"]
    directory = tmp_path / "cold-rename"
    project, resource = _project(directory, code)
    original = {
        path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()
    }
    offset = (
        code.index("    callback =") + len("    ") + 1
        if selected == "class_slot"
        else code.index("def module_callback") + len("def ") + 1
    )
    new_name = "renamed_callback"
    evidence = {
        "fixture": "canonical_name_rename",
        "selected": selected,
        "before_source": code,
        "offset": offset,
        "new_name": new_name,
        "cold_project_has_no_query_before_rename": True,
        "original_file_bytes_hex": {
            name: data.hex() for name, data in original.items()
        },
    }
    try:
        before = _run(code, directory)
        evidence["before"] = before
        assert before == (0, expected_stdout, "")
        changes = Rename(project, resource, offset).get_changes(new_name)
        assert original == {name: (directory / name).read_bytes() for name in original}
        evidence["changeset_description"] = changes.get_description()
        project.do(changes)
        after_code = resource.read()
        after = _run(after_code, directory)
        evidence.update(
            after_source=after_code,
            after=after,
            actual_source_change=after_code != code,
        )
        assert (directory / "sentinel.txt").read_bytes() == original["sentinel.txt"]
        assert after_code != code
        assert after == before, evidence
        if selected == "class_slot":
            assert "    renamed_callback = module_callback\n" in after_code
            assert "Owner().renamed_callback(Other())" in after_code
            assert "def module_callback(self, item):" in after_code
        else:
            assert "def renamed_callback(self, item):" in after_code
            assert "    callback = renamed_callback\n" in after_code
            assert "Owner().callback(Other())" in after_code
        evidence["runtime_preserved"] = True
    finally:
        project.close()
        (tmp_path / "evidence.json").write_text(
            json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
        )


@pytest.mark.parametrize("query_order", [("first", "second"), ("second", "first")])
@pytest.mark.parametrize("selected", ["Owner", "SecondOwner"])
def test_shared_class_function_keeps_receivers_separate(
    tmp_path, query_order, selected
):
    code = (
        MODULE_FUNCTION
        + OWNER
        + CLASS_ALIAS
        + "class SecondOwner:\n    def __init__(self):\n        self.field = 3\n"
        + CLASS_ALIAS
        + OTHER
        + "first = Owner().callback(Other())\n"
        + "second = SecondOwner().callback(Other())\n"
        + "print(first.field, second.field)\n"
    )
    query_project, query_resource = _project(tmp_path / "separate-query", code)
    try:
        scope = query_project.get_pymodule(query_resource).get_scope()
        expected_types = {
            "first": scope.lookup("Owner").get_object(),
            "second": scope.lookup("SecondOwner").get_object(),
        }
        other_type = scope.lookup("Other").get_object()
        queries = []
        for name in (*query_order, *query_order):
            value = scope.lookup(name).get_object()
            value_type = value.get_type()
            queries.append(
                {
                    "name": name,
                    "unknown": value is pyobjects.get_unknown(),
                    "type_expected": value_type is expected_types[name],
                    "type_other": value_type is other_type,
                }
            )
    finally:
        query_project.close()
    directory = tmp_path / "cold-rename"
    project, resource = _project(directory, code)
    original = {
        path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()
    }
    offset = (
        code.index("self.field = " + ("1" if selected == "Owner" else "3"))
        + len("self.")
        + 1
    )
    evidence = {
        "fixture": "shared_two_classes-" + "-".join(query_order),
        "selected": selected,
        "queries": queries,
        "before_source": code,
        "offset": offset,
        "new_name": "changed",
        "cold_project_has_no_query_before_rename": True,
        "original_file_bytes_hex": {
            name: data.hex() for name, data in original.items()
        },
    }
    try:
        before = _run(code, directory)
        evidence["before"] = before
        assert before == (0, "1 3\n", "")
        changes = Rename(project, resource, offset).get_changes("changed")
        assert original == {name: (directory / name).read_bytes() for name in original}
        evidence["changeset_description"] = changes.get_description()
        project.do(changes)
        after_code = resource.read()
        after = _run(after_code, directory)
        evidence.update(
            after_source=after_code,
            after=after,
            actual_source_change=after_code != code,
            runtime_preserved=after == before,
        )
        assert (directory / "sentinel.txt").read_bytes() == original["sentinel.txt"]
        assert after_code != code
        assert "self.changed = " + ("1" if selected == "Owner" else "3") in after_code
        assert after == before, evidence
        expected_read = (
            "print(first.changed, second.field)"
            if selected == "Owner"
            else "print(first.field, second.changed)"
        )
        assert expected_read in after_code
        assert not any(item["type_other"] for item in queries), queries
    finally:
        project.close()
        (tmp_path / "evidence.json").write_text(
            json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
        )
