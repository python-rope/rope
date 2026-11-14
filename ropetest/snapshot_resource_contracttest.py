"""Real source snapshots keep local and external resource reads closed."""

import ast
import os
import shutil
import sys
import typing
from textwrap import dedent, indent

import pytest

from rope.base import change, evaluate, pyobjects
from rope.base.fscommands import FileSystemCommands
from rope.base.project import NoProject, Project, get_no_project
from rope.refactor import patchedast, rename, similarfinder


@pytest.fixture
def alias_project(tmp_path):
    project = Project(str(tmp_path))
    try:
        yield project
    finally:
        project.close()


def test_installed_native_capture_region(alias_project):
    source = 'prefix = "é"\nvalue = (first,\n         second)\n'
    resource = alias_project.root.create_file("captures.py")
    resource.write(source)
    module = alias_project.get_pymodule(resource)
    match = next(similarfinder.SimilarFinder(module).get_matches("value = ${value}"))
    start, end = match.get_capture_region("value")
    assert source[start:end] == "(first,\n         second)"
    with pytest.raises(ValueError, match="missing"):
        match.get_capture_region("missing")


def test_installed_mro_retains_unresolved_imported_base(alias_project):
    provider = alias_project.root.create_file("provider.py")
    provider.write("declared = 1\n")
    resource = alias_project.root.create_file("consumer.py")
    resource.write(dedent("""\
        from provider import missing
        class Base(object):
            member = 1
        class Derived(Base, missing):
            pass
    """))
    module = alias_project.get_pymodule(resource)
    base = module["Base"].get_object()
    derived = module["Derived"].get_object()
    resolved, unresolved = derived.get_bases()
    assert resolved is base
    assert isinstance(unresolved, pyobjects.UnresolvedBase)
    assert unresolved.pyobject is module["missing"].get_object()
    assert derived.get_superclasses() == [base]
    assert derived.get_mro() == [derived, *base.get_mro(), unresolved]
    assert derived["member"] is base["member"]


def test_installed_class_header_retains_previous_import_binding(alias_project):
    provider = alias_project.root.create_file("provider.py")
    provider.write(dedent("""\
        class Foo:
            member = 1
    """))
    resource = alias_project.root.create_file("consumer.py")
    resource.write(dedent("""\
        from provider import Foo
        class Foo(Foo):
            pass
    """))
    imported = alias_project.get_pymodule(provider)["Foo"].get_object()
    derived = alias_project.get_pymodule(resource)["Foo"].get_object()
    assert derived.get_mro() == [derived, imported]
    assert derived["member"] is imported["member"]


def test_installed_class_subscription_retains_hook_result(alias_project):
    resource = alias_project.root.create_file("subscription.py")
    source = dedent("""\
        class Other:
            pass
        class Base:
            def __class_getitem__(cls, item):
                return Other
        class Derived(Base[int]):
            pass
    """)
    resource.write(source)
    namespace = {}
    exec(source, namespace)
    assert namespace["Derived"].__bases__ == (namespace["Other"],)
    module = alias_project.get_pymodule(resource)
    assert module["Derived"].get_object().get_bases() == [
        module["Other"].get_object()
    ]


@pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 requires Python 3.12")
def test_installed_pep695_bound_generic_preserves_ancestry(alias_project):
    resource = alias_project.root.create_file("generic.py")
    source = dedent("""\
        class Identity:
            pass
        class Ownership[Resource: Identity]:
            pass
        class Leaf(Ownership[Identity]):
            pass
    """)
    resource.write(source)
    namespace = {}
    exec(source, namespace)
    assert namespace["Ownership"] in namespace["Leaf"].__mro__
    assert namespace["Ownership"].__type_params__[0].__bound__ is namespace["Identity"]
    module = alias_project.get_pymodule(resource)
    assert module["Ownership"].get_object() in module["Leaf"].get_object().get_mro()


