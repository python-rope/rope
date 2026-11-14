"""Ordinary return observations through public dynamic object analysis."""

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

import rope
from rope.base import evaluate, libutils, pyobjects
from rope.base.project import Project

SUBJECT = dedent("""\
    from helper import module_callback
    class Owner:
        def __init__(self):
            self.field = 1
    class Other:
        def __init__(self):
            self.field = 2
    owner = Owner()
    owner.callback = module_callback
    result = module_callback(Other(), Owner())
    print(result.field)
    """)

CONTROLS = dedent("""\
    class Marker:
        pass
    def stable(value):
        return value
    stable_result = stable(Marker())
    items = []
    items.append(Marker())
    saved = items[0]
    """)

MAIN = dedent("""\
    import controls
    import subject
    """)

HELPER_BEFORE = dedent("""\
    def module_callback(self, item):
        return eval("self")
    """)

HELPER_AFTER = dedent("""\
    def module_callback(self, item):
        return eval("item")
    """)

SELF_WRITING_HELPER = dedent("""\
    from pathlib import Path

    def module_callback(self, item):
        Path(__file__).write_bytes(b'from pathlib import Path\\n\\ndef module_callback(self, item):\\n    return eval("item")\\n')
        return eval("self")
    """)

SELF_WRITTEN_HELPER = dedent("""\
    from pathlib import Path

    def module_callback(self, item):
        return eval("item")
    """)

RESOURCES = {
    "subject.py": SUBJECT,
    "controls.py": CONTROLS,
    "main.py": MAIN,
    "sentinel.txt": "untouched\n",
}


def _rope_source():
    return Path(rope.__file__).resolve().parent.parent


def _open_project(directory, validation):
    options = dict(
        ropefolder=".ropeproject",
        save_history=False,
        save_objectdb=True,
        automatic_soa=False,
        perform_doa=True,
        import_dynload_stdmods=False,
        python_path=[str(_rope_source())],
    )
    if validation:
        options["validate_objectdb"] = True
    project = Project(str(directory), **options)
    assert project.prefs.get("validate_objectdb", False) is validation
    return project


def _write_resources(directory, helper):
    directory.mkdir()
    for name, text in dict(RESOURCES, **{"helper.py": helper}).items():
        (directory / name).write_bytes(text.encode("utf-8"))


def _resources(directory):
    return {name: (directory / name).read_bytes() for name in (*RESOURCES, "helper.py")}


def _run_public_doa(project, directory, expected_stdout, helper_after=None):
    before = _resources(directory)
    runmod = project.find_module("rope.base.oi.runmod")
    assert Path(runmod.real_path).resolve() == _rope_source() / "rope/base/oi/runmod.py"
    output_path = directory / "doa-output.log"
    with output_path.open("wb") as output:
        runner = project.pycore.run_module(project.get_file("main.py"), stdout=output)
        try:
            runner.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            runner.kill_process()
            runner.process.wait(timeout=5)
            runner.wait_process()
            raise
        runner.wait_process()
        assert runner.process.returncode == 0
    assert output_path.read_text(encoding="utf-8") == expected_stdout
    expected_resources = dict(before)
    if helper_after is not None:
        expected_resources["helper.py"] = helper_after.encode("utf-8")
    assert _resources(directory) == expected_resources


def _observe(project, expected_result):
    """Keep all semantic stages, then assert the observations at the end."""
    directory = Path(project.address)
    before = _resources(directory)
    consumer = project.get_pymodule(project.get_file("subject.py"))
    helper = project.get_pymodule(project.get_file("helper.py"))
    controls = project.get_pymodule(project.get_file("controls.py"))
    result_offset = consumer.source_code.index("result = module_callback") + 2
    callee_offset = result_offset + len("result = ")
    result_name = evaluate.eval_location(consumer, result_offset)
    value = result_name.get_object() if result_name is not None else None
    callee_name = evaluate.eval_location(consumer, callee_offset)
    callee = callee_name.get_object() if callee_name is not None else None
    canonical = helper["module_callback"].get_object()
    marker = controls["Marker"].get_object()
    observed = project.pycore.object_info.get_parameter_objects(canonical)
    holding = project.pycore.object_info.get_per_name(controls.get_scope(), "items")

    def has_current_type(item, expected):
        return item is not None and item.get_type() is expected

    if expected_result is None:
        result_matches = (
            result_name is not None
            and value is pyobjects.get_unknown()
            and value.get_type() is not consumer["Other"].get_object()
            and value.get_type() is not consumer["Owner"].get_object()
        )
    else:
        result_matches = has_current_type(value, consumer[expected_result].get_object())
    observation = {
        "expected_result": expected_result,
        "result_matches": result_matches,
        "canonical_helper": callee is canonical,
        "helper_parent_current": callee is not None and callee.parent is helper,
        "stable_result": has_current_type(
            controls["stable_result"].get_object(), marker
        ),
        "saved": has_current_type(controls["saved"].get_object(), marker),
        "stable_parameter": has_current_type(
            controls["stable"].get_object().get_scope().lookup("value").get_object(),
            marker,
        ),
        "per_name": has_current_type(holding, marker),
        "parameter_count": observed is not None and len(observed) == 2,
        "parameter_self": has_current_type(
            observed[0] if observed else None, consumer["Other"].get_object()
        ),
        "parameter_item": has_current_type(
            observed[1] if observed and len(observed) > 1 else None,
            consumer["Owner"].get_object(),
        ),
    }
    assert _resources(directory) == before
    return observation


def _assert_observations(observations):
    for observation in observations:
        assert all(
            value for name, value in observation.items() if name != "expected_result"
        ), observation


@pytest.mark.parametrize(
    "validation", [False, True], ids=["default-validation", "validation-enabled"]
)
def test_public_doa_opaque_return_write_reopen_and_unrelated_observations(
    tmp_path, validation
):
    directory = tmp_path / "project"
    _write_resources(directory, HELPER_BEFORE)
    observations = []
    project = _open_project(directory, validation)
    try:
        libutils.analyze_module(project, project.get_file("controls.py"))
        _run_public_doa(project, directory, "2\n")
        observations.append(_observe(project, "Other"))
        project.close()
        project = _open_project(directory, validation)
        observations.append(_observe(project, "Other"))
        before = _resources(directory)
        project.get_file("helper.py").write(HELPER_AFTER)
        before["helper.py"] = HELPER_AFTER.encode("utf-8")
        assert _resources(directory) == before
        project.validate(project.root)
        _run_public_doa(project, directory, "1\n")
        observations.append(_observe(project, "Owner"))
        project.close()
        project = _open_project(directory, validation)
        observations.append(_observe(project, "Owner"))
    finally:
        project.close()
    _assert_observations(observations)


@pytest.mark.parametrize(
    "validation", [False, True], ids=["default-validation", "validation-enabled"]
)
def test_doa_old_frame_self_changes_source_then_fresh_current_return(
    tmp_path, validation
):
    directory = tmp_path / "project"
    _write_resources(directory, SELF_WRITING_HELPER)
    observations = []
    project = _open_project(directory, validation)
    try:
        # Do not preload helper's PyModule or return before its old frame runs.
        libutils.analyze_module(project, project.get_file("controls.py"))
        _run_public_doa(project, directory, "2\n", helper_after=SELF_WRITTEN_HELPER)
        project.validate(project.root)
        observations.append(_observe(project, None))
        _run_public_doa(project, directory, "1\n")
        observations.append(_observe(project, "Owner"))
        project.close()
        project = _open_project(directory, validation)
        observations.append(_observe(project, "Owner"))
    finally:
        project.close()
    _assert_observations(observations)
