import re
import subprocess
import sys
import textwrap

import pytest

from rope.base import evaluate, exceptions, pyobjects
from rope.base.project import Project
from rope.refactor.rename import Rename

CLASSES = textwrap.dedent("""class First:
    def __init__(self):
        self.field = 1
class Other:
    def __init__(self):
        self.field = 2
""")
BOX = textwrap.dedent("""class Box:
    def __init__(self):
        self.field = 0
""")


def driver(code, directory):
    compile(code, "subject.py", "exec")
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return {"exit": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def exercise(
    tmp_path,
    code,
    field,
    expected,
    reject=False,
    warm=False,
    replacement=None,
    uncertain_classes=("Box",),
):
    directory = tmp_path
    record = {
        "source": code,
        "expected": expected,
        "field": field,
        "expected_rejection": reject,
    }
    project = Project(
        str(directory),
        ropefolder=None,
        save_history=False,
        save_objectdb=False,
        perform_doa=False,
    )
    try:
        resource = project.root.create_file("subject.py")
        resource.write(code)
        record["before"] = driver(code, directory)
        assert record["before"]["exit"] == 0 and record["before"]["stdout"] == expected

        def inspect():
            module = project.get_pymodule(resource)
            finder = evaluate.ScopeNameFinder(module)
            rows = []
            # Late-first queries stress the same cache without inventing values.
            for match in reversed(list(re.finditer(r"\.field\b", resource.read()))):
                pyname = finder.get_pyname_at(match.start() + 2)
                rows.append(
                    {
                        "offset": match.start() + 2,
                        "none": pyname is None,
                        "definition": (
                            pyname.get_definition_location()[1] if pyname else None
                        ),
                    }
                )
            for class_name in ["Box", "Base", "Child"]:
                pyname = module.get_scope().lookup(class_name)
                if pyname is not None:
                    obj = pyname.get_object()
                    if (
                        isinstance(obj, pyobjects.AbstractClass)
                        and "slot" in obj.get_attributes()
                    ):
                        slot = obj.get_attribute("slot")
                        rows.append(
                            {
                                "class": class_name,
                                "slot_unknown": slot.get_object()
                                is pyobjects.get_unknown(),
                                "slot_definition": slot.get_definition_location()[1],
                            }
                        )
            return rows

        if warm:
            record["warm_queries"] = inspect()
            record["hot_queries"] = inspect()
        if replacement is not None:
            resource.write(replacement)
            code = replacement
            record["replacement_source"] = code
            record["replacement_before"] = driver(code, directory)
            assert record["replacement_before"]["exit"] == 0
        before_bytes = resource.read_bytes()
        offset = (
            code.index(field) + 1
            if isinstance(field, str)
            else code.index(f"self.field = {field}") + len("self.") + 1
        )
        record["selected_offset"] = offset
        try:
            changes = Rename(project, resource, offset).get_changes("changed")
        except exceptions.RefactoringError as error:
            record["refactor_error"] = str(error)
            record["atomic_unchanged"] = resource.read_bytes() == before_bytes
            assert reject, error
            assert record["atomic_unchanged"]
            record["after_source"] = resource.read()
            record["after"] = driver(record["after_source"], directory)
        else:
            project.do(changes)
            record["after_source"] = resource.read()
            record["after"] = driver(record["after_source"], directory)
            if reject:
                pytest.fail(
                    "Ambiguous data field Rename was accepted instead of atomically rejected"
                )
        expected_after = record.get("replacement_before", record["before"])
        assert (
            record["after"]["exit"] == 0
            and record["after"]["stdout"] == expected_after["stdout"]
        ), record["after"]
        record["final_queries"] = inspect()
        if reject:
            assert all(
                row["slot_unknown"]
                for row in record["final_queries"]
                if row.get("class") in uncertain_classes
            )
    finally:
        project.close()


@pytest.mark.parametrize("read", ["Box.slot", "Box().slot"])
@pytest.mark.parametrize("placeholder", [False, True])
@pytest.mark.parametrize("field", [1, 2])
def test_single_external_data_field_rename(tmp_path, read, placeholder, field):
    box = BOX + ("    slot = None\n" if placeholder else "")
    code = (
        CLASSES
        + box
        + textwrap.dedent(f"Box.slot = Other()\nresult = {read}\nprint(result.field)\n")
    )
    exercise(tmp_path, code, field, "2\n")


@pytest.mark.parametrize("field", [1, 2])
def test_rhs_uses_module_namespace_and_stable_data_variable(tmp_path, field):
    code = (
        CLASSES
        + BOX
        + textwrap.dedent(
            "    Other = First\n    slot = None\npeer = Other()\nBox.slot = peer\nresult = Box().slot\nprint(result.field)\n"
        )
    )
    exercise(tmp_path, code, field, "2\n", warm=True)


def test_unrelated_same_named_attribute_does_not_poison_supported_data(tmp_path):
    code = (
        CLASSES
        + textwrap.dedent("class Unrelated:\n    slot = First()\n")
        + BOX
        + textwrap.dedent(
            "print(Unrelated.slot.field)\nBox.slot = Other()\nprint(Box().slot.field)\n"
        )
    )
    exercise(tmp_path, code, 2, textwrap.dedent("1\n2\n"), warm=True)


def test_resource_write_invalidates_external_data_value_and_canonical_fields(tmp_path):
    code = (
        CLASSES
        + BOX
        + textwrap.dedent(
            "Box.slot = Other()\nresult = Box().slot\nprint(result.field)\n"
        )
    )
    replacement = code.replace("Box.slot = Other()", "Box.slot = First()")
    exercise(tmp_path, code, 1, "2\n", warm=True, replacement=replacement)


@pytest.mark.parametrize("saved", [False, True])
@pytest.mark.parametrize("field", [1, 2])
def test_early_read_and_saved_value_are_unknown_and_atomic(tmp_path, saved, field):
    box = BOX + "    slot = First()\n"
    early = (
        textwrap.dedent("saved = Box().slot\nprint(saved.field)\n")
        if saved
        else "print(Box.slot.field)\n"
    )
    code = (
        CLASSES
        + box
        + early
        + textwrap.dedent("Box.slot = Other()\nprint(Box().slot.field)\n")
    )
    exercise(tmp_path, code, field, textwrap.dedent("1\n2\n"), reject=True, warm=True)


@pytest.mark.parametrize("field", [1, 2])
def test_repeated_data_writes_are_unknown_and_atomic(tmp_path, field):
    code = (
        CLASSES
        + BOX
        + textwrap.dedent(
            "Box.slot = First()\nBox.slot = Other()\nprint(Box.slot.field)\n"
        )
    )
    exercise(tmp_path, code, field, "2\n", reject=True)


@pytest.mark.parametrize("field", [1, 2])
def test_conditional_data_only_blocks_affected_field(tmp_path, field):
    code = (
        CLASSES
        + BOX
        + textwrap.dedent("if True:\n    Box.slot = Other()\nprint(Box().slot.field)\n")
    )
    exercise(tmp_path, code, field, "2\n", reject=field == 2, warm=True)


@pytest.mark.parametrize("field", [1, 2])
def test_rebound_class_and_saved_class_alias_are_unknown_and_atomic(tmp_path, field):
    code = (
        CLASSES
        + BOX
        + textwrap.dedent(
            "    slot = First()\nclass Replacement:\n    slot = First()\nold = Box\nBox = Replacement\nBox.slot = Other()\nprint(old.slot.field)\nprint(Box.slot.field)\n"
        )
    )
    exercise(tmp_path, code, field, textwrap.dedent("1\n2\n"), reject=True, warm=True)


@pytest.mark.parametrize("field", [1, 2])
def test_inheritance_does_not_merge_base_and_child_values(tmp_path, field):
    code = CLASSES + textwrap.dedent(
        "class Base:\n    slot = None\nclass Child(Base):\n    slot = First()\nBase.slot = Other()\nprint(Child.slot.field)\nprint(Base.slot.field)\n"
    )
    exercise(
        tmp_path,
        code,
        field,
        textwrap.dedent("1\n2\n"),
        reject=field == 2,
        warm=True,
        uncertain_classes=("Base",),
    )


@pytest.mark.parametrize("field", [0, "marker"])
def test_uncertain_data_does_not_block_unrelated_class_or_global_rename(
    tmp_path, field
):
    code = (
        "marker = 42\n"
        + CLASSES
        + BOX
        + textwrap.dedent(
            "if True:\n    Box.slot = Other()\nprint(marker)\nprint(Box().slot.field)\n"
        )
    )
    exercise(tmp_path, code, field, textwrap.dedent("42\n2\n"), warm=True)


@pytest.mark.parametrize("field", [1, 2])
def test_instance_attribute_and_class_data_remain_distinct_or_unknown(tmp_path, field):
    code = CLASSES + textwrap.dedent(
        "class Box:\n    def __init__(self):\n        self.field = 0\n        self.slot = First()\nBox.slot = Other()\nprint(Box().slot.field)\nprint(Box.slot.field)\n"
    )
    exercise(tmp_path, code, field, textwrap.dedent("1\n2\n"), reject=True, warm=True)


def test_deferred_data_read_is_unknown_and_atomic(tmp_path):
    code = (
        CLASSES
        + BOX
        + textwrap.dedent(
            "def read():\n    return Box.slot\nBox.slot = Other()\nprint(read().field)\n"
        )
    )
    exercise(tmp_path, code, 2, "2\n", reject=True, warm=True)


@pytest.mark.parametrize(
    "rhs",
    [
        "callback",
        "lambda self, item: self",
        "staticmethod(callback)",
        "classmethod(callback)",
    ],
)
def test_ordinary_callable_negative_control_retains_legacy_boundary(tmp_path, rhs):
    if rhs == "staticmethod(callback)":
        definition = textwrap.dedent("def callback(item):\n    return item\n")
        expected, field = "2\n", 1
    elif rhs == "classmethod(callback)":
        definition = textwrap.dedent("def callback(cls, item):\n    return item\n")
        expected, field = "2\n", 1
    else:
        definition = textwrap.dedent("def callback(self, item):\n    return self\n")
        expected, field = "0\n", 2
    code = (
        CLASSES
        + definition
        + BOX
        + textwrap.dedent(
            f"Box.callback = {rhs}\nresult = Box().callback(Other())\nprint(result.field)\n"
        )
    )
    exercise(tmp_path, code, field, expected, warm=True)


def test_custom_descriptor_negative_control_is_not_new_data_support(tmp_path):
    code = (
        CLASSES
        + textwrap.dedent(
            "class Descriptor:\n    def __get__(self, instance, owner):\n        return Other()\n"
        )
        + BOX
        + textwrap.dedent("Box.callback = Descriptor()\nprint(Box().callback.field)\n")
    )
    exercise(tmp_path, code, 1, "2\n", warm=True)


@pytest.mark.parametrize("warm", [False, True])
def test_new_public_query_canonical_identity_and_resource_refresh(tmp_path, warm):
    directory = tmp_path
    code = (
        CLASSES
        + BOX
        + textwrap.dedent(
            "Box.slot = Other()\nresult = Box().slot\nprint(result.field)\n"
        )
    )
    project = Project(
        str(directory),
        ropefolder=None,
        save_history=False,
        save_objectdb=False,
        perform_doa=False,
    )
    record = {"source": code}
    try:
        resource = project.root.create_file("subject.py")
        resource.write(code)
        record["before"] = driver(code, directory)
        assert record["before"]["exit"] == 0 and record["before"]["stdout"] == "2\n"

        def query(expected):
            module = project.get_pymodule(resource)
            scope = module.get_scope()
            data_class = scope.lookup(expected).get_object()
            finder = evaluate.ScopeNameFinder(module)
            field = data_class.get_attribute("field")
            result = scope.lookup("result").get_object()
            assert result.get_type() is data_class
            field_read = finder.get_pyname_at(
                resource.read().index("print(result.field)") + len("print(result.") + 1
            )
            assert field_read is field
            box = scope.lookup("Box").get_object()
            slot = box.get_attribute("slot")
            write_name = finder.get_pyname_at(
                resource.read().index("Box.slot") + len("Box.") + 1
            )
            read_name = finder.get_pyname_at(
                resource.read().index("Box().slot") + len("Box().") + 1
            )
            assert write_name is read_name is slot
            assert slot.get_object().get_type() is data_class
            assert slot.get_definition_location()[0] is module
            assert (
                slot.get_definition_location()[1]
                == resource.read()[: resource.read().index("Box.slot")].count("\n") + 1
            )
            return module, slot, field

        old_module, old_slot, old_field = query("Other")
        if warm:
            assert query("Other") == (old_module, old_slot, old_field)
        replacement = code.replace("Box.slot = Other()", "Box.slot = First()")
        resource.write(replacement)
        new_module, new_slot, new_field = query("First")
        assert (
            new_module is not old_module
            and new_slot is not old_slot
            and new_field is not old_field
        )
        record["after_resource_write"] = driver(replacement, directory)
        assert (
            record["after_resource_write"]["exit"] == 0
            and record["after_resource_write"]["stdout"] == "1\n"
        )
        record["canonical_identity_passed"] = True
    finally:
        project.close()


@pytest.mark.parametrize(
    "lookup",
    ["holder-getattribute", "holder-getattr", "metaclass", "decorator", "rhs-new"],
)
def test_new_lookup_rewriting_boundary_is_unknown_and_atomic(tmp_path, lookup):
    if lookup == "holder-getattribute":
        box = BOX + textwrap.indent(
            textwrap.dedent(
                "    def __getattribute__(self, name):\n        if name == 'slot':\n            return First()\n        return super().__getattribute__(name)\n"
            ),
            "    ",
        )
        code = (
            CLASSES
            + box
            + textwrap.dedent("Box.slot = Other()\nprint(Box().slot.field)\n")
        )
        field, expected = 1, "1\n"
    elif lookup == "holder-getattr":
        box = BOX + textwrap.indent(
            textwrap.dedent(
                "    def __getattr__(self, name):\n        return First()\n"
            ),
            "    ",
        )
        code = (
            CLASSES
            + box
            + textwrap.dedent("Box.slot = Other()\nprint(Box().slot.field)\n")
        )
        field, expected = 2, "2\n"
    elif lookup == "metaclass":
        meta = textwrap.dedent(
            "class Meta(type):\n    def __getattribute__(cls, name):\n        if name == 'slot':\n            return First()\n        return super().__getattribute__(name)\n"
        )
        code = (
            CLASSES
            + meta
            + textwrap.dedent(
                "class Box(metaclass=Meta):\n    pass\nBox.slot = Other()\nprint(Box.slot.field)\n"
            )
        )
        field, expected = 1, "1\n"
    elif lookup == "decorator":
        code = (
            CLASSES
            + textwrap.dedent("def decorate(cls):\n    return cls\n@decorate\n")
            + BOX
            + textwrap.dedent("Box.slot = Other()\nprint(Box().slot.field)\n")
        )
        field, expected = 2, "2\n"
    else:
        modified = CLASSES.replace(
            "class Other:\n",
            textwrap.dedent(
                "class Other:\n    def __new__(cls):\n        return First()\n"
            ),
        )
        code = (
            modified
            + BOX
            + textwrap.dedent("Box.slot = Other()\nprint(Box().slot.field)\n")
        )
        field, expected = 1, "1\n"
    exercise(tmp_path, code, field, expected, reject=True, warm=True)


@pytest.mark.parametrize("timing", ["before", "after"])
@pytest.mark.parametrize("field", [1, 2])
def test_global_class_rebinding_blocks_affected_fields(tmp_path, timing, field):
    prefix = CLASSES + textwrap.dedent(
        "class Box:\n    pass\nclass Replacement:\n    slot = Other()\n"
    )
    rebind = textwrap.dedent(
        "def rebind():\n    global Box\n    Box = Replacement\nrebind()\n"
    )
    if timing == "before":
        code = (
            prefix
            + rebind
            + textwrap.dedent(
                "Box.slot = First()\nprint(Box.slot.field, Replacement.slot.field)\n"
            )
        )
        expected = "1 1\n"
    else:
        code = (
            prefix
            + textwrap.dedent("Box.slot = First()\nsaved = Box.slot\n")
            + rebind
            + "print(saved.field, Box.slot.field)\n"
        )
        expected = "1 2\n"
    exercise(
        tmp_path,
        code,
        field,
        expected,
        reject=True,
        warm=True,
        uncertain_classes=("Box", "Replacement"),
    )


@pytest.mark.parametrize("field", [1, 2])
def test_class_body_lookup_alias_does_not_use_plain_data_inference(tmp_path, field):
    lookup = textwrap.dedent(
        "def lookup(self, name):\n    if name == 'slot':\n        return First()\n    return object.__getattribute__(self, name)\n"
    )
    code = (
        CLASSES
        + lookup
        + textwrap.dedent(
            "class Box:\n    __getattribute__ = lookup\nBox.slot = Other()\nprint(Box.slot.field, Box().slot.field)\n"
        )
    )
    exercise(tmp_path, code, field, "2 1\n", reject=True, warm=True)


@pytest.mark.parametrize("field", [1, 2])
def test_module_instance_write_keeps_class_data_uncertain(tmp_path, field):
    code = CLASSES + textwrap.dedent(
        "class Box:\n    pass\nBox.slot = Other()\nbox = Box()\nbox.slot = First()\nprint(Box.slot.field, box.slot.field)\n"
    )
    exercise(tmp_path, code, field, "2 1\n", reject=True, warm=True)


@pytest.mark.parametrize("field", [1, 2])
def test_lookup_factory_parameter_reassignment_does_not_lose_guard_type(
    tmp_path, field
):
    factory = textwrap.dedent(
        "def choose(item):\n    item = First()\n    return item\n"
    )
    box = textwrap.dedent(
        "class Box:\n    def __getattribute__(self, name):\n        if name == 'slot':\n            return choose(Other())\n        return object.__getattribute__(self, name)\n"
    )
    code = (
        CLASSES
        + factory
        + box
        + textwrap.dedent(
            "Box.slot = Other()\nprint(Box.slot.field, Box().slot.field)\n"
        )
    )
    exercise(tmp_path, code, field, "2 1\n", reject=True, warm=True)


def test_lookup_keyword_only_expansion_does_not_lose_affected_data_type(tmp_path):
    third = textwrap.dedent(
        "class Third:\n    def __init__(self):\n        self.field = 3\n"
    )
    choose = textwrap.dedent(
        "def choose(*, item):\n    if False:\n        item = First()\n    return item\n"
    )
    box = textwrap.dedent(
        "class Box:\n    def __getattribute__(self, name):\n        if name == 'slot':\n            return choose(**{'item': Other()})\n        return object.__getattribute__(self, name)\n"
    )
    code = (
        CLASSES
        + third
        + choose
        + box
        + textwrap.dedent(
            "Box.slot = Third()\nprint(Box.slot.field, Box().slot.field)\n"
        )
    )
    exercise(tmp_path, code, 2, "3 2\n", reject=True, warm=True)


def exercise_imported_slot(
    tmp_path, selection, *, early=None, module_import=False, reexport=False
):
    values = textwrap.dedent("class Foreign:\n    field = 'FOREIGN'\nold = Foreign()\n")
    binding = (
        "    import values as slot\n"
        if module_import
        else "    from values import old as slot\n"
    )
    subject = (
        textwrap.dedent("class Other:\n    field = 'OTHER'\nclass Owner:\n") + binding
    )
    if early == "class-body":
        subject += "    saved = slot\n"
    elif early == "module":
        subject += "saved = Owner.slot\n"
    subject += "Owner.slot = Other()\n"
    if early == "class-body":
        subject += "print(Owner.saved.field)\n"
    elif early == "module":
        subject += (
            "print(saved.old.field)\n" if module_import else "print(saved.field)\n"
        )
    else:
        subject += "print(Owner.slot.field)\n"
    expected = "FOREIGN\n" if early else "OTHER\n"
    project = Project(
        str(tmp_path),
        ropefolder=None,
        save_history=False,
        save_objectdb=False,
        perform_doa=False,
    )
    try:
        resources = {
            name: project.root.create_file(name) for name in ["values.py", "subject.py"]
        }
        if reexport:
            resources["foreign.py"] = project.root.create_file("foreign.py")
            resources["foreign.py"].write(values.removesuffix("old = Foreign()\n"))
            resources["values.py"].write(
                textwrap.dedent("from foreign import Foreign\nold = Foreign()\n")
            )
        else:
            resources["values.py"].write(values)
        resources["subject.py"].write(subject)
        before_sources = {
            name: resource.read_bytes() for name, resource in resources.items()
        }

        def runtime():
            result = subprocess.run(
                [sys.executable, "-B", "-c", "import subject"],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=20,
            )
            return result.returncode, result.stdout, result.stderr

        before = runtime()
        assert before[0] == 0 and before[1] == expected, before
        resource = resources["subject.py"]
        if selection == "other":
            offset = subject.index("field = 'OTHER'")
            changed_name = "changed_field"
        elif selection == "foreign":
            resource = resources["foreign.py"] if reexport else resources["values.py"]
            offset = values.index("field = 'FOREIGN'")
            changed_name = "changed_field"
        elif selection == "slot":
            offset = subject.index("Owner.slot =") + len("Owner.")
            changed_name = "changed_slot"
        elif selection == "dependency":
            resource = resources["values.py"]
            offset = values.index("old =")
            changed_name = "changed_original"
        else:
            resource = resources["values.py"]
            offset = None
            changed_name = "changed_values"
        try:
            changes = Rename(project, resource, offset).get_changes(changed_name)
        except exceptions.RefactoringError:
            assert early, "Unambiguous imported-slot overwrite must be refactorable"
            assert {
                name: value.read_bytes() for name, value in resources.items()
            } == before_sources
        else:
            project.do(changes)
            changed_subject = resources["subject.py"].read()
            if selection in ["other", "foreign"]:
                assert f"changed_field = '{selection.upper()}'" in resource.read()
            elif selection == "slot":
                assert "Owner.changed_slot = Other()" in changed_subject
                assert "as changed_slot" in changed_subject
            elif selection == "dependency":
                assert "changed_original = Foreign()" in resource.read()
                assert "import changed_original as slot" in changed_subject
            else:
                assert not resources["values.py"].exists()
                assert project.get_file("changed_values.py").exists()
                assert "import changed_values as slot" in changed_subject
        after = runtime()
        assert after[0] == 0 and after[1] == expected, after
        if not early:
            source = resources["subject.py"].read()
            module = project.get_pymodule(resources["subject.py"])
            other = module.get_scope().lookup("Other").get_object()
            field_name = "changed_field" if selection == "other" else "field"
            slot_name = "changed_slot" if selection == "slot" else "slot"
            finder = evaluate.ScopeNameFinder(module)
            field = finder.get_pyname_at(
                source.index(f"Owner.{slot_name}.{field_name}")
                + len(f"Owner.{slot_name}.")
            )
            assert field is other.get_attribute(field_name)
            write = finder.get_pyname_at(
                source.index(f"Owner.{slot_name} =") + len("Owner.")
            )
            read = finder.get_pyname_at(
                source.index(f"Owner.{slot_name}.{field_name}") + len("Owner.")
            )
            assert (
                write
                is read
                is module.get_scope()
                .lookup("Owner")
                .get_object()
                .get_attribute(slot_name)
            )
            assert write.get_object().get_type() is other
    finally:
        project.close()


@pytest.mark.parametrize("selection", ["other", "foreign", "slot", "dependency"])
def test_safe_imported_slot_overwrite_preserves_source_and_new_binding(
    tmp_path, selection
):
    exercise_imported_slot(tmp_path, selection)


@pytest.mark.parametrize("selection", ["other", "module"])
def test_safe_imported_module_slot_uses_new_value_and_keeps_module_source(
    tmp_path, selection
):
    exercise_imported_slot(tmp_path, selection, module_import=True)


@pytest.mark.parametrize("early", ["module", "class-body"])
def test_early_imported_foreign_field_is_preserved_or_atomically_refused(
    tmp_path, early
):
    exercise_imported_slot(tmp_path, "foreign", early=early)


def test_early_imported_module_keeps_instance_field_or_atomically_refused(tmp_path):
    exercise_imported_slot(tmp_path, "foreign", early="module", module_import=True)


def test_early_reexported_module_keeps_instance_field_or_atomically_refused(tmp_path):
    exercise_imported_slot(
        tmp_path, "foreign", early="module", module_import=True, reexport=True
    )


def test_early_imported_package_keeps_foreign_field_or_atomically_refuses(tmp_path):
    sources = {
        "foreign.py": textwrap.dedent("class Foreign:\n    field = 'FOREIGN'\n"),
        "valuespkg/__init__.py": textwrap.dedent(
            "from foreign import Foreign\nold = Foreign()\n"
        ),
        "subject.py": textwrap.dedent(
            "class Other:\n    field = 'OTHER'\nclass Owner:\n    import valuespkg as slot\nsaved = Owner.slot\nOwner.slot = Other()\nprint(saved.old.field)\n"
        ),
    }
    project = Project(
        str(tmp_path),
        ropefolder=None,
        save_history=False,
        save_objectdb=False,
        perform_doa=False,
    )
    try:
        package = project.root.create_folder("valuespkg")
        resources = {
            "foreign.py": project.root.create_file("foreign.py"),
            "valuespkg/__init__.py": package.create_file("__init__.py"),
            "subject.py": project.root.create_file("subject.py"),
        }
        for name, resource in resources.items():
            resource.write(sources[name])
        original = {name: resource.read_bytes() for name, resource in resources.items()}
        before = driver("import subject", tmp_path)
        assert before["exit"] == 0 and before["stdout"] == "FOREIGN\n", before
        try:
            changes = Rename(
                project, resources["foreign.py"], sources["foreign.py"].index("field =")
            ).get_changes("changed_field")
        except exceptions.RefactoringError:
            assert {
                name: resource.read_bytes() for name, resource in resources.items()
            } == original
        else:
            project.do(changes)
            assert "changed_field = 'FOREIGN'" in resources["foreign.py"].read()
        after = driver("import subject", tmp_path)
        assert after["exit"] == 0 and after["stdout"] == "FOREIGN\n", after
    finally:
        project.close()


# Module export and Unicode import regressions, using existing test helpers.


def _module_data_project(directory, sources):
    project = Project(
        str(directory),
        ropefolder=None,
        save_history=False,
        save_objectdb=False,
        perform_doa=False,
    )
    resources = {}
    for path, code in sources.items():
        parent = project.root
        parts = path.split("/")
        for part in parts[:-1]:
            parent = (
                parent.get_child(part)
                if parent.has_child(part)
                else parent.create_folder(part)
            )
        resources[path] = parent.create_file(parts[-1])
        resources[path].write(code)
    project.root.create_file("sentinel.py").write("untouched = 'sentinel'\n")
    return project, resources


def _python_source_bytes(directory):
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*.py")
    }