def test_installed_native_import_roots(alias_project):
    source = (
        "import outer.child as overwritten, second\n"
        "overwritten = None\n"
        "from .relative import ignored\n"
        "if False:\n    from guarded.child import *\n"
        "def nested():\n    import nested_package.child\n"
    )
    resource = alias_project.root.create_file("imports.py")
    resource.write(source)
    module = alias_project.get_pymodule(resource)
    assert module.get_source_binding_index().absolute_import_roots() == frozenset(
        {"outer", "second", "guarded", "nested_package"}
    )


def test_installed_native_assignment_string_sequence(alias_project):
    resource = alias_project.root.create_file("metadata.py")
    resource.write("shared = ('first',)\nclass Owner:\n    names = tuple(shared)\n")
    module = alias_project.get_pymodule(resource)
    index = module.get_source_binding_index()
    assert index.assignment_string_sequence("names") is None
    scope = module["Owner"].get_object().get_scope()
    assert index.assignment_string_sequence("names", scope) == ("first",)
    assert index.assignment_string_sequence("names", class_metadata=True) == ("first",)


@pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 requires Python 3.12")
@pytest.mark.parametrize("owner", ["module", "function", "class"])
@pytest.mark.parametrize("bindings", ["alias", "ordinary-first", "alias-first", "repeated"])
def test_type_alias_definition_location_preserves_first_binding(alias_project, owner, bindings):
    declaration = "type Bag[T] = (\n    SequenceOf[T]\n)\n"
    body = "ordinary = 0\n\n"
    if bindings == "ordinary-first":
        body += "Bag = 1\n"
    body += declaration
    if bindings == "alias-first":
        body += "Bag = 1\n"
    elif bindings == "repeated":
        body += "type Bag[U] = SequenceOf[U]\n"
    body += "reference = Bag\n"
    header = {"module": "", "function": "def factory():\n", "class": "class Owner:\n"}[owner]
    source = "from collections.abc import Sequence as SequenceOf\n" + header
    source += indent(body, "    ") if header else body
    resource = alias_project.root.create_file("declarations.py")
    resource.write(source)
    module = alias_project.get_pymodule(resource)
    scope = module.get_scope()
    if owner != "module":
        scope = module["factory" if owner == "function" else "Owner"].get_object().get_scope()
    alias = scope["Bag"]
    first_line = source[:source.index("Bag")].count("\n") + 1
    ordinary_line = source[:source.index("ordinary =")].count("\n") + 1
    assert alias.get_definition_location() == (module, first_line)
    assert scope["ordinary"].get_definition_location() == (module, ordinary_line)
    if bindings in {"ordinary-first", "alias-first"}:
        assert alias.get_object().get_type() is scope["ordinary"].get_object().get_type()
    else:
        assert alias.get_object() is pyobjects.get_unknown()
    assert alias.get_definition_location() == (module, first_line)


@pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 requires Python 3.12")
@pytest.mark.parametrize("owner", ["module", "function", "class"])
def test_type_alias_location_does_not_evaluate_or_substitute_lazy_value(alias_project, owner):
    source = "events = []\ndef resolve():\n    events.append('value')\n    raise RuntimeError('lazy value')\n"
    declaration = "type Bag[T] = resolve()\n"
    if owner == "module":
        source += declaration + "selected = Bag\n"
    elif owner == "class":
        source += "class Owner:\n" + indent(declaration, "    ") + "selected = Owner.Bag\n"
    else:
        source += "def factory():\n" + indent(declaration + "return Bag\n", "    ") + "selected = factory()\n"
    resource = alias_project.root.create_file("lazy.py")
    resource.write(source)
    module = alias_project.get_pymodule(resource)
    scope = module.get_scope()
    if owner != "module":
        scope = module["factory" if owner == "function" else "Owner"].get_object().get_scope()
    alias = scope["Bag"]
    assert alias.get_definition_location() == (module, source[:source.index("type Bag")].count("\n") + 1)
    assert alias.get_object() is pyobjects.get_unknown()
    namespace = {}
    exec(compile(source, resource.real_path, "exec"), namespace)
    assert isinstance(namespace["selected"], typing.TypeAliasType)
    assert namespace["events"] == []
    with pytest.raises(RuntimeError, match="lazy value"):
        namespace["selected"].__value__
    assert namespace["events"] == ["value"]


@pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 requires Python 3.12")
@pytest.mark.parametrize("method", ["__init__", "method"])
def test_method_type_alias_is_local_not_an_instance_attribute(alias_project, method):
    source = f"class Owner:\n    ordinary = 0\n    def {method}(self):\n        type Bag[T] = list[T]\n        value = 1\n        self.actual = value\n"
    resource = alias_project.root.create_file("methods.py")
    resource.write(source)
    module = alias_project.get_pymodule(resource)
    owner = module["Owner"].get_object()
    assert "Bag" not in owner.get_attributes()
    assert "value" not in owner.get_attributes()
    assert owner["ordinary"].get_definition_location() == (module, 2)
    assert owner["actual"].get_definition_location() == (module, 6)
    scope = owner[method].get_object().get_scope()
    assert scope["Bag"].get_definition_location() == (module, 4)
    assert scope["value"].get_definition_location() == (module, 5)
    assert scope["Bag"].get_object() is pyobjects.get_unknown()


@pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 requires Python 3.12")
@pytest.mark.parametrize("imports,reference", [
    ("from supplier import Bag", "Bag"),
    ("from supplier import Bag as Alias", "Alias"),
    ("import supplier", "supplier.Bag"),
])
def test_imported_type_alias_location_and_native_rename(alias_project, imports, reference):
    supplier = alias_project.root.create_file("supplier.py")
    source = "from collections.abc import Sequence\n\ntype Bag[T] = Sequence[T]\n"
    supplier.write(source)
    client = alias_project.root.create_file("client.py")
    client_source = imports + "\nreference = " + reference + "[int]\n"
    client.write(client_source)
    producer = alias_project.get_pymodule(supplier)
    consumer = alias_project.get_pymodule(client)
    offset = client_source.rindex(reference.rsplit(".", 1)[-1]) + 1
    binding = evaluate.eval_location(consumer, offset)
    assert binding.get_definition_location() == (producer, 3)
    alias_project.do(rename.Rename(alias_project, supplier, source.index("Bag")).get_changes("Crate"))
    assert supplier.read() == source.replace("Bag", "Crate")
    assert client.read() == client_source.replace("Bag", "Crate")


@pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 requires Python 3.12")
@pytest.mark.parametrize("forward", [False, True])
@pytest.mark.parametrize("shadowed", [False, True])
def test_class_type_alias_value_resolves_its_sibling(alias_project, forward, shadowed):
    declaration = "type Bag[T] = list[T]\n"
    reference = "type Items = Bag[int]\n"
    body = reference + declaration if forward else declaration + reference
    source = "type Bag[T] = tuple[T, ...]\n" if shadowed else ""
    source += "class Owner:\n" + indent(body, "    ")
    resource = alias_project.root.create_file("class_aliases.py")
    resource.write(source)
    module = alias_project.get_pymodule(resource)
    owner = module["Owner"].get_object()

    binding = evaluate.eval_location(module, source.index("Bag[int]") + 1)

    assert binding is owner["Bag"]
    namespace = {}
    exec(compile(source, resource.real_path, "exec"), namespace)
    runtime_owner = namespace["Owner"]
    assert typing.get_origin(runtime_owner.Items.__value__) is runtime_owner.Bag


@pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 requires Python 3.12")
def test_conditional_class_type_alias_retains_ambiguous_binding(alias_project):
    source = (
        "condition = True\n"
        "class Owner:\n"
        "    if condition:\n"
        "        type Bag[T] = list[T]\n"
        "    type Items = Bag[int]\n"
    )
    resource = alias_project.root.create_file("conditional_alias.py")
    resource.write(source)
    module = alias_project.get_pymodule(resource)
    binding = evaluate.eval_location(module, source.index("Bag[int]") + 1)

    assert binding.is_refactoring_identity_safe is False
    assert binding.may_reference(module["Owner"].get_object()["Bag"])


def test_default_project_initialization_has_no_warnings(tmp_path, recwarn):
    project = Project(str(tmp_path))
    try:
        assert project.root.pathlib == tmp_path
    finally:
        project.close()
    assert not recwarn.list


