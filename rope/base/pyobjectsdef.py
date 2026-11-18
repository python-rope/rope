import rope.base.builtins
import rope.base.codeanalyze
import rope.base.evaluate
import rope.base.libutils
import rope.base.oi.soi
import rope.base.pyscopes
from rope.base import (
    arguments,
    ast,
    exceptions,
    fscommands,
    nameanalyze,
    pynamesdef,
    pyobjects,
    utils,
)


def _inheritance_order(pyclass):
    """Return the method resolution order of `pyclass`, or its bases walk

    A hierarchy Python refuses to create has no method resolution order;
    its ancestors then follow the bases.

    """
    mro = pyclass.get_consistent_mro()
    if mro is None:
        from rope.base.oi.type_hinting.utils import get_mro

        mro = get_mro(pyclass)
    return mro


def _mro_holds(mro, target):
    """Tell whether ``mro`` holds the class ``target`` by runtime identity.

    A runtime class can be wrapped by distinct ``BuiltinClass`` objects
    (``_runtime_class`` cache versus module attribute exposure); the
    metaclass derivation compares the wrapped runtime classes, falling back
    to object identity for source-defined classes.
    """
    target_builtin = getattr(target, "builtin", None)
    if target_builtin is not None:
        for ancestor in mro:
            if ancestor is target:
                return True
            if getattr(ancestor, "builtin", None) is target_builtin:
                return True
        return False
    return target in mro


def _base_binding_at_position(pyname, base_node):
    """Resolve a class base against the binding visible at its source position.

    Python evaluates base expressions at class-creation time. A module that
    rebinds an imported name (``from x import c`` ... ``class F(c)`` ...
    ``c = F``) resolves the base to the IMPORT binding: every recorded
    assignment of the rebinding sits after the class statement. Names without
    a retained pre-assignment binding, and names whose assignments genuinely
    precede the base, keep the scope binding.

    """
    prior = getattr(pyname, "pre_assignment_binding", None)
    if prior is None:
        return pyname
    for assignment in getattr(pyname, "assignments", ()) or ():
        node = getattr(assignment, "type_hint", None) or assignment.ast_node
        if (node.lineno, node.col_offset) <= (base_node.lineno, base_node.col_offset):
            return pyname
    return prior


def _scope_at_base_position(pycore, scope, base_node):
    """Bind the root name of a compound base as it is at the class statement.

    ``s[T]`` or ``pkg.Base`` evaluates its root name before any position
    correction can apply to the result; a later rebinding of that name (the
    facade alias ``s = Derived``) would make the class its own base.

    """
    root = base_node
    while isinstance(root, (ast.Subscript, ast.Attribute)):
        root = root.value
    if root is base_node or not isinstance(root, ast.Name):
        return scope
    pyname = scope.lookup(root.id)
    if pyname is None:
        return scope
    positioned = _base_binding_at_position(pyname, base_node)
    if positioned is pyname:
        return scope
    return rope.base.pyscopes.TemporaryScope(pycore, scope, {root.id: positioned})


def _base_is_external(cls, base_node):
    """Whether a failing base node lives in an installed third-party module.

    The base expression is evaluated in the declaring module's scope; when
    that module's file sits outside the project root, the evaluation failure
    is an analysis limitation over foreign code, never a defect of the
    governed tree.

    """
    module = cls.get_module()
    resource = module.get_resource() if module is not None else None
    if resource is None:
        return False
    project = resource.project
    if not hasattr(project, "address"):
        # NoProject resources live outside any open project, such as
        # installed libraries, so they are external by definition.
        return True
    return not str(resource.real_path).startswith(str(project.address))