def _preserve_saved_foreign_field(
    tmp_path, sources, reference, target="foreign-field", expect_success=False
):
    sources = dict(sources)
    if target == "unrelated-global":
        sources["subject.py"] = "unconnected = 'OK'\n" + sources["subject.py"].replace(
            f"print({reference})", f"print({reference}, unconnected)"
        )
    expected = "FOREIGN OK\n" if target == "unrelated-global" else "FOREIGN\n"
    project, resources = _module_data_project(tmp_path, sources)
    try:
        before = driver("import subject", tmp_path)
        assert before["exit"] == 0 and before["stdout"] == expected, before
        original = _python_source_bytes(tmp_path)
        if target == "unrelated-global":
            selected_path, marker, new_name = (
                "subject.py",
                "unconnected = 'OK'",
                "changed_unconnected",
            )
        else:
            selected_path = (
                "foreign.py" if "foreign.py" in sources else "valuespkg/foreign.py"
            )
            marker, new_name = "field = 'FOREIGN'", "renamed_field"
        resource = resources[selected_path]
        offset = sources[selected_path].index(marker)
        try:
            changes = Rename(project, resource, offset).get_changes(new_name)
        except exceptions.RefactoringError:
            assert target == "foreign-field", "Unrelated global Rename must succeed"
            assert not expect_success, "Ordinary referenced field Rename must succeed"
            assert _python_source_bytes(tmp_path) == original
        else:
            # get_changes itself must leave every resource unchanged.
            assert _python_source_bytes(tmp_path) == original
            project.do(changes)
            if target == "unrelated-global":
                assert "changed_unconnected = 'OK'" in resource.read()
                assert f"print({reference}, changed_unconnected)" in resource.read()
                current = _python_source_bytes(tmp_path)
                assert {
                    key: value for key, value in current.items() if key != "subject.py"
                } == {
                    key: value for key, value in original.items() if key != "subject.py"
                }
            else:
                assert "renamed_field = 'FOREIGN'" in resource.read()
                assert (
                    reference.replace(".field", ".renamed_field")
                    in resources["subject.py"].read()
                )
            assert "field = 'OTHER'" in resources["subject.py"].read()
        assert project.get_file("sentinel.py").read_bytes() == original["sentinel.py"]
        after = driver("import subject", tmp_path)
        assert after["exit"] == 0 and after["stdout"] == expected, after
    finally:
        project.close()