def test_configured_source_folder_selection_has_no_warnings(tmp_path, recwarn):
    source = tmp_path / "src"
    source.mkdir()
    project = Project(str(tmp_path), source_folders=["src"])
    try:
        assert project.get_resource("src") in project.get_source_folders()
    finally:
        project.close()
    assert not recwarn.list


@pytest.mark.parametrize("handler", ["except", "except*"])
def test_try_else_finally_expression_regions_and_matching(tmp_path, handler):
    if handler == "except*" and sys.version_info < (3, 11):
        pytest.skip("exception groups require Python 3.11")
    source = dedent(f"""\
        def execute(self):
            try:
                self.run()
            {handler} Exception:
                self.failed()
            else:
                (
                    self._record_execution_metrics
                )
            finally:
                self.cleanup()
    """)
    tree = patchedast.get_patched_ast(source, True)
    expression = tree.body[0].body[0].orelse[0].value
    start = source.index("self._record_execution_metrics")
    expected = (start, start + len("self._record_execution_metrics"))
    assert expression.region == expected
    assert patchedast.write_ast(tree) == source
    project = Project(str(tmp_path))
    try:
        module = project.root.create_file("consumer.py")
        module.write(source)
        finder = similarfinder.SimilarFinder(project.get_pymodule(module))
        matches = list(finder.get_matches("(\nself._record_execution_metrics\n)"))
        assert [match.get_region() for match in matches] == [expected]
    finally:
        project.close()


@pytest.mark.parametrize("prefix", ["", "\u03c0"])
def test_fstring_fields_follow_expression_coordinates(prefix):
    source = dedent(
        'result = f"${{frozen}}({{{literal}}})" if frozen else literal\n'
    ).replace('f"', f'f"{prefix}', 1)
    module = patchedast.get_patched_ast(source, sorted_children=True)
    fields = [node for node in ast.walk(module) if isinstance(node, ast.FormattedValue)]
    start = source.index("{literal}")
    assert len(fields) == 1
    assert fields[0].region == (start, start + len("{literal}"))
    assert patchedast.write_ast(module) == source


class CapturedFileSystem(FileSystemCommands):
    """A read-only filesystem captured from real test inputs."""

    def __init__(self, roots):
        self.files = {}
        self.directories = {}
        self.states = {}
        for root in roots:
            for directory, _folders, files in os.walk(root):
                self.directories[directory] = tuple(os.listdir(directory))
                self.states[directory] = os.stat(directory)
                for name in files:
                    path = os.path.join(directory, name)
                    self.states[path] = os.stat(path)
                    with open(path, "rb") as stream:
                        self.files[path] = stream.read()

    @staticmethod
    def realpath(path):
        return os.path.abspath(os.path.expanduser(path))

    def exists(self, path):
        return path in self.files or path in self.directories

    def isfile(self, path):
        return path in self.files

    def isdir(self, path):
        return path in self.directories

    def listdir(self, path):
        return self.directories[path]

    def read(self, path):
        return self.files[path]

    def stat(self, path):
        return self.states[path]


@pytest.mark.parametrize("captured", [False, True])
@pytest.mark.parametrize(
    "destination, expected",
    [("", "source.py"), ("existing", "existing/source.py"), ("late", "late")],
)
def test_move_destination_uses_project_filesystem(
    tmp_path, captured, destination, expected
):
    root = tmp_path / "project"
    (root / "existing").mkdir(parents=True)
    (root / "source.py").write_text("value = 1\n", encoding="utf-8")
    commands = CapturedFileSystem((str(root),)) if captured else FileSystemCommands()
    if captured:
        shutil.rmtree(root)
        (root / "late").mkdir(parents=True)
    project = Project(
        str(root),
        fscommands=commands,
        ropefolder=None,
        save_objectdb=False,
        save_history=False,
    )
    try:
        source = project.get_resource("source.py")
        assert change.MoveResource(source, destination).new_resource.path == expected
        assert (
            change.MoveResource(source, destination, exact=True).new_resource.path
            == destination
        )
    finally:
        project.close()