class PyFunction(pyobjects.PyFunction):
    def __init__(self, pycore, ast_node, parent):
        rope.base.pyobjects.AbstractFunction.__init__(self)
        rope.base.pyobjects.PyDefinedObject.__init__(self, pycore, ast_node, parent)
        self.arguments = self.ast_node.args
        self.parameter_pyobjects = pynamesdef._Inferred(
            self._infer_parameters, self.get_module()._get_concluded_data()
        )
        self.returned = pynamesdef._Inferred(self._infer_returned)
        self.parameter_pynames = None
        self.assigned_attributes = {}

    def _create_structural_attributes(self):
        return self.assigned_attributes

    def _create_concluded_attributes(self):
        return {}

    def _create_scope(self):
        return rope.base.pyscopes.FunctionScope(self.pycore, self, _FunctionVisitor)

    def _infer_parameters(self):
        pyobjects = rope.base.oi.soi.infer_parameter_objects(self)
        self._handle_special_args(pyobjects)
        return pyobjects

    def _infer_returned(self, args=None):
        return rope.base.oi.soi.infer_returned_object(self, args)

    def _handle_special_args(self, pyobjects):
        count = len(self.get_param_names(special_args=False))
        pyobjects[:] = pyobjects[:count]
        pyobjects.extend([None] * (count - len(pyobjects)))
        if self.arguments.vararg:
            pyobjects.append(rope.base.builtins.get_list())
        if self.arguments.kwarg:
            pyobjects.append(rope.base.builtins.get_dict())

    def _set_parameter_pyobjects(self, pyobjects):
        if pyobjects is not None:
            self._handle_special_args(pyobjects)
        self.parameter_pyobjects.set(pyobjects)

    def get_parameters(self):
        if self.parameter_pynames is None:
            result = {}
            for index, name in enumerate(self.get_param_names()):
                # TODO: handle tuple parameters
                result[name] = pynamesdef.ParameterName(self, index)
            self.parameter_pynames = result
        return self.parameter_pynames

    def get_parameter(self, index):
        if index < len(self.parameter_pyobjects.get()):
            return self.parameter_pyobjects.get()[index]

    def get_returned_object(self, args):
        return self.returned.get(args)

    def get_name(self):
        return self.get_ast().name

    def get_param_names(self, special_args=True):
        return [
            name
            for kind, name in self.get_parameter_layout()
            if special_args or kind not in ("vararg", "kwarg")
        ]

    def get_parameter_layout(self):
        """Return binding kinds in the order used by parameter object slots."""
        result = [("posonly", node.arg) for node in self.arguments.posonlyargs]
        result.extend(("positional", node.arg) for node in self.arguments.args)
        result.extend(("kwonly", node.arg) for node in self.arguments.kwonlyargs)
        if self.arguments.vararg:
            result.append(("vararg", self.arguments.vararg.arg))
        if self.arguments.kwarg:
            result.append(("kwarg", self.arguments.kwarg.arg))
        return tuple(result)

    def get_positional_param_names(self):
        return [
            name
            for kind, name in self.get_parameter_layout()
            if kind in ("posonly", "positional")
        ]

    def get_keyword_param_names(self):
        return [
            name
            for kind, name in self.get_parameter_layout()
            if kind in ("positional", "kwonly")
        ]

    def get_parameter_defaults(self):
        positional = self.arguments.posonlyargs + self.arguments.args
        defaults = self.arguments.defaults
        result = {
            node.arg: default
            for node, default in zip(
                positional[len(positional) - len(defaults) :], defaults
            )
        }
        result.update(
            (node.arg, default)
            for node, default in zip(
                self.arguments.kwonlyargs, self.arguments.kw_defaults
            )
            if default is not None
        )
        return result

    def get_kind(self):
        """Get function type

        It returns one of 'function', 'method', 'staticmethod' or
        'classmethod' strs.

        """
        scope = self.parent.get_scope()
        if isinstance(self.parent, PyClass):
            for decorator in self.decorators:
                pyname = rope.base.evaluate.eval_node(scope, decorator)
                if pyname is None:
                    continue
                decorator_object = pyname.get_object()
                if not isinstance(decorator_object, rope.base.builtins.BuiltinClass):
                    continue
                if decorator_object.builtin is staticmethod:
                    return "staticmethod"
                if decorator_object.builtin is classmethod:
                    return "classmethod"
            if self.get_name() == "__class_getitem__":
                return "classmethod"
            return "method"
        return "function"

    @property
    def decorators(self):
        try:
            return self.ast_node.decorator_list
        except AttributeError:
            return getattr(self.ast_node, "decorators", None)


class PyComprehension(pyobjects.PyComprehension):
    def __init__(self, pycore, ast_node, parent):
        self.visitor_class = _ComprehensionVisitor
        rope.base.pyobjects.PyObject.__init__(self, type_="Comp")
        rope.base.pyobjects.PyDefinedObject.__init__(self, pycore, ast_node, parent)

    def _create_scope(self):
        return rope.base.pyscopes.ComprehensionScope(
            self.pycore, self, _ComprehensionVisitor
        )

    def get_kind(self):
        return "Comprehension"