_MODULE_DATA_SUBJECT = textwrap.dedent("""\
    class Other:
        field = 'OTHER'
    class Owner:
        import values as slot
    saved = Owner.slot
    Owner.slot = Other()
    print(saved.old.field)
    """)


@pytest.mark.parametrize(
    "case", ["factory-result", "module-alias", "legal-cycle", "nested-class"]
)
@pytest.mark.parametrize("target", ["foreign-field", "unrelated-global"])
def test_saved_imported_module_data_keeps_field_safety_and_unrelated_rename(
    tmp_path, case, target
):
    subject = _MODULE_DATA_SUBJECT
    reference = "saved.old.field"
    if case == "factory-result":
        sources = {
            "foreign.py": textwrap.dedent("""\
                class Foreign:
                    field = 'FOREIGN'
                def make():
                    return Foreign()
                """),
            "values.py": textwrap.dedent("""\
                from foreign import make
                old = make()
                """),
            "subject.py": subject,
        }
    elif case == "module-alias":
        reference = "saved.alias.old.field"
        sources = {
            "foreign.py": textwrap.dedent("""\
                class Foreign:
                    field = 'FOREIGN'
                old = Foreign()
                """),
            "values.py": "import foreign as alias\n",
            "subject.py": subject.replace("saved.old.field", reference),
        }
    elif case == "legal-cycle":
        sources = {
            "foreign.py": textwrap.dedent("""\
                import values as values_namespace
                class Foreign:
                    field = 'FOREIGN'
                old = Foreign()
                """),
            "values.py": textwrap.dedent("""\
                import foreign as foreign_namespace
                old = foreign_namespace.old
                """),
            "subject.py": subject,
        }
    else:
        reference = "saved.Inner.field"
        sources = {
            "foreign.py": textwrap.dedent("""\
                class Outer:
                    class Inner:
                        field = 'FOREIGN'
                old = Outer()
                """),
            "subject.py": textwrap.dedent("""\
                class Other:
                    field = 'OTHER'
                class Owner:
                    from foreign import old as slot
                saved = Owner.slot
                Owner.slot = Other()
                print(saved.Inner.field)
                """),
        }
    _preserve_saved_foreign_field(tmp_path, sources, reference, target)


