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
