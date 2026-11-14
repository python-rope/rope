import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import rope
from rope.base import arguments
from rope.base.project import Project


def test_unproved_decodable_return_is_not_used(tmp_path):
    expression = " + ".join(["1"] * 95)
    program = dedent(f"""\
        import sys
        def value(x):
            ignored = {expression}
            return x
        class Marker:
            value = 95
        argument = Marker()
        sys.setrecursionlimit(80)
        result = value(argument)
        print(result.value)
        """)
    (tmp_path / "main.py").write_text(program, encoding="utf-8")
    actual = subprocess.run(
        [sys.executable, "-B", "main.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert (actual.returncode, actual.stdout, actual.stderr) == (0, "95\n", "")
    source = Path(rope.__file__).resolve().parent.parent
    project = Project(
        str(tmp_path), ropefolder=None, perform_doa=True, python_path=[str(source)]
    )
    received = []
    receiver = project.pycore.object_info.doa_data_received

    def observe(data):
        received.append(data)
        receiver(data)

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
        module = project.get_pymodule(project.get_file("main.py"))
        function = module["value"].get_object()
        marker = module["Marker"].get_object()
        calls = [
            item for item in received if item[0][0] == "defined" and item[0][-1] == "2"
        ]
        assert len(calls) == 1 and calls[0][3] is None
        returned = project.pycore.object_info.doi_to_pyobject(calls[0][2])
        assert returned.get_type() is marker
        observed = project.pycore.object_info.get_parameter_objects(function)
        assert observed and observed[0].get_type() is marker
        args = arguments.ObjectArguments([module["argument"]])
        assert project.pycore.object_info.get_exact_returned(function, args) is None
        assert project.pycore.object_info.get_returned(function, args) is None
    finally:
        project.close()