_IMPORT_SPAN_VALUES = textwrap.dedent("""\
    class Foreign:
        field = 'FOREIGN'
    old = Foreign()
    """)
_IMPORT_SPAN_SUBJECT = textwrap.dedent("""\
    from pkg.values import old as foreign
    class Other:
        field = 'OTHER'
    class 容器:
        标签 = '中'; import pkg.values as pkg
    容器.pkg = Other()
    print(foreign.field, 容器.pkg.field)
    """)


@pytest.mark.parametrize(
    "kind, identifier, new_name",
    [
        ("package", "pkg", "renamed_pkg"),
        ("module", "values", "renamed_values"),
        ("alias", "pkg", "renamed_slot"),
    ],
)
def test_dotted_import_source_and_local_alias_rename_with_unicode_prefix(
    tmp_path, kind, identifier, new_name
):
    sources = {
        "pkg/__init__.py": "",
        "pkg/values.py": _IMPORT_SPAN_VALUES,
        "subject.py": _IMPORT_SPAN_SUBJECT,
    }
    project, resources = _module_data_project(tmp_path, sources)
    try:
        before = driver("import subject", tmp_path)
        assert before["exit"] == 0 and before["stdout"] == "FOREIGN OTHER\n", before
        original = _python_source_bytes(tmp_path)
        source = sources["subject.py"]
        line = next(
            value
            for value in source.splitlines()
            if "import pkg.values as pkg" in value
        )
        character_column = line.index("import pkg.values")
        byte_column = len(line[:character_column].encode("utf-8"))
        assert character_column == 14 and byte_column == 20
        marker = "容器.pkg = Other()" if kind == "alias" else "import pkg.values as pkg"
        # Public offsets are Unicode character offsets, including the source word.
        offset = source.index(marker) + marker.index(identifier)
        changes = Rename(project, resources["subject.py"], offset).get_changes(new_name)
        assert _python_source_bytes(tmp_path) == original
        project.do(changes)
        subject = resources["subject.py"].read()
        if kind == "alias":
            values_path, init_path = "pkg/values.py", "pkg/__init__.py"
            expected_subject = source.replace("as pkg", "as renamed_slot").replace(
                "容器.pkg", "容器.renamed_slot"
            )
            slot_name = "renamed_slot"
            # The source package/module spelling remains intact.
            assert "import pkg.values as renamed_slot" in subject
            assert "from pkg.values import old as foreign" in subject
        else:
            slot_name = "pkg"
            target_module = (
                "renamed_pkg.values" if kind == "package" else "pkg.renamed_values"
            )
            values_path = (
                "renamed_pkg/values.py"
                if kind == "package"
                else "pkg/renamed_values.py"
            )
            init_path = (
                "renamed_pkg/__init__.py" if kind == "package" else "pkg/__init__.py"
            )
            expected_subject = source.replace("pkg.values", target_module)
            assert not project.get_file("pkg/values.py").exists()
            if kind == "package":
                assert not project.root.has_child("pkg")
            assert f"import {target_module} as pkg" in subject
            assert f"from {target_module} import old as foreign" in subject
        assert subject == expected_subject
        assert project.get_file(values_path).read() == sources["pkg/values.py"]
        assert project.get_file(init_path).read() == ""
        assert project.get_file("sentinel.py").read_bytes() == original["sentinel.py"]
        after = driver("import subject", tmp_path)
        assert after["exit"] == 0 and after["stdout"] == "FOREIGN OTHER\n", after
        module = project.get_pymodule(resources["subject.py"])
        finder = evaluate.ScopeNameFinder(module)
        for marker, expected_path, expected_line, class_name in (
            ("foreign.field", values_path, 2, "Foreign"),
            (f"容器.{slot_name}.field", "subject.py", 3, "Other"),
        ):
            field_offset = subject.index(marker) + marker.rindex(".field") + 1
            pyname = finder.get_pyname_at(field_offset)
            assert pyname is not None
            assert pyname.get_object() is not pyobjects.get_unknown()
            owner_module = project.get_pymodule(project.get_file(expected_path))
            expected_pyname = (
                owner_module.get_attribute(class_name)
                .get_object()
                .get_attribute("field")
            )
            assert pyname is expected_pyname
            defining, lineno = pyname.get_definition_location()
            assert (
                defining is not None and defining.get_resource().path == expected_path
            )
            assert lineno == expected_line
    finally:
        project.close()