class PyClass(pyobjects.PyClass):
    def __init__(self, pycore, ast_node, parent):
        self.visitor_class = _ClassVisitor
        rope.base.pyobjects.AbstractClass.__init__(self)
        rope.base.pyobjects.PyDefinedObject.__init__(self, pycore, ast_node, parent)
        self.parent = parent
        self._bases = self.get_module()._get_concluded_data()
        self._mro = self.get_module()._get_concluded_data()
        self._metaclass = self.get_module()._get_concluded_data()
        self._linearizing = False
        self._receiver_attributes_collected = False
        self._base_name_binding = None

    def _create_structural_attributes(self):
        from rope.base import externaldata

        attributes = super()._create_structural_attributes()
        attributes = externaldata.add_class_data(self, attributes)
        if any(
            rope.base.builtins._is_runtime_class(self, owner)
            for owner in (
                rope.base.builtins.typing.Generic,
                rope.base.builtins.typing.Protocol,
            )
        ):
            attributes["__class_getitem__"] = rope.base.builtins._class_getitem(
                self, self.pycore.project, True
            )
        return attributes

    def get_bases(self):
        if self._bases.get() is None:
            bases = self._get_bases()
            if any(
                isinstance(base, pyobjects.UnresolvedBase) and base.pyobject is None
                for base in bases
            ):
                # A base that cannot be evaluated yet is a transient answer
                # (inference is incomplete at that point); caching it would leave
                # a permanent UnresolvedBase in the MRO.
                return bases
            self._bases.set(bases)
        return self._bases.get()

    def get_superclasses(self):
        return [
            base
            for base in self.get_bases()
            if not isinstance(base, pyobjects.UnresolvedBase)
        ]

    def get_mro(self):
        """Return the native C3 order, retaining unresolved base witnesses.

        Linearize the current bases once and preserve hierarchy failures.
        An order containing an unresolved base is partial and is never
        cached as a complete method resolution order.
        """
        return self._linearize(strict=True)

    def get_consistent_mro(self):
        """Return `get_mro()`, or `None` when Python would refuse the class

        Cyclic, repeated and unmergeable bases give `None` instead of
        raising `rope.base.exceptions.InconsistentHierarchyError`.
        """
        return self._linearize(strict=False)

    def _linearize(self, strict):
        if self._mro.get() is None:
            # Evaluating the bases may look up attributes of this class;
            # only the linearization of the ancestors can reach it again.
            bases = self.get_bases()
            if self._linearizing:
                if not strict:
                    return None
                raise exceptions.InconsistentHierarchyError(
                    "Cyclic class inheritance: %s" % self.get_name()
                )
            self._linearizing = True
            try:
                mro = pyobjects.linearize(self, bases, strict=strict)
            finally:
                self._linearizing = False
            if mro is None or any(
                isinstance(base, pyobjects.UnresolvedBase) for base in mro
            ):
                return mro
            self._mro.set(mro)
        return self._mro.get()

    def invalidate_bases(self):
        """Drop the cached bases and MRO so the next read recomputes them.

        Call this after the inputs defining the hierarchy change.
        """
        self._bases.set(None)
        self._mro.set(None)

    def get_mro(self):
        return self._linearize(strict=True)

    def get_consistent_mro(self):
        return self._linearize(strict=False)

    def _linearize(self, strict):
        if self._mro.get() is None:
            bases = self.get_superclasses()
            if self._linearizing:
                if not strict:
                    return None
                raise exceptions.InconsistentHierarchyError(
                    "Cyclic class inheritance: %s" % self.get_name()
                )
            self._linearizing = True
            try:
                mro = pyobjects.linearize(self, bases, strict=strict)
            finally:
                self._linearizing = False
            if mro is None:
                return None
            self._mro.set(mro)
        return self._mro.get()

    def get_name(self):
        return self.get_ast().name

    def get_metaclass(self):
        if self._metaclass.get() is None:
            winner = super().get_metaclass()
            for keyword in self.ast_node.keywords:
                if keyword.arg == "metaclass":
                    binding = rope.base.evaluate.eval_node(
                        self.parent.get_scope(), keyword.value
                    )
                    if binding is None or not isinstance(
                        binding.get_object(), pyobjects.AbstractClass
                    ):
                        self._metaclass.set(
                            pyobjects.UnresolvedBase(
                                keyword.value,
                                binding.get_object() if binding is not None else None,
                            )
                        )
                        return self._metaclass.get()
                    winner = binding.get_object()
            for base in self.get_bases():
                if isinstance(base, pyobjects.UnresolvedBase):
                    self._metaclass.set(base)
                    return base
                candidate = base.get_metaclass()
                if not isinstance(candidate, pyobjects.AbstractClass):
                    self._metaclass.set(candidate)
                    return candidate
                if _mro_holds(candidate.get_mro(), winner):
                    winner = candidate
                elif not _mro_holds(winner.get_mro(), candidate):
                    raise exceptions.InconsistentHierarchyError(
                        "Conflicting metaclasses: %s" % self.get_name()
                    )
            self._metaclass.set(winner)
        return self._metaclass.get()

    def _get_structural_attributes(self):
        attributes = super()._get_structural_attributes()
        if (
            self.structural_attributes is not None
            and not self._receiver_attributes_collected
        ):
            # Resolve decorators only after all class bindings exist and the
            # structural visitor's recursion guard has been released.
            self._receiver_attributes_collected = True
            self.attributes.set(None)
            visitor = self.visitor_class(self.pycore, self)
            visitor.names = attributes
            try:
                for defined in self.defineds:
                    if (
                        isinstance(defined, PyFunction)
                        and defined.get_kind() != "staticmethod"
                    ):
                        visitor.visit_method_attributes(defined.get_ast())
            finally:
                # get_kind() can cache a view before the receiver fields exist.
                self.attributes.set(None)
        return attributes

    def _create_concluded_attributes(self):
        result = {}
        mro = self.get_consistent_mro()
        if mro is None:
            # A hierarchy Python refuses to create has no method resolution
            # order; its attributes are inherited along the bases, as rope
            # always did for such classes.
            for base in reversed(self.get_superclasses()):
                result.update(base.get_attributes())
            return result
        for ancestor in reversed(mro[1:]):
            result.update(ancestor._get_own_attributes())
        return result

    def _get_own_attributes(self):
        return self._get_structural_attributes()

    def _get_bases(self):
        if rope.base.builtins._is_runtime_class(
            self, rope.base.builtins.typing.Generic
        ):
            return rope.base.builtins._runtime_class(
                rope.base.builtins.typing.Generic
            ).get_superclasses()
        bindings = []
        for base_node in self.ast_node.bases:
            scope = self.parent.get_scope()
            if self._base_name_binding is not None:
                from rope.base.sourcebindings import TypeParameterEnvironment

                context = (
                    self.get_module()
                    ._get_source_binding_index()
                    .context_for_node(base_node)
                )
                if context is not None:
                    scope = context.environment
                names = {self.get_name(): self._base_name_binding}
                if isinstance(scope, TypeParameterEnvironment):
                    names.update(scope.get_defined_names())
                scope = rope.base.pyscopes.TemporaryScope(self.pycore, scope, names)
            scope = _scope_at_base_position(self.pycore, scope, base_node)
            try:
                evaluated = rope.base.evaluate.eval_node(scope, base_node)
                bindings.append(_base_binding_at_position(evaluated, base_node))
            except Exception as error:
                try:
                    module = self.get_module()
                    expression = ast.get_source_segment(module.source_code, base_node)
                    note = (
                        f"while evaluating base {expression!r} of "
                        f"{module.get_name()}.{self.get_name()} "
                        f"at line {base_node.lineno}"
                    )
                except Exception as diagnostic_error:
                    note = f"base evaluation context failed: {diagnostic_error!r}"
                error.__dict__.setdefault("__notes__", []).append(note)
                # A base outside the project that analysis cannot evaluate (for
                # instance a generic alias from an installed library) becomes an
                # UnresolvedBase, which callers already handle, instead of failing
                # the whole indexing. Classes of the project still propagate the
                # error, since it is a real defect there.
                if _base_is_external(self, base_node):
                    bindings.append(None)
                    continue
                raise
        original = rope.base.builtins.get_tuple(
            *(
                binding.get_object() if binding is not None else None
                for binding in bindings
            )
        )
        generic_aliases = [
            value
            for value in original.get_type().get_holding_objects()
            if isinstance(value, rope.base.builtins.GenericAlias)
            and rope.base.builtins._is_runtime_class(
                value.origin, rope.base.builtins.typing.Generic
            )
        ]
        if generic_aliases and any(
            alias != generic_aliases[0] for alias in generic_aliases[1:]
        ):
            raise TypeError("Cannot inherit from Generic[...] multiple times")
        result = []
        for base_node, binding in zip(self.ast_node.bases, bindings):
            if binding is None:
                result.append(pyobjects.UnresolvedBase(base_node))
            else:
                value = binding.get_object()
                if isinstance(value, pyobjects.AbstractClass):
                    result.append(value)
                elif "__mro_entries__" in value:
                    method, receiver = rope.base.evaluate.get_callable(
                        value["__mro_entries__"]
                    )
                    if method is None:
                        raise TypeError("__mro_entries__ must be callable")
                    if receiver is None:
                        receiver = pynamesdef.UnboundName(value)
                    args = arguments.ObjectArguments([pynamesdef.UnboundName(original)])
                    args = arguments.bind_method(
                        receiver,
                        method,
                        args,
                        self.parent.get_scope(),
                        owner=receiver.get_object().get_type(),
                    )
                    replacement = method.get_returned_object(args)
                    if replacement is None:
                        result.append(pyobjects.UnresolvedBase(base_node, value))
                        continue
                    sequence = replacement.get_type()
                    if not isinstance(sequence, rope.base.builtins.Tuple):
                        raise TypeError("__mro_entries__ must return a tuple")
                    entries = sequence.get_holding_objects()
                    # ``__mro_entries__`` derivations may hand back the raw
                    # typing origin (a GenericAlias head or a module-level
                    # alias object) instead of a rope class. A non-class
                    # entry occupies its MRO slot as an unresolved witness —
                    # raising here would abort the whole hierarchy walk for
                    # a base Python itself accepts at runtime.
                    classes = [
                        entry
                        for entry in entries
                        if isinstance(entry, pyobjects.AbstractClass)
                    ]
                    result.extend(classes)
                    if len(classes) != len(entries):
                        result.append(pyobjects.UnresolvedBase(base_node, value))
                else:
                    if isinstance(base_node, ast.Subscript):
                        origin_binding = rope.base.evaluate.eval_node(
                            scope, base_node.value
                        )
                        origin = (
                            origin_binding.get_object()
                            if origin_binding is not None
                            else None
                        )
                        if isinstance(origin, pyobjects.AbstractClass):
                            # PEP 560: a parameterized base contributes the ancestry of its
                            # origin class. When the owner's __class_getitem__ is opaque (for
                            # instance pydantic builds dynamic submodels), the value is neither
                            # a class nor exposes __mro_entries__, and the origin is the correct
                            # lower bound for the MRO.
                            result.append(origin)
                            continue
                    result.append(pyobjects.UnresolvedBase(base_node, value))
        if getattr(self.ast_node, "type_params", ()):
            generic = self.pycore.project.get_module("typing")["Generic"].get_object()
            if not isinstance(generic, pyobjects.AbstractClass):
                result.append(pyobjects.UnresolvedBase(self.ast_node, generic))
            elif not any(
                isinstance(base, pyobjects.AbstractClass)
                and generic in _inheritance_order(base)
                for base in result
            ):
                result.append(generic)
        return result

    def _create_scope(self):
        return rope.base.pyscopes.ClassScope(self.pycore, self)


