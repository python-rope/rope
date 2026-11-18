import os
import subprocess
import sys
from textwrap import dedent

import pytest

from rope.base import arguments, evaluate, libutils, pyobjects
from rope.base.project import Project
from rope.refactor.rename import Rename

CLASSES = dedent("""\
    class Owner:
        def __init__(self):
            self.field = 1
        callback = module_callback
    class Child(Owner):
        def __init__(self):
            self.field = 3
    class Other:
        def __init__(self):
            self.field = 2
""")
PREFS = dict(
    save_history=False,
    perform_doa=False,
    automatic_soa=False,
)


def _write_inputs(directory, helper, subject):
    directory.mkdir()
    (directory / "helper.py").write_text(helper, encoding="utf-8")
    (directory / "subject.py").write_text(subject, encoding="utf-8")
    (directory / "sentinel.txt").write_bytes(b"untouched\n")
    return _input_bytes(directory)


def _input_bytes(directory):
    return {
        name: (directory / name).read_bytes()
        for name in ("helper.py", "subject.py", "sentinel.txt")
    }


def _run(directory):
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


@pytest.mark.parametrize("access", ["direct", "saved"])
def test_imported_inherited_function_parameter_rename(tmp_path, access):
    helper_code = dedent("""\
        def module_callback(self, item):
            return item
    """)
    call = (
        "result = Child().callback(item=Other())\n"
        if access == "direct"
        else "saved = Child().callback\nresult = saved(item=Other())\n"
    )
    subject_code = (
        "from helper import module_callback\n"
        + CLASSES
        + call
        + "print(result.field)\n"
    )
    directory = tmp_path / "project"
    original = _write_inputs(directory, helper_code, subject_code)
    before = _run(directory)
    assert before == (0, "2\n", "")
    project = Project(directory, ropefolder=None, save_objectdb=False, **PREFS)
    try:
        helper = project.get_file("helper.py")
        resource = project.get_file("subject.py")
        offset = helper.read().index("item") + 1
        changes = Rename(project, helper, offset).get_changes("renamed")
        assert _input_bytes(directory) == original
        project.do(changes)
        after_helper, after_subject = helper.read(), resource.read()
        assert "def module_callback(self, renamed):" in after_helper
        assert "return renamed" in after_helper
        assert "renamed=Other()" in after_subject
        assert _input_bytes(directory) != original
        assert _run(directory) == before
        assert (directory / "sentinel.txt").read_bytes() == original["sentinel.txt"]

        helper_module = project.get_pymodule(helper)
        subject_module = project.get_pymodule(resource)
        function = helper_module.get_scope().lookup("module_callback").get_object()
        keyword = evaluate.eval_location(
            subject_module, after_subject.index("renamed=Other") + 1
        )
        assert keyword is function.get_parameters()["renamed"]
        assert function.parent is helper_module
        assert function.get_module() is helper_module
        owner = subject_module.get_scope().lookup("Owner").get_object()
        slot = evaluate.eval_location(
            subject_module, after_subject.index("callback = module_callback") + 1
        )
        assert slot is owner["callback"]
        assert slot.get_definition_location()[0] is subject_module
    finally:
        project.close()


def test_imported_inherited_callback_survives_analysis_and_reopen(tmp_path):
    helper_code = dedent("""\
        def module_callback(self, item):
            return self
    """)
    use_code = dedent("""\
        def use(callback, item):
            return callback(item)
    """)
    calls = dedent("""\
        direct = Child().callback(Other())
        saved = Child().callback
        result = use(saved, Other())
        print(result.field)
    """)
    subject_code = "from helper import module_callback\n" + use_code + CLASSES + calls
    directory = tmp_path / "project"
    original = _write_inputs(directory, helper_code, subject_code)
    before = _run(directory)
    assert before == (0, "3\n", "")

    for analyze in (True, False):
        project = Project(
            directory, save_objectdb=True, validate_objectdb=True, **PREFS
        )
        try:
            resource = project.get_file("subject.py")
            helper = project.get_file("helper.py")
            if analyze:
                libutils.analyze_module(project, resource)
            subject_module = project.get_pymodule(resource)
            helper_module = project.get_pymodule(helper)
            scope = subject_module.get_scope()
            child = scope.lookup("Child").get_object()
            function = helper_module.get_scope().lookup("module_callback").get_object()
            use = scope.lookup("use").get_object()
            callback_values = project.pycore.object_info.get_passed_objects(use, 0)
            assert callback_values
            for callback in callback_values:
                assert isinstance(callback, pyobjects.AbstractFunction)
                assert callback.get_name() == function.get_name()
                returned = callback.get_returned_object(
                    arguments.ObjectArguments([scope.lookup("Other")])
                )
                assert returned.get_type() is child
            receivers = project.pycore.object_info.get_passed_objects(function, 0)
            assert any(receiver.get_type() is child for receiver in receivers)
            assert scope.lookup("result").get_object().get_type() is child
            assert function.parent is helper_module
            assert function.get_module() is helper_module
            assert _input_bytes(directory) == original
            assert _run(directory) == before
        finally:
            project.close()
    assert any((directory / ".ropeproject").iterdir())
    assert _input_bytes(directory) == original