def test_saved_namespace_module_foreign_field_is_preserved_or_atomically_refused(
    tmp_path,
):
    # Select a field from the real module inside a namespace package.
    sources = {
        "valuespkg/foreign.py": textwrap.dedent("""\
            class Foreign:
                field = 'FOREIGN'
            old = Foreign()
            """),
        "subject.py": textwrap.dedent("""\
            import valuespkg.foreign
            class Other:
                field = 'OTHER'
            class Owner:
                import valuespkg as slot
            saved = Owner.slot
            Owner.slot = Other()
            print(saved.foreign.old.field)
            """),
    }
    assert "valuespkg/__init__.py" not in sources
    _preserve_saved_foreign_field(tmp_path, sources, "saved.foreign.old.field")


def test_ordinary_referenced_foreign_field_rename_succeeds_without_external_write(
    tmp_path,
):
    sources = {
        "foreign.py": textwrap.dedent("""\
            class Foreign:
                field = 'FOREIGN'
            """),
        "subject.py": textwrap.dedent("""\
            from foreign import Foreign
            class Other:
                field = 'OTHER'
            saved = Foreign()
            print(saved.field)
            """),
    }
    _preserve_saved_foreign_field(tmp_path, sources, "saved.field", expect_success=True)


_NAMESPACE_COMMON = textwrap.dedent("""class First:
    field = 'FIRST'
class Other:
    field = 'OTHER'
""")