class PyModule(pyobjects.PyModule):
    def __init__(self, pycore, source=None, resource=None, force_errors=False):
        ignore = pycore.project.prefs.get("ignore_syntax_errors", False)
        syntax_errors = force_errors or not ignore
        self.has_errors = False
        try:
            source, node = self._init_source(pycore, source, resource)
        except exceptions.ModuleSyntaxError:
            self.has_errors = True
            if syntax_errors:
                raise
            else:
                source = "\n"
                node = ast.parse("\n")
        self.source_code = source
        self.star_imports = []
        self.visitor_class = _GlobalVisitor
        self.coding = fscommands.read_str_coding(self.source_code)
        super().__init__(pycore, node, resource)

    def _init_source(self, pycore, source_code, resource):
        filename = "string"
        if resource:
            filename = resource.path
        try:
            if source_code is None:
                source_bytes = resource.read_bytes()
                source_code, _ = fscommands.file_data_to_unicode(source_bytes)
            else:
                if isinstance(source_code, str):
                    source_bytes = fscommands.unicode_to_file_data(source_code)
                else:
                    source_bytes = source_code
            ast_node = ast.parse(source_bytes, filename=filename)
        except SyntaxError as e:
            raise exceptions.ModuleSyntaxError(filename, e.lineno, e.msg)
        except UnicodeDecodeError as e:
            raise exceptions.ModuleSyntaxError(filename, 1, "%s" % (e.reason))
        return source_code, ast_node

    @utils.prevent_recursion(lambda: {})
    def _create_concluded_attributes(self):
        result = {}
        for star_import in self.star_imports:
            result.update(star_import.get_names())
        return result

    def _create_scope(self):
        return rope.base.pyscopes.GlobalScope(self.pycore, self)

    def get_source_binding_index(self):
        return self._get_source_binding_index()._complete()

    @utils.saveit
    def _get_source_binding_index(self):
        from rope.base.sourcebindings import SourceBindingIndex

        return SourceBindingIndex(
            self, _defer_bodies=not self.requires_header_bindings()
        )

    @utils.saveit
    def requires_header_bindings(self):
        """Whether walrus header names need binding-index preparation.

        The raw ``":=" in source_code`` scan answers a per-module constant,
        so attribute and scope reads must not repeat it per call.
        """
        return ":=" in self.source_code

    def get_attributes(self):
        if self.requires_header_bindings():
            self._get_source_binding_index().prepare_header_bindings()
        return super().get_attributes()

    def get_attribute(self, name):
        if self.requires_header_bindings():
            self._get_source_binding_index().prepare_header_bindings()
        return super().get_attribute(name)

    @property
    @utils.saveit
    def lines(self):
        """A `SourceLinesAdapter`"""
        return rope.base.codeanalyze.SourceLinesAdapter(self.source_code)

    @property
    @utils.saveit
    def logical_lines(self):
        """A `LogicalLinesFinder`"""
        return rope.base.codeanalyze.CachingLogicalLineFinder(self.lines)

    def get_name(self):
        return rope.base.libutils.modname(self.resource) if self.resource else ""


