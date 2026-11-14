import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

import rope
from rope.base import arguments
from rope.base.project import Project


@pytest.mark.parametrize("with_argument", [False, True])
def test_dynamic_analysis_does_not_break_lowered_recursion_limit(
    tmp_path, with_argument
):
    expression = " + ".join((["x.value"] if with_argument else []) + ["1"] * 95)
    parameters = "x" if with_argument else ""
    call = "Marker()" if with_argument else ""
    program = dedent(f"""\
        import sys
        def value({parameters}):
            return {expression}
        """)
    if with_argument:
        program += dedent("""\
            class Marker:
                value = 0
            """)
    program += dedent(f"""\
        sys.setrecursionlimit(80)
        print(value({call}))
        """)
    (tmp_path / "main.py").write_text(program, encoding="utf-8")
    original = subprocess.run(
        [sys.executable, "-B", "main.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert (original.returncode, original.stdout, original.stderr) == (0, "95\n", "")
    source = Path(rope.__file__).resolve().parent.parent
    project = Project(
        str(tmp_path), ropefolder=None, perform_doa=True, python_path=[str(source)]
    )
    received = []
    original_receiver = project.pycore.object_info.doa_data_received

    def observe(data):
        received.append(data)
        original_receiver(data)

    project.pycore.object_info.doa_data_received = observe
    try:
        output = tmp_path / "output.log"
        with output.open("wb") as stream:
            runner = project.pycore.run_module(
                project.get_file("main.py"), stdout=stream
            )
            try:
                runner.process.wait(timeout=20)
                runner.wait_process()
            except Exception:
                if runner.process.poll() is None:
                    runner.kill_process()
                    runner.process.wait(timeout=5)
                raise
        assert runner.process.returncode == 0, output.read_text(encoding="utf-8")
        assert output.read_text(encoding="utf-8") == "95\n"
        returns = [
            item for item in received if item[0][0] == "defined" and item[0][-1] == "2"
        ]
        assert returns and all(len(item) == 4 and item[3] is None for item in returns)
        function = project.get_pymodule(project.get_file("main.py"))[
            "value"
        ].get_object()
        args = [None] if with_argument else []
        assert (
            project.pycore.object_info.get_exact_returned(
                function, arguments.ObjectArguments(args)
            )
            is None
        )
        if with_argument:
            observed = project.pycore.object_info.get_parameter_objects(function)
            marker = project.get_pymodule(project.get_file("main.py"))[
                "Marker"
            ].get_object()
            assert observed is not None and len(observed) == 1
            assert observed[0].get_type() is marker
    finally:
        project.close()