_NAMESPACE_PATTERN = _NAMESPACE_COMMON + textwrap.dedent("""def lookup(self, name):
    if name == 'slot':
        return First()
    return object.__getattribute__(self, name)
class Box:
    match lookup:
        case __getattribute__:
            pass
Box.slot = Other()
print(Box.slot.field, Box().slot.field)
""")

_NAMESPACE_TUPLE = _NAMESPACE_COMMON + textwrap.dedent("""class Box:
    slot = Other()
Box.slot, spare = First(), 0
print(Box.slot.field)
""")

_NAMESPACE_CLASS_ALIAS = _NAMESPACE_COMMON + textwrap.dedent("""class Box:
    pass
Box.slot = Other()
alias = Box
def replace():
    alias.slot = First()
replace()
print(Box.slot.field)
""")

_NAMESPACE_WILDCARD = _NAMESPACE_COMMON + textwrap.dedent("""class Box:
    pass
Box.slot = First()
saved = Box
from values import *
print(saved.slot.field, Box.slot.field)
""")

_NAMESPACE_WILDCARD_VALUES = textwrap.dedent("""class Foreign:
    field = 'FOREIGN'
class Box:
    slot = Foreign()
__all__ = ['Box']
""")


@pytest.mark.parametrize(
    "code, values, expected",
    [
        pytest.param(
            _NAMESPACE_PATTERN, None, "OTHER FIRST\n", id="pattern-class-hook"
        ),
        pytest.param(_NAMESPACE_TUPLE, None, "FIRST\n", id="tuple-class-slot"),
        pytest.param(
            _NAMESPACE_CLASS_ALIAS, None, "FIRST\n", id="deferred-class-alias"
        ),
        pytest.param(
            _NAMESPACE_WILDCARD,
            _NAMESPACE_WILDCARD_VALUES,
            "FIRST FOREIGN\n",
            id="wildcard-class-rebinding",
        ),
    ],
)
def test_unsafe_namespace_writes_atomically_refuse_field_rename(
    tmp_path, code, values, expected
):
    project = Project(
        str(tmp_path),
        ropefolder=None,
        save_history=False,
        save_objectdb=False,
        perform_doa=False,
    )
    try:
        sources = {"subject.py": code, "sentinel.py": "untouched = 'sentinel'\n"}
        if values is not None:
            sources["values.py"] = values
        resources = {}
        for path, source in sources.items():
            resource = project.root.create_file(path)
            resource.write(source)
            resources[path] = resource

        before = driver("import subject", tmp_path)
        assert before["exit"] == 0 and before["stdout"] == expected, before
        snapshot = {path: resource.read_bytes() for path, resource in resources.items()}

        # No Rope query primes inference: Rename is the first semantic consumer.
        offset = code.index("field = 'FIRST'") + 1
        with pytest.raises(exceptions.RefactoringError):
            Rename(project, resources["subject.py"], offset).get_changes(
                "changed_field"
            )

        assert {
            path: resource.read_bytes() for path, resource in resources.items()
        } == snapshot
        after = driver("import subject", tmp_path)
        assert after["exit"] == 0 and after["stdout"] == expected, after
    finally:
        project.close()