class PyPackage(pyobjects.PyPackage):
    def __init__(self, pycore, resource=None, force_errors=False):
        self.resource = resource
        init_dot_py = self._get_init_dot_py()
        if init_dot_py is not None:
            self.source_code = pycore.project.get_pymodule(
                init_dot_py, force_errors=force_errors
            ).source_code
            ast_node = pycore.project.get_pymodule(
                init_dot_py, force_errors=force_errors
            ).get_ast()
        else:
            # A namespace package has no source of its own; model it as
            # an empty module so scope and line queries work on it.
            self.source_code = "\n"
            ast_node = ast.parse(self.source_code)
        self.star_imports = []
        self.visitor_class = _GlobalVisitor
        self.coding = fscommands.read_str_coding(self.source_code)
        super().__init__(pycore, ast_node, resource)

    def _create_structural_attributes(self):
        result = {}
        # A package defines no module-level objects of its own; its names
        # come from extension/builtin submodules and its folder children.
        self.defineds = []
        modname = rope.base.libutils.modname(self.resource)
        extension_submodules = self.pycore._builtin_submodules(modname)
        for name, module in extension_submodules.items():
            result[name] = rope.base.builtins.BuiltinName(module)
        if self.resource is None:
            return result
        for name, resource in self._get_child_resources().items():
            result[name] = pynamesdef.ImportedModule(self, resource=resource)
        return result

    def _create_concluded_attributes(self):
        result = {}
        init_dot_py = self._get_init_dot_py()
        if init_dot_py:
            init_object = self.pycore.project.get_pymodule(init_dot_py)
            result.update(init_object.get_attributes())
        return result

    def _get_child_resources(self):
        result = {}
        for child in self.resource.get_children():
            if child.is_folder():
                result[child.name] = child
            elif child.name.endswith(".py") and child.name != "__init__.py":
                name = child.name[:-3]
                result[name] = child
        return result

    def _get_init_dot_py(self):
        if self.resource is not None and self.resource.has_child("__init__.py"):
            return self.resource.get_child("__init__.py")
        else:
            return None

    @property
    @utils.saveit
    def lines(self):
        """A `SourceLinesAdapter` over the package source"""
        return rope.base.codeanalyze.SourceLinesAdapter(self.source_code)

    @property
    @utils.saveit
    def logical_lines(self):
        """A `LogicalLinesFinder` over the package source"""
        return rope.base.codeanalyze.CachingLogicalLineFinder(self.lines)

    def _create_scope(self):
        module = self.get_module()
        if module is self:
            # A namespace package has no __init__.py to delegate to;
            # fall back to its own (empty) module scope instead of
            # recursing through get_scope() forever.
            return rope.base.pyscopes.GlobalScope(self.pycore, self)
        return module.get_scope()

    def get_module(self):
        init_dot_py = self._get_init_dot_py()
        if init_dot_py:
            return self.pycore.project.get_pymodule(init_dot_py)
        return self

    def get_name(self):
        return rope.base.libutils.modname(self.resource) if self.resource else ""


