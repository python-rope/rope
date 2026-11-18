import json

import pytest

from rope.base import pyobjects
from rope.refactor.rename import Rename
from ropetest.refactor.class_stored_function_test import (
    CLASS_ALIAS,
    MODULE_FUNCTION,
    OTHER,
    OWNER,
    _project,
    _run,
)

PREFIX = MODULE_FUNCTION + OWNER + CLASS_ALIAS + OTHER
INHERITED = (
    PREFIX
    + "class Child(Owner):\n    def __init__(self):\n        self.field = 3\n"
    + "result = Child().callback(Other())\nprint(result.field)\n"
)
CASES = {
    "alias_override": (
        PREFIX
        + "instance = Owner()\nalias = instance\nalias.callback = module_callback\n"
        + "result = instance.callback(Other(), Owner())\nprint(result.field)\n",
        "Other",
        "2\n",
    ),
    "inherited": (INHERITED, "Child", "3\n"),
    "object_base": (
        PREFIX.replace("class Owner:", "class Owner(object):")
        + "result = Owner().callback(Other())\nprint(result.field)\n",
        "Owner",
        "1\n",
    ),
    "different_instance_override": (
        PREFIX
        + "first = Owner()\nsecond = Owner()\nsecond.callback = module_callback\n"
        + "result = first.callback(Other())\nprint(result.field)\n",
        "Owner",
        "1\n",
    ),
}


def _query(directory, code, expected_class):
    project, resource = _project(directory, code)
    try:
        scope = project.get_pymodule(resource).get_scope()
        result = scope.lookup("result").get_object()
        return {
            "unknown": result is pyobjects.get_unknown(),
            "type_expected": result.get_type()
            is scope.lookup(expected_class).get_object(),
        }
    finally:
        project.close()


def _exercise(tmp_path, fixture, code, expected_class, expected_stdout, selected):
    query = _query(tmp_path / "query", code, expected_class)
    directory = tmp_path / "cold"
    project, resource = _project(directory, code)
    original = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
    if selected == "parent_slot":
        offset = code.index("    callback =") + len("    ") + 1
        new_name = "renamed_callback"
    else:
        value = {"Owner": "1", "Other": "2", "Child": "3"}[selected]
        offset = code.index("self.field = " + value) + len("self.") + 1
        new_name = "changed"
    evidence = {
        "fixture": fixture,
        "selected": selected,
        "query": query,
        "before_source": code,
        "offset": offset,
        "new_name": new_name,
        "query_project_separate_from_cold": True,
        "original_bytes_hex": {name: data.hex() for name, data in original.items()},
    }
    try:
        before = _run(code, directory)
        evidence["before"] = before
        assert before == (0, expected_stdout, "")
        changes = Rename(project, resource, offset).get_changes(new_name)
        assert original == {name: (directory / name).read_bytes() for name in original}
        evidence["changeset"] = changes.get_description()
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
        assert after == before, evidence
        if selected == "parent_slot":
            assert "    renamed_callback = module_callback" in after_code
            assert "Child().renamed_callback(Other())" in after_code
        else:
            assert "self.changed = " + value in after_code
            expected_read = (
                "print(result.changed)"
                if selected == expected_class
                else "print(result.field)"
            )
            assert expected_read in after_code
    finally:
        project.close()
        (tmp_path / "evidence.json").write_text(
            json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
        )


@pytest.mark.parametrize("fixture", list(CASES))
@pytest.mark.parametrize("field_role", ["primary", "Other"])
def test_receiver_storage_regressions_preserve_execution(tmp_path, fixture, field_role):
    code, expected_class, stdout = CASES[fixture]
    primary = "Child" if fixture == "inherited" else "Owner"
    selected = primary if field_role == "primary" else "Other"
    _exercise(tmp_path, fixture, code, expected_class, stdout, selected)