@pytest.mark.parametrize(
    "binding", ["pattern-capture", "except-alias", "loop-unpack", "annotated-local"]
)
@pytest.mark.parametrize("field", [1, 2])
def test_lookup_factory_local_rebinding_keeps_actual_return_type_guarded(
    tmp_path, binding, field
):
    classes = CLASSES
    if binding == "pattern-capture":
        factory = textwrap.dedent("""\
            def choose(item):
                match Other():
                    case item:
                        return item
            """)
    elif binding == "except-alias":
        classes = CLASSES.replace("class First:", "class First(Exception):")
        factory = textwrap.dedent("""\
            def choose(item):
                try:
                    raise First()
                except First as item:
                    return item
            """)
    elif binding == "loop-unpack":
        factory = textwrap.dedent("""\
            def choose(item):
                for item, spare in [(Other(), First())]:
                    return item
            """)
    else:
        factory = textwrap.dedent("""\
            def choose(item):
                item: object = Other()
                return item
            """)

    hook = textwrap.dedent("""\
        def __getattribute__(self, name):
            if name == 'slot':
                return choose(First())
            return object.__getattribute__(self, name)
        """)
    tail = textwrap.dedent("""\
        Box.slot = First()
        print(Box.slot.field, Box().slot.field)
        """)
    expected = "1 2\n"
    if binding == "except-alias":
        hook = hook.replace("choose(First())", "choose(Other())")
        tail = tail.replace("Box.slot = First()", "Box.slot = Other()")
        expected = "2 1\n"
    code = classes + factory + BOX + textwrap.indent(hook, "    ") + tail
    sentinel = tmp_path / "sentinel.py"
    sentinel.write_text("untouched = 'sentinel'\n", encoding="utf-8")
    original_sentinel = sentinel.read_bytes()
    exercise(tmp_path, code, field, expected, reject=True, warm=False)
    assert sentinel.read_bytes() == original_sentinel