class _AnnAssignVisitor(ast.RopeNodeVisitor):
    def __init__(self, scope_visitor):
        self.scope_visitor = scope_visitor
        self.assigned_ast = None
        self.type_hint = None

    def _AnnAssign(self, node):
        self.assigned_ast = node.value
        self.type_hint = node.annotation

        self.visit(node.target)

    def _assigned(self, name, assignment=None):
        self.scope_visitor._assigned(name, assignment)

    def _Name(self, node):
        assignment = pynamesdef.AssignmentValue(
            self.assigned_ast, assign_type=True, type_hint=self.type_hint
        )
        self._assigned(node.id, assignment)

    def _Tuple(self, node):
        names = nameanalyze.get_name_levels(node)
        for name, levels in names:
            assignment = None
            if self.assigned_ast is not None:
                assignment = pynamesdef.AssignmentValue(self.assigned_ast, levels)
            self._assigned(name, assignment)

    def _Annotation(self, node):
        pass

    def _Attribute(self, node):
        pass

    def _Subscript(self, node):
        pass

    def _Slice(self, node):
        pass


class _ExpressionVisitor(ast.RopeNodeVisitor):
    def __init__(self, scope_visitor):
        self.scope_visitor = scope_visitor

    def _assigned(self, name, assignment=None):
        self.scope_visitor._assigned(name, assignment)

    def _GeneratorExp(self, node):
        list_comp = PyComprehension(
            self.scope_visitor.pycore, node, self.scope_visitor.owner_object
        )
        self.scope_visitor.defineds.append(list_comp)

    def _SetComp(self, node):
        self._GeneratorExp(node)

    def _ListComp(self, node):
        self._GeneratorExp(node)

    def _DictComp(self, node):
        self._GeneratorExp(node)

    def _NamedExpr(self, node):
        _AssignVisitor(self).visit(node.target)
        self.visit(node.value)


class _AssignVisitor(ast.RopeNodeVisitor):
    def __init__(self, scope_visitor):
        self.scope_visitor = scope_visitor
        self.assigned_ast = None
        self.assigned_targets = ()

    def _Assign(self, node):
        self.assigned_ast = node.value
        self.assigned_targets = node.targets
        for child_node in node.targets:
            self.visit(child_node)
        _ExpressionVisitor(self.scope_visitor).visit(node.value)

    def _TypeAlias(self, node):
        # the alias value is not recorded as an assigned value: a type
        # alias is a distinct TypeAliasType object whose value is evaluated
        # lazily, so substituting the value for the alias name is unsafe
        self.visit(node.name)

    def _assigned(self, name, assignment=None):
        self.scope_visitor._assigned(name, assignment)

    def _Name(self, node):
        assignment = None
        if self.assigned_ast is not None:
            assignment = pynamesdef.AssignmentValue(self.assigned_ast)
        self._assigned(node.id, assignment)

    def _Tuple(self, node):
        names = nameanalyze.get_name_levels(node)
        for name, levels in names:
            assignment = None
            if self.assigned_ast is not None:
                assignment = pynamesdef.AssignmentValue(self.assigned_ast, levels)
            self._assigned(name, assignment)

    def _Attribute(self, node):
        visitor = self.scope_visitor
        if not isinstance(visitor, _GlobalVisitor) or not isinstance(
            node.value, ast.Name
        ):
            return
        receiver = visitor.names.get(node.value.id)
        if not isinstance(receiver, pynamesdef.DefinedName):
            return
        function = receiver.get_object()
        if (
            not isinstance(function, PyFunction)
            or function.parent is not visitor.owner_object
        ):
            return
        if visitor.depth != 1 or len(self.assigned_targets) != 1:
            function.assigned_attributes[node.attr] = self._unresolved_attribute(
                function, node, "conditional or chained assignment"
            )
            function.attributes.set(None)
            return
        builtins_scope = rope.base.pyscopes.Scope(
            visitor.pycore, rope.base.builtins.builtins, None
        )
        scope = rope.base.pyscopes.TemporaryScope(
            visitor.pycore, builtins_scope, visitor.names
        )
        scope.pyobject = visitor.owner_object
        value = rope.base.evaluate.eval_node(scope, self.assigned_ast)
        if value is None:
            function.assigned_attributes[node.attr] = self._unresolved_attribute(
                function, node, "unresolved assignment value"
            )
            function.attributes.set(None)
            return
        from rope.base.sourcebindings import SourceValueName

        function.assigned_attributes[node.attr] = SourceValueName(
            value, value.get_object()
        )
        function.attributes.set(None)

    @staticmethod
    def _unresolved_attribute(function, target, reason):
        module = function.get_module()
        line = target.lineno
        message = (
            "Unresolved function attribute write: "
            f"{module.get_name()}:{line}: "
            f"{function.get_name()}.{target.attr} ({reason})"
        )

        def unresolved():
            raise exceptions.RopeError(message)

        return pynamesdef.EvaluatedName(unresolved, module=module, lineno=line)

    def _Subscript(self, node):
        pass

    def _Slice(self, node):
        pass


