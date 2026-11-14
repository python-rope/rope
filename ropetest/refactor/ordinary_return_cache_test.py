"""Ordinary function body changes must invalidate returned facts, not observations."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from rope.base import arguments, evaluate, libutils, pyobjects
from rope.base.project import Project

HELPER_BEFORE = dedent("""\
    def module_callback(self, item):
        return self
    """)
HELPER_AFTER = dedent("""\
    def module_callback(self, item):
        return item
    """)
# Exact saved direct-module AB derivation: only the original call line changed.
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
RESOURCES = {
    "helper.py": HELPER_BEFORE,
    "subject.py": SUBJECT,
    "main.py": "import subject\n",
    "sentinel.txt": "untouched\n",
}
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


class Lifecycle:
    def __init__(self, directory, validation):
        self.directory = directory
        self.validation = validation
        self.records = []
        self.project = None
        self.directory.mkdir()
        for name, code in RESOURCES.items():
            (self.directory / name).write_bytes(code.encode("utf-8"))
        self.open()

    def open(self):
        options = dict(
            ropefolder=".ropeproject",
            save_history=False,
            save_objectdb=True,
            automatic_soa=False,
            perform_doa=False,
            import_dynload_stdmods=False,
        )
        if self.validation:
            options["validate_objectdb"] = True
        self.project = Project(str(self.directory), **options)
        assert self.project.prefs.get("validate_objectdb", False) is self.validation

    def close(self):
        if self.project is not None:
            self.project.close()
            self.project = None

    def reopen(self):
        self.close()
        self.open()

    def module(self, name):
        return self.project.get_pymodule(self.project.get_file(name))

    def bytes(self):
        names = set(RESOURCES)
        if (self.directory / "controls.py").exists():
            names.add("controls.py")
        return {
            name: (self.directory / name).read_bytes().hex() for name in sorted(names)
        }

    def runtime(self, stdout):
        execution = subprocess.run(
            [sys.executable, "-B", "main.py"],
            cwd=self.directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        actual = dict(
            returncode=execution.returncode,
            stdout=execution.stdout,
            stderr=execution.stderr,
        )
        assert actual == dict(returncode=0, stdout=stdout, stderr=""), actual
        return actual

    def describe(self, value, module, expected):
        actual_type = value.get_type() if value is not None else None
        actual_name = (
            actual_type.get_name() if hasattr(actual_type, "get_name") else None
        )
        current = module.get_scope().lookup(expected) if expected is not None else None
        target = current.get_object() if current is not None else None
        return dict(
            expected_class=expected,
            actual_class=actual_name,
            unknown=value is pyobjects.get_unknown(),
            absent=value is None,
            matches=value is None if expected is None else actual_type is target,
            type_is_current_Owner=(
                actual_type is module["Owner"].get_object()
                if "Owner" in module
                else None
            ),
            type_is_current_Other=(
                actual_type is module["Other"].get_object()
                if "Other" in module
                else None
            ),
        )

    def observe(self, stage, stdout, expected):
        before = self.bytes()
        execution = self.runtime(stdout)
        consumer = self.module("subject.py")
        helper = self.module("helper.py")
        function = helper["module_callback"].get_object()
        anchor = consumer.source_code.index("result = module_callback")
        offset = anchor + 2
        result_name = evaluate.eval_location(consumer, offset)
        result = result_name.get_object() if result_name is not None else None
        callee_offset = anchor + len("result = ") + 2
        callee_name = evaluate.eval_location(consumer, callee_offset)
        callee = callee_name.get_object() if callee_name is not None else None
        after = self.bytes()
        assert before == after
        record = dict(
            stage=stage,
            runtime=execution,
            resources_before_hex=before,
            resources_after_hex=after,
            offset=offset,
            line=consumer.source_code[:offset].count("\n") + 1,
            callee_offset=callee_offset,
            canonical_helper=callee is function,
            helper_parent_current=callee is not None and callee.parent is helper,
            result=self.describe(result, consumer, expected),
        )
        self.records.append(record)
        return (
            record["canonical_helper"]
            and record["helper_parent_current"]
            and record["result"]["matches"]
        )

    def write_body(self):
        before = self.bytes()
        self.project.get_file("helper.py").write(HELPER_AFTER)
        self.project.validate(self.project.root)
        after = self.bytes()
        assert after["helper.py"] == HELPER_AFTER.encode("utf-8").hex()
        assert all(
            after[name] == value
            for name, value in before.items()
            if name != "helper.py"
        )

    def parameter_observations(self, stage):
        consumer = self.module("subject.py")
        function = self.module("helper.py")["module_callback"].get_object()
        observed = self.project.pycore.object_info.get_parameter_objects(function)
        assert observed is not None and len(observed) == 2
        record = dict(
            stage=stage,
            parameter_self=self.describe(observed[0], consumer, "Other"),
            parameter_item=self.describe(observed[1], consumer, "Owner"),
        )
        self.records.append(record)
        return (
            record["parameter_self"]["matches"] and record["parameter_item"]["matches"]
        )

    def fallback(self, stage, expected):
        consumer = self.module("subject.py")
        function = self.module("helper.py")["module_callback"].get_object()
        # Normal public read with unobserved argument vector; no record injection.
        value = self.project.pycore.object_info.get_returned(
            function,
            arguments.ObjectArguments([None, None]),
        )
        record = dict(stage=stage, fallback=self.describe(value, consumer, expected))
        self.records.append(record)
        return record["fallback"]["matches"]

    def controls(self, stage):
        module = self.module("controls.py")
        marker = module["Marker"].get_object()
        stable = module["stable"].get_object()
        parameter = stable.get_scope().lookup("value").get_object()
        per_name = self.project.pycore.object_info.get_per_name(
            module.get_scope(), "items"
        )
        values = dict(
            stable_result=module["stable_result"].get_object(),
            saved=module["saved"].get_object(),
            stable_parameter=parameter,
            list_per_name=per_name,
        )
        record = dict(
            stage=stage,
            controls={
                name: dict(
                    actual_class=(
                        value.get_type().get_name()
                        if value is not None and hasattr(value.get_type(), "get_name")
                        else None
                    ),
                    matches=value is not None and value.get_type() is marker,
                )
                for name, value in values.items()
            },
        )
        self.records.append(record)
        return all(value["matches"] for value in record["controls"].values())


@pytest.fixture(params=[False, True], ids=["default-validation", "validation-enabled"])
def lifecycle(tmp_path, request):
    instance = Lifecycle(tmp_path / "project", request.param)
    try:
        yield instance
    finally:
        instance.close()
        out = os.environ.get("ORDINARY_RETURN_RECEIPTS")
        if out:
            name = hashlib.sha256(request.node.nodeid.encode("utf-8")).hexdigest()[:16]
            record = dict(
                nodeid=request.node.nodeid,
                validation=request.param,
                resources_final_hex=instance.bytes(),
                observations=instance.records,
            )
            (Path(out) / (name + ".json")).write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )


def test_direct_module_body_write_validate_reopen(lifecycle):
    checks = [lifecycle.observe("initial", "2\n", "Other")]
    lifecycle.write_body()
    checks.append(lifecycle.observe("resource-write-and-validate", "1\n", "Owner"))
    lifecycle.reopen()
    checks.append(lifecycle.observe("close-and-reopen", "1\n", "Owner"))
    assert all(checks), lifecycle.records


def test_body_changes_while_project_closed(lifecycle):
    checks = [lifecycle.observe("initial", "2\n", "Other")]
    lifecycle.close()
    (lifecycle.directory / "helper.py").write_bytes(HELPER_AFTER.encode("utf-8"))
    lifecycle.open()
    lifecycle.project.validate(lifecycle.project.root)
    checks.append(
        lifecycle.observe("cold-reopen-after-external-body-write", "1\n", "Owner")
    )
    assert all(checks), lifecycle.records


def test_fallback_drops_old_return_and_keeps_arguments(lifecycle):
    checks = [
        lifecycle.observe("initial", "2\n", "Other"),
        lifecycle.fallback("initial-fallback", "Other"),
    ]
    lifecycle.write_body()
    checks.append(lifecycle.parameter_observations("parameters-after-body-write"))
    checks.append(lifecycle.fallback("fallback-before-new-body-query", None))
    checks.append(lifecycle.observe("normal-query-new-body", "1\n", "Owner"))
    checks.append(lifecycle.fallback("fallback-after-new-body-query", "Owner"))
    lifecycle.reopen()
    checks.append(lifecycle.parameter_observations("parameters-after-reopen"))
    checks.append(lifecycle.fallback("fallback-after-reopen", "Owner"))
    assert all(checks), lifecycle.records


def test_unmodified_function_parameter_and_per_name_survive(lifecycle):
    lifecycle.project.root.create_file("controls.py").write(CONTROLS)
    libutils.analyze_module(
        lifecycle.project, lifecycle.project.get_file("controls.py")
    )
    checks = [
        lifecycle.observe("initial", "2\n", "Other"),
        lifecycle.controls("initial-controls"),
    ]
    lifecycle.write_body()
    checks.append(lifecycle.controls("controls-after-other-function-body-write"))
    checks.append(
        lifecycle.parameter_observations("changed-function-parameters-preserved")
    )
    lifecycle.reopen()
    checks.append(lifecycle.controls("controls-after-reopen"))
    checks.append(
        lifecycle.parameter_observations("changed-function-parameters-after-reopen")
    )
    assert all(checks), lifecycle.records