_EXTRA_MAPPING_CLASS_IDENTITY = CLASSES + BOX + textwrap.dedent("""Box.slot = Other()
saved = Box
match {'replacement': First()}:
    case {**Box}:
        pass
print(saved.slot.field, Box['replacement'].field)
""")

_EXTRA_STAR_CLASS_IDENTITY = CLASSES + BOX + textwrap.dedent("""Box.slot = Other()
saved = Box
match [First()]:
    case [*Box]:
        pass
print(saved.slot.field, Box[0].field)
""")

_EXTRA_EXCEPT_CLASS_IDENTITY = CLASSES + BOX + textwrap.dedent("""Box.slot = Other()
saved = Box
try:
    raise ValueError('replacement')
except ValueError as Box:
    print(saved.slot.field, str(Box))
print(saved.slot.field)
""")

_EXTRA_EXCEPT_LOOKUP_HOOK = CLASSES + textwrap.dedent("""def lookup(self, name):
    if name == 'slot':
        return First()
    return object.__getattribute__(self, name)
class Box:
    __getattribute__ = lookup
    try:
        raise ValueError('replacement')
    except ValueError as __getattribute__:
        pass
Box.slot = Other()
print(Box.slot.field, Box().slot.field)
""")

_EXTRA_IMPORT_ATTRIBUTE = CLASSES + textwrap.dedent("""class Box:
    from values import old
Box.old = First()
print(Box.old.field)
""")

_EXTRA_IMPORT_VALUES = textwrap.dedent("""old = object()
""")


@pytest.mark.parametrize(
    "code, values, marker, marker_offset, replacement, expected",
    [
        pytest.param(
            _EXTRA_MAPPING_CLASS_IDENTITY,
            None,
            "field = 2",
            1,
            "changed_field",
            "2 1\n",
            id="mapping-rest-class-identity",
        ),
        pytest.param(
            _EXTRA_STAR_CLASS_IDENTITY,
            None,
            "field = 2",
            1,
            "changed_field",
            "2 1\n",
            id="star-class-identity",
        ),
        pytest.param(
            _EXTRA_EXCEPT_CLASS_IDENTITY,
            None,
            "field = 2",
            1,
            "changed_field",
            "2 replacement\n2\n",
            id="except-class-identity",
        ),
        pytest.param(
            _EXTRA_EXCEPT_LOOKUP_HOOK,
            None,
            "field = 2",
            1,
            "changed_field",
            "2 2\n",
            id="except-clears-class-lookup-hook",
        ),
        pytest.param(
            _EXTRA_IMPORT_ATTRIBUTE,
            _EXTRA_IMPORT_VALUES,
            "Box.old = First()",
            len("Box.") + 1,
            "changed_slot",
            "1\n",
            id="unaliased-import-backed-class-attribute",
        ),
    ],
)
def test_namespace_captures_and_import_backed_attribute_refuse_unsafe_rename(
    tmp_path, code, values, marker, marker_offset, replacement, expected
):
    project = Project(
        str(tmp_path),
        ropefolder=None,
        save_history=False,
        save_objectdb=False,
        perform_doa=False,
    )
    try:
        sources = {"subject.py": code, "sentinel.py": "untouched = 'sentinel'\n"}
        if values is not None:
            sources["values.py"] = values
        resources = {}
        for path, source in sources.items():
            resource = project.root.create_file(path)
            resource.write(source)
            resources[path] = resource

        before = driver("import subject", tmp_path)
        assert before["exit"] == 0 and before["stdout"] == expected, before
        snapshot = {path: resource.read_bytes() for path, resource in resources.items()}
        assert code.count(marker) == 1

        with pytest.raises(exceptions.RefactoringError):
            Rename(
                project, resources["subject.py"], code.index(marker) + marker_offset
            ).get_changes(replacement)

        assert {
            path: resource.read_bytes() for path, resource in resources.items()
        } == snapshot
        after = driver("import subject", tmp_path)
        assert after["exit"] == 0 and after["stdout"] == expected, after
    finally:
        project.close()