class _ScopeVisitor(_ExpressionVisitor):
    def __init__(self, pycore, owner_object):
        _ExpressionVisitor.__init__(self, scope_visitor=self)
        self.pycore = pycore
        self.owner_object = owner_object
        self.names = {}
        self.defineds = []

    def get_module(self):
        if self.owner_object is not None:
            return self.owner_object.get_module()
        else:
            return None

    def _ClassDef(self, node):
        pyclass = PyClass(self.pycore, node, self.owner_object)
        pyclass._base_name_binding = self.names.get(node.name)
        self.names[node.name] = pynamesdef.DefinedName(pyclass)
        self.defineds.append(pyclass)

    def _FunctionDef(self, node):
        pyfunction = PyFunction(self.pycore, node, self.owner_object)
        for decorator in pyfunction.decorators:
            if isinstance(decorator, ast.Name) and decorator.id == "property":
                if isinstance(self, _ClassVisitor):
                    type_ = rope.base.builtins.Property(pyfunction)
                    arg = pynamesdef.UnboundName(
                        rope.base.pyobjects.PyObject(self.owner_object)
                    )

                    def _eval(type_=type_, arg=arg):
                        return type_.get_property_object(
                            arguments.ObjectArguments([arg])
                        )

                    lineno = utils.guess_def_lineno(self.get_module(), node)

                    self.names[node.name] = pynamesdef.EvaluatedName(
                        _eval, module=self.get_module(), lineno=lineno
                    )
                    break
        else:
            self.names[node.name] = pynamesdef.DefinedName(pyfunction)
        self.defineds.append(pyfunction)

    def _AsyncFunctionDef(self, node):
        return self._FunctionDef(node)

    def _Assign(self, node):
        _AssignVisitor(self).visit(node)

    def _AnnAssign(self, node):
        _AnnAssignVisitor(self).visit(node)

    def _TypeAlias(self, node):
        _AssignVisitor(self).visit(node)
        pyname = self.names[node.name.id]
        if (
            isinstance(pyname, pynamesdef.AssignedName)
            and pyname.get_definition_location()[1] is None
        ):
            pyname.lineno = node.lineno

    def _AugAssign(self, node):
        pass

    def _add_match_capture(self, node, name):
        if name is not None:
            assignment = pynamesdef.AssignmentValue(node)
            self._assigned(name, assignment)

    def _MatchAs(self, node):
        self._add_match_capture(node, node.name)
        self.generic_visit(node)

    def _MatchStar(self, node):
        self._add_match_capture(node, node.name)

    def _MatchMapping(self, node):
        self._add_match_capture(node, node.rest)
        self.generic_visit(node)

    def _For(self, node):
        self._update_evaluated(node.target, node.iter, ".__iter__().next()")
        for child in node.body + node.orelse:
            self.visit(child)

    def _AsyncFor(self, node):
        return self._For(node)

    def _assigned(self, name, assignment):
        pyname = self.names.get(name, None)
        if pyname is None or not isinstance(pyname, pynamesdef.AssignedName):
            # Python rebinds the name on assignment: an earlier import
            # binding (ImportedName/ImportedModule) must not shadow the
            # module's own later assignment (runtime semantics).
            replacement = pynamesdef.AssignedName(module=self.get_module())
            # The replaced binding stays visible for source positions BEFORE
            # the first assignment (class bases, mid-module lookups): class
            # creation evaluates the import, not the later rebind.
            replacement.pre_assignment_binding = pyname
            pyname = replacement
        if isinstance(pyname, pynamesdef.AssignedName):
            if assignment is not None:
                node = assignment.type_hint or assignment.ast_node
                context = (
                    self.get_module()._get_source_binding_index().context_for_node(node)
                )
                assignment.branch_context = (
                    context.branch_context if context is not None else None
                )
                pyname.assignments.append(assignment)
            self.names[name] = pyname

    def _update_evaluated(
        self, targets, assigned, evaluation="", eval_type=False, type_hint=None
    ):
        result = {}
        if isinstance(targets, str):
            assignment = pynamesdef.AssignmentValue(assigned, [], evaluation, eval_type)
            self._assigned(targets, assignment)
        else:
            names = nameanalyze.get_name_levels(targets)
            for name, levels in names:
                assignment = pynamesdef.AssignmentValue(
                    assigned, levels, evaluation, eval_type
                )
                self._assigned(name, assignment)
        return result

    def _With(self, node):
        for item in node.items:
            if item.optional_vars:
                self._update_evaluated(
                    item.optional_vars, item.context_expr, ".__enter__()"
                )
        for child in node.body:
            self.visit(child)

    def _AsyncWith(self, node):
        return self._With(node)

    def _excepthandler(self, node):
        node_name_type = str
        if node.name is not None and isinstance(node.name, node_name_type):
            type_node = node.type
            if isinstance(node.type, ast.Tuple) and type_node.elts:
                type_node = type_node.elts[0]
            self._update_evaluated(node.name, type_node, eval_type=True)

        for child in node.body:
            self.visit(child)

    def _ExceptHandler(self, node):
        self._excepthandler(node)

    def _Import(self, node):
        for import_pair in node.names:
            module_name = import_pair.name
            alias = import_pair.asname
            first_package = module_name.split(".")[0]
            if alias is not None:
                imported = pynamesdef.ImportedModule(self.get_module(), module_name)
                if not self._is_ignored_import(imported):
                    self.names[alias] = imported
            else:
                imported = pynamesdef.ImportedModule(self.get_module(), first_package)
                if not self._is_ignored_import(imported):
                    self.names[first_package] = imported

    def _ImportFrom(self, node):
        level = 0
        if node.level:
            level = node.level
        imported_module = pynamesdef.ImportedModule(
            self.get_module(),
            node.module or "",
            level,
        )
        if self._is_ignored_import(imported_module):
            return
        if len(node.names) == 1 and node.names[0].name == "*":
            if isinstance(self.owner_object, PyModule):
                self.owner_object.star_imports.append(StarImport(imported_module))
        else:
            for imported_name in node.names:
                imported = imported_name.name
                alias = imported_name.asname
                if alias is not None:
                    imported = alias
                self.names[imported] = pynamesdef.ImportedName(
                    imported_module, imported_name.name
                )

    def _is_ignored_import(self, imported_module):
        if not self.pycore.project.prefs.get("ignore_bad_imports", False):
            return False
        return not isinstance(
            imported_module.get_object(), rope.base.pyobjects.AbstractModule
        )

    def _Global(self, node):
        module = self.get_module()
        for name in node.names:
            if module is not None:
                try:
                    pyname = module[name]
                except exceptions.AttributeNotFoundError:
                    pyname = pynamesdef.AssignedName(node.lineno)
            self.names[name] = pyname