def test_local_and_external_snapshot_resources_ignore_changed_disk(tmp_path):
    root = tmp_path / "consumer"
    local = root / "src"
    external = tmp_path / "dependencies"
    package = external / "provider"
    local.mkdir(parents=True)
    package.mkdir(parents=True)
    (local / "consumer.py").write_text(
        "from provider import Original\nborrowed = Original\n",
        encoding="utf-8",
    )
    (package / "__init__.py").write_text(
        "class Original:\n    marker = 1\n",
        encoding="utf-8",
    )
    captured = CapturedFileSystem((str(root), str(external)))
    singleton = get_no_project()
    shutil.rmtree(root)
    shutil.rmtree(external)
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "class Changed:\n    marker = 2\n",
        encoding="utf-8",
    )
    (external / "late.py").write_text("marker = 3\n", encoding="utf-8")
    outside = NoProject(fscommands=captured)
    project = Project(
        str(root),
        fscommands=captured,
        external_project=outside,
        ropefolder=None,
        source_folders=["src"],
        python_path=[str(external)],
        save_objectdb=False,
        save_history=False,
    )
    try:
        module = project.get_module("consumer")
        name = module.get_attribute("borrowed")
        assert name.get_object().get_name() == "Original"
        holder = name.get_object().get_module()
        assert holder.get_resource().project is outside
        assert project.find_module("late") is None
        assert project.get_resource("src/consumer.py").read().startswith(
            "from provider import Original"
        )
        assert project.get_folder("src").get_children() == [
            project.get_file("src/consumer.py")
        ]
        assert get_no_project() is singleton
        assert not root.exists()
    finally:
        project.close()


def test_snapshot_directory_acquisition_failure_is_not_an_empty_result(tmp_path):
    root = tmp_path / "consumer"
    root.mkdir()
    captured = CapturedFileSystem((str(root),))
    project = Project(
        str(root),
        fscommands=captured,
        external_project=NoProject(fscommands=captured),
        ropefolder=None,
        save_objectdb=False,
        save_history=False,
    )
    try:
        del captured.directories[str(root)]
        with pytest.raises(KeyError):
            project.get_folder("").get_children()
    finally:
        project.close()


def test_native_relative_namespace_and_stub_resources_use_captured_inputs(tmp_path):
    root = tmp_path / "consumer"
    local = root / "src"
    package = local / "application"
    external = tmp_path / "dependencies"
    namespace = external / "namespace"
    package.mkdir(parents=True)
    namespace.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "owner.py").write_text("class Local:\n    pass\n", encoding="utf-8")
    (package / "consumer.py").write_text(
        "from .owner import Local\n"
        "from namespace.owner import External\n"
        "local = Local\nexternal = External\n",
        encoding="utf-8",
    )
    (namespace / "owner.py").write_text(
        "class External:\n    pass\n", encoding="utf-8"
    )
    (local / "schema.pyi").write_text(
        "class Schema:\n    value: str\n", encoding="utf-8"
    )
    captured = CapturedFileSystem((str(root), str(external)))
    shutil.rmtree(root)
    shutil.rmtree(external)
    outside = NoProject(fscommands=captured)
    project = Project(
        str(root),
        fscommands=captured,
        external_project=outside,
        ropefolder=None,
        source_folders=["src"],
        python_path=[str(external)],
        save_objectdb=False,
        save_history=False,
    )
    try:
        consumer = project.get_module("application.consumer")
        relative = project.find_relative_module(
            "owner", project.get_folder("src/application"), 1
        )
        assert relative == project.get_resource("src/application/owner.py")
        local_owner = consumer.get_attribute("local").get_object()
        assert local_owner.get_name() == "Local"
        assert local_owner.get_module().get_resource() == relative
        external_owner = consumer.get_attribute("external").get_object()
        assert external_owner.get_name() == "External"
        assert external_owner.get_module().get_resource().project is outside
        assert project.find_module("namespace").is_folder()
        stub = project.get_resource("src/schema.pyi")
        assert project.get_pymodule(stub).get_attribute("Schema").get_object().get_name() == "Schema"
        # This port preserves Rope's existing module election: .pyi is an
        # explicitly supplied resource, not an extra module-name fallback.
        assert project.find_module("schema") is None
        assert not root.exists()
        assert not external.exists()
    finally:
        project.close()
