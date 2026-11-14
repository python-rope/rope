import hashlib
import sys
from textwrap import dedent

from rope.base import arguments, ast
from rope.base.project import Project


def test_deep_function_return_lookup_survives_low_analysis_recursion_limit(tmp_path):
    expression = " + ".join(["1"] * 95)
    source = dedent(f"""\
        def value():
            return {expression}
        """)
    (tmp_path / "main.py").write_text(source, encoding="utf-8")
    project = Project(str(tmp_path), ropefolder=None)
    try:
        function = project.get_pymodule(project.get_file("main.py"))[
            "value"
        ].get_object()
        manager = project.pycore.object_info
        args = arguments.ObjectArguments([])
        original_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(80)
            assert manager.get_exact_returned(function, args) is None
            assert manager.get_returned(function, args) is None
            manager.function_called(function, [])
        finally:
            sys.setrecursionlimit(original_limit)
    finally:
        project.close()


def test_deep_module_provenance_survives_low_analysis_recursion_limit(tmp_path):
    expression = " + ".join(["1"] * 95)
    (tmp_path / "main.py").write_text(
        dedent(f"""\
            def value():
                return 1
            ignored = {expression}
            """),
        encoding="utf-8",
    )
    project = Project(str(tmp_path), ropefolder=None)
    try:
        module = project.get_pymodule(project.get_file("main.py"))
        function = module["value"].get_object()
        manager = project.pycore.object_info
        version = manager._return_version(function)
        digest = hashlib.sha256(
            ast.dump(module.get_ast(), include_attributes=False).encode("utf-8")
        ).hexdigest()
        metadata = ("function-body-v1", version, digest)
        assert manager._doa_return_version(function, metadata) == version
        original_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(80)
            assert manager._doa_return_version(function, metadata) is None
        finally:
            sys.setrecursionlimit(original_limit)
    finally:
        project.close()


def test_low_recursion_observation_preserves_proved_return(tmp_path):
    expression = " + ".join(["1"] * 95)
    (tmp_path / "main.py").write_text(
        dedent(f"""\
            class First: pass
            class Second: pass
            first = First()
            second = Second()
            def value():
                ignored = {expression}
                return first
            """),
        encoding="utf-8",
    )
    project = Project(str(tmp_path), ropefolder=None)
    try:
        module = project.get_pymodule(project.get_file("main.py"))
        function = module["value"].get_object()
        first = module["first"].get_object()
        second = module["second"].get_object()
        args = arguments.ObjectArguments([])
        manager = project.pycore.object_info
        manager.function_called(function, [], first)
        assert manager.get_exact_returned(function, args).get_type() is first.get_type()
        original_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(80)
            manager.function_called(function, [], second)
        finally:
            sys.setrecursionlimit(original_limit)
        assert manager.get_exact_returned(function, args).get_type() is first.get_type()
    finally:
        project.close()


def test_unproved_doa_message_preserves_proved_return_and_parameters(tmp_path):
    expression = " + ".join(["1"] * 95)
    (tmp_path / "main.py").write_text(
        dedent(f"""\
            class First: pass
            class Second: pass
            class Argument: pass
            first = First()
            argument = Argument()
            def value(item):
                ignored = {expression}
                return first
            """),
        encoding="utf-8",
    )
    project = Project(str(tmp_path), ropefolder=None)
    try:
        module = project.get_pymodule(project.get_file("main.py"))
        function = module["value"].get_object()
        first = module["first"].get_object()
        argument = module["argument"].get_object()
        args = arguments.ObjectArguments([module["argument"]])
        manager = project.pycore.object_info
        message = (
            ("defined", "main.py", "6"),
            (("instance", ("defined", "main.py", "Argument")),),
            ("instance", ("defined", "main.py", "Second")),
            None,
        )
        assert manager.doi_to_pyobject(message[0]) is function
        assert (
            manager.doi_to_pyobject(message[2]).get_type()
            is module["Second"].get_object()
        )
        manager.function_called(function, [argument], first)
        assert manager.get_exact_returned(function, args).get_type() is first.get_type()
        original_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(80)
            manager.doa_data_received(message)
        finally:
            sys.setrecursionlimit(original_limit)
        assert manager.get_exact_returned(function, args).get_type() is first.get_type()
        assert manager.get_returned(function, args).get_type() is first.get_type()
        assert (
            manager.get_parameter_objects(function)[0].get_type() is argument.get_type()
        )
    finally:
        project.close()
