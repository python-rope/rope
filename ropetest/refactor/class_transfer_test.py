import runpy

import pytest

from rope.base.exceptions import RefactoringError
from rope.base.project import Project
from rope.refactor.move import MoveMethod


def test_same_module_transfer_preserves_local_and_global_bindings(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("handler.py")
        resource.write(
            "import math\n"
            "class Handler:\n"
            "    class Helpers:\n"
            "        @staticmethod\n"
            "        def calculate(value):\n"
            "            result = math.floor(value)\n"
            "            return result\n"
        )
        source = resource.read()
        changes = MoveMethod.get_class_changes(
            project,
            [(resource, source.index("calculate"), "calculate")],
            resource,
            source.index("Handler"),
            resources=[resource],
        )
        project.do(changes)
        namespace = runpy.run_path(resource.real_path)
        assert namespace["Handler"].calculate(3.5) == 3
        assert not hasattr(namespace["Handler"].Helpers, "calculate")
    finally:
        project.close()


@pytest.mark.parametrize("declaration", ["factor = 2\n", ""])
def test_same_module_transfer_rejects_unproven_global_identity(tmp_path, declaration):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("handler.py")
        resource.write(
            declaration + "class Handler:\n"
            "    class Helpers:\n"
            "        @staticmethod\n"
            "        def calculate(value):\n"
            "            global factor\n"
            "            return value * factor\n"
        )
        source = resource.read()
        with pytest.raises(
            RefactoringError,
            match="(?:changes binding|Unproven method dependency): factor",
        ):
            MoveMethod.get_class_changes(
                project,
                [(resource, source.index("calculate"), "calculate")],
                resource,
                source.index("Handler"),
                resources=[resource],
            )
        assert resource.read() == source
    finally:
        project.close()


def test_cross_module_transfer_preserves_branch_local_source_binding(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        source = project.root.create_file("source.py")
        destination = project.root.create_file("destination.py")
        source.write(
            "class Source:\n"
            "    @staticmethod\n"
            "    def choose(value):\n"
            "        if value:\n"
            '            msg = f"value: {value}"\n'
            "            raise ValueError(msg)\n"
            "        return value\n"
        )
        destination.write("class Target:\n    pass\n")
        before = runpy.run_path(source.real_path)["Source"]
        assert before.choose(0) == 0
        with pytest.raises(ValueError, match="value: 3"):
            before.choose(3)
        changes = MoveMethod.get_class_changes(
            project,
            [(source, source.read().index("choose"), "choose")],
            destination,
            destination.read().index("Target"),
            resources=[source, destination],
        )
        project.do(changes)
        after = runpy.run_path(destination.real_path)["Target"]
        assert after.choose(0) == 0
        with pytest.raises(ValueError, match="value: 3"):
            after.choose(3)
        assert not hasattr(runpy.run_path(source.real_path)["Source"], "choose")
    finally:
        project.close()


def test_branch_value_overlay_does_not_admit_global_assignment(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        source = project.root.create_file("source.py")
        destination = project.root.create_file("destination.py")
        source.write(
            "msg = 'original'\n"
            "class Source:\n"
            "    @staticmethod\n"
            "    def choose(value):\n"
            "        global msg\n"
            "        if value:\n"
            '            msg = f"value: {value}"\n'
            "        return msg\n"
        )
        destination.write("class Target:\n    pass\n")
        before = source.read(), destination.read()
        with pytest.raises(RefactoringError):
            MoveMethod.get_class_changes(
                project,
                [(source, source.read().index("choose"), "choose")],
                destination,
                destination.read().index("Target"),
                resources=[source, destination],
            )
        assert (source.read(), destination.read()) == before
    finally:
        project.close()


def test_cross_module_transfer_rejects_mutation_through_builtins_namespace(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        origin = project.root.create_file("origin.py")
        target = project.root.create_file("target.py")
        source = (
            "class Origin:\n    @staticmethod\n    def compute():\n"
            "        return 9\n"
        )
        destination = (
            "import builtins\noriginal = builtins.staticmethod\n"
            "builtins.__dict__['staticmethod'] = lambda f: 42\n"
            "class Target:\n    pass\n"
            "builtins.__dict__['staticmethod'] = original\n"
        )
        origin.write(source)
        target.write(destination)
        with pytest.raises(RefactoringError, match="destination namespace bindings"):
            MoveMethod.get_class_changes(
                project,
                [(origin, source.index("compute"), "compute")],
                target,
                destination.index("Target"),
                resources=[origin, target],
            )
        assert origin.read() == source
        assert target.read() == destination
    finally:
        project.close()