class _ComprehensionVisitor(_ScopeVisitor):
    def _comprehension(self, node):
        self.visit(node.target)
        self.visit(node.iter)

    def _Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.names[node.id] = self._get_pyobject(node)

    def _get_pyobject(self, node):
        return pynamesdef.AssignedName(lineno=node.lineno, module=self.get_module())


class _GlobalVisitor(_ScopeVisitor):
    """Build module bindings without treating inactive version imports as live.

    A direct import-only guard may select a branch only after an import-only
    standard-library prelude authenticates its ``sys`` binding and runtime.
    The source AST remains complete; mixed scopes, TYPE_CHECKING and unproved
    conditions retain their existing traversal and declaration identities.
    """

    def __init__(self, pycore, owner_object):
        super().__init__(pycore, owner_object)
        self.depth = 0

    def _If(self, node):
        selected = rope.base.evaluate._header_version_guard(
            self.get_module(), self.names, node
        )
        if selected is None:
            return self.generic_visit(node)
        for statement in node.body if selected else node.orelse:
            self.visit(statement)

    def visit(self, node):
        self.depth += 1
        try:
            return super().visit(node)
        finally:
            self.depth -= 1


class _ClassVisitor(_ScopeVisitor):
    def visit_method_attributes(self, node):
        positional = node.args.posonlyargs + node.args.args
        if positional:
            first = positional[0]
            new_visitor = None
            if isinstance(first, ast.arg):
                new_visitor = _ClassInitVisitor(self, first.arg)
            if new_visitor is not None:
                for child in ast.iter_child_nodes(node):
                    new_visitor.visit(child)


class _FunctionVisitor(_ScopeVisitor):
    def __init__(self, pycore, owner_object):
        super().__init__(pycore, owner_object)
        self.returned_asts = []
        self.generator = False

    def _Return(self, node):
        if node.value is not None:
            self.returned_asts.append(node.value)

    def _Yield(self, node):
        if node.value is not None:
            self.returned_asts.append(node.value)
        self.generator = True


class _ClassInitVisitor(_AssignVisitor):
    def __init__(self, scope_visitor, self_name):
        super().__init__(scope_visitor)
        self.self_name = self_name

    def _Attribute(self, node):
        if not isinstance(node.ctx, ast.Store):
            return
        if isinstance(node.value, ast.Name) and node.value.id == self.self_name:
            if node.attr not in self.scope_visitor.names:
                self.scope_visitor.names[node.attr] = pynamesdef.AssignedName(
                    lineno=node.lineno, module=self.scope_visitor.get_module()
                )
            if self.assigned_ast is not None:
                pyname = self.scope_visitor.names[node.attr]
                if isinstance(pyname, pynamesdef.AssignedName):
                    pyname.assignments.append(
                        pynamesdef.AssignmentValue(self.assigned_ast)
                    )

    def _Tuple(self, node):
        if not isinstance(node.ctx, ast.Store):
            return
        for child in ast.iter_child_nodes(node):
            self.visit(child)

    def _Name(self, node):
        pass

    def _FunctionDef(self, node):
        pass

    def _ClassDef(self, node):
        pass

    def _For(self, node):
        pass

    def _With(self, node):
        pass


class StarImport:
    def __init__(self, imported_module):
        self.imported_module = imported_module

    def get_names(self):
        result = {}
        imported = self.imported_module.get_object()
        for name in imported:
            if not name.startswith("_"):
                result[name] = pynamesdef.ImportedName(self.imported_module, name)
        return result