def test_inherited_callback_slot_rename_preserves_source_identity(tmp_path):
    _exercise(
        tmp_path, "inherited_parent_slot", INHERITED, "Child", "3\n", "parent_slot"
    )


IMPORTED = (
    "from helper import module_callback\n"
    + OWNER
    + CLASS_ALIAS
    + OTHER
    + "result = Owner().callback(Other())\nprint(result.field)\n"
)


def _imported_project(directory):
    project, resource = _project(directory, IMPORTED)
    helper = project.root.create_file("helper.py")
    helper.write(MODULE_FUNCTION)
    return project, resource, helper


@pytest.mark.parametrize("selected", ["Owner", "Other", "class_slot", "function"])
def test_imported_function_class_storage_preserves_execution(tmp_path, selected):
    query_project, query_resource, query_helper = _imported_project(tmp_path / "query")
    try:
        scope = query_project.get_pymodule(query_resource).get_scope()
        result = scope.lookup("result").get_object()
        function = scope.lookup("module_callback").get_object()
        helper_module = query_project.get_pymodule(query_helper)
        query = {
            "unknown": result is pyobjects.get_unknown(),
            "type_expected": result.get_type() is scope.lookup("Owner").get_object(),
            "function_is_canonical": function
            is helper_module.get_scope().lookup("module_callback").get_object(),
            "function_module_is_helper": function.get_module() is helper_module,
        }
    finally:
        query_project.close()
    directory = tmp_path / "cold"
    project, resource, helper = _imported_project(directory)
    original = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
    target, text = (
        (helper, MODULE_FUNCTION) if selected == "function" else (resource, IMPORTED)
    )
    if selected == "function":
        offset = text.index("module_callback") + 1
        new_name = "renamed_function"
    elif selected == "class_slot":
        offset = text.index("    callback =") + len("    ") + 1
        new_name = "renamed_callback"
    else:
        value = "1" if selected == "Owner" else "2"
        offset = text.index("self.field = " + value) + len("self.") + 1
        new_name = "changed"
    evidence = {
        "fixture": "imported_function",
        "selected": selected,
        "query": query,
        "offset": offset,
        "target": target.path,
        "new_name": new_name,
        "query_project_separate_from_cold": True,
        "before_source": {"subject.py": resource.read(), "helper.py": helper.read()},
        "original_bytes_hex": {name: data.hex() for name, data in original.items()},
    }
    try:
        before = _run(IMPORTED, directory)
        evidence["before"] = before
        assert before == (0, "1\n", "")
        changes = Rename(project, target, offset).get_changes(new_name)
        assert original == {name: (directory / name).read_bytes() for name in original}
        evidence["changeset"] = changes.get_description()
        project.do(changes)
        after_source = {"subject.py": resource.read(), "helper.py": helper.read()}
        after_bytes = {name: (directory / name).read_bytes() for name in original}
        after = _run(resource.read(), directory)
        evidence.update(
            after_source=after_source,
            after_bytes_hex={name: data.hex() for name, data in after_bytes.items()},
            after=after,
            actual_source_change=after_bytes != original,
            runtime_preserved=after == before,
        )
        assert after_bytes["sentinel.txt"] == original["sentinel.txt"]
        assert after_bytes != original
        assert after == before, evidence
        assert query["function_is_canonical"] and query["function_module_is_helper"]
        subject = after_source["subject.py"]
        if selected == "function":
            assert "def renamed_function(" in after_source["helper.py"]
            assert "from helper import renamed_function" in subject
            assert "callback = renamed_function" in subject
        elif selected == "class_slot":
            assert "renamed_callback = module_callback" in subject
            assert "Owner().renamed_callback(Other())" in subject
        else:
            assert "self.changed = " + value in subject
            assert (
                "print(result.changed)"
                if selected == "Owner"
                else "print(result.field)"
            ) in subject
    finally:
        project.close()
        (tmp_path / "evidence.json").write_text(
            json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
        )
