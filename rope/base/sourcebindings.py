"""Canonical source identities for expression scopes and function headers.

The index is built solely from the module AST.  Structural scopes are resolved
only after construction, so looking up a decorator cannot recursively build a
partially published index.  Source identities never contain call-time values.
"""

import sys
from dataclasses import dataclass

from rope.base import (
    ast,
    codeanalyze,
    exceptions,
    nameanalyze,
    pynames,
    pyobjects,
    pyscopes,
)


def _resolved(environment):
    if isinstance(environment, _StructuralReference):
        return environment.resolve()
    return environment


class _StructuralReference:
    """An AST owner, without forcing Rope's structural visitor during build."""

    def __init__(self, index, node, parent=None, entry=None):
        self.index = index
        self.node = node
        self.parent = parent
        self.entry = parent if entry is None else entry
        self._scope = None
        self.header_slots = {}
        self.redirected_headers = {}
        self._installed_slots = False
        self._installing_slots = False
        self.unsupported_formals = {}

    def resolve(self):
        if self._scope is None:
            if self.parent is None:
                self._scope = self.index.pymodule.get_scope()
            else:
                parent_scope = self.parent.resolve()
                for scope in parent_scope.get_scopes():
                    if scope.pyobject.get_ast() is self.node:
                        self._scope = scope
                        break
                if self._scope is None:
                    raise RuntimeError("source owner has no structural scope")
        if (
            (self.header_slots or self.redirected_headers)
            and not self._installed_slots
            and not self._installing_slots
        ):
            self._installing_slots = True
            try:
                self._install_header_slots()
                self._installed_slots = True
            finally:
                self._installing_slots = False
        return self._scope

    def _install_header_slots(self):
        from rope.base import pynamesdef

        names = self._scope.get_names()
        for name, assignments in self.header_slots.items():
            binding = names.get(name)
            if not isinstance(binding, (pynames.AssignedName, pynames.ParameterName)):
                binding = pynamesdef.AssignedName(
                    assignments[0].get_lineno(), self.index.pymodule
                )
                names[name] = binding
                if self.get_kind() in ("Module", "Class"):
                    self._scope.pyobject._get_structural_attributes()[name] = binding
                    attributes = self._scope.pyobject.attributes.get()
                    if attributes is not None:
                        attributes[name] = binding
            binding.binding_scope = self._scope
            if isinstance(binding, pynames.AssignedName):
                present = {
                    id(assignment.ast_node) for assignment in binding.assignments
                }
                binding.assignments.extend(
                    assignment
                    for assignment in assignments
                    if id(assignment.ast_node) not in present
                )
                binding.invalidate()
        for name, owner in self.redirected_headers.items():
            names[name] = owner.resolve().get_names()[name]

    def lookup(self, name):
        return self.resolve().lookup(name)

    def _propagated_lookup(self, name):
        return self.resolve()._propagated_lookup(name)

    def get_names(self):
        return self.resolve().get_names()

    def get_defined_names(self):
        return self.resolve().get_defined_names()

    def get_propagated_names(self):
        return self.resolve().get_propagated_names()

    def get_module(self):
        return self.index.pymodule

    def get_region(self):
        return self.resolve().get_region()

    def __getattr__(self, name):
        return getattr(self.resolve(), name)

    def get_kind(self):
        if isinstance(self.node, ast.ClassDef):
            return "Class"
        if isinstance(self.node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return "Function"
        return "Module"

    @property
    def pyobject(self):
        return self.resolve().pyobject


class _PropagationView:
    """Use an enclosing environment without inheriting ordinary class names."""

    def __init__(self, environment):
        self.environment = environment
        self.parent = environment.parent

    def lookup(self, name):
        return self.environment._propagated_lookup(name)

    def _propagated_lookup(self, name):
        return self.lookup(name)

    def get_names(self):
        return self.environment.get_propagated_names()

    def get_propagated_names(self):
        return self.get_names()

    def __getattr__(self, name):
        return getattr(self.environment, name)


@dataclass(frozen=True)
class AnnotationPolicy:
    mode: str
    runtime_profile: tuple
    resolver_contract: str


@dataclass(frozen=True)
class SourceContext:
    _environment: object
    _structural_scope: object
    source_node: object
    role: str
    annotation_owner: object = None
    annotation_policy: object = None

    @property
    def environment(self):
        return _resolved(self._environment)

    @property
    def structural_scope(self):
        return _resolved(self._structural_scope)


@dataclass(frozen=True)
class SourceFragment:
    start: int
    end: int
    depth: int
    context: SourceContext


class SourceLocalName(pynames.AssignedName):
    def __init__(self, environment, name, node):
        self.environment = environment
        self.binding_scope = environment
        self.name = name
        self.node = node
        self.assignments = []
        self._value_name = None

    def get_object(self):
        if self.assignments:
            if self._value_name is None:
                from rope.base import pynamesdef

                self._value_name = pynamesdef.AssignedName(
                    self.node.lineno, self.environment.get_module()
                )
                self._value_name.assignments.extend(self.assignments)
            return self._value_name.get_object()
        return pyobjects.get_unknown()

    def get_definition_location(self):
        return self.environment.get_module(), self.node.lineno

    def invalidate(self):
        if self._value_name is not None:
            self._value_name.invalidate()


class LambdaParameterName(pynames.ParameterName):
    def __init__(self, pyfunction, name, index, node):
        self.pyfunction = pyfunction
        self.binding_scope = pyfunction.get_scope()
        self.name = name
        self.index = index
        self.node = node

    def get_object(self):
        return pyobjects.get_unknown()

    def get_objects(self):
        return []

    def get_definition_location(self):
        return self.pyfunction.get_module(), self.node.lineno


class TypeParameterName(SourceLocalName):
    pass


class SourceValueName(pynames.PyName):
    """An attribute's call value, retaining its canonical source name."""

    def __init__(self, source_pyname, pyobject):
        self.source_pyname = source_pyname
        self.pyobject = pyobject

    def get_object(self):
        return self.pyobject

    def get_definition_location(self):
        return self.source_pyname.get_definition_location()

    def __getattr__(self, name):
        return getattr(self.source_pyname, name)


def source_lambda_attribute_value(primary, attribute):
    """Separate an initializer's lambda value from the class namespace value."""
    from rope.base import evaluate

    receiver = primary.get_object()
    class_access = isinstance(receiver, pyobjects.AbstractClass)
    receiver_class = receiver if class_access else receiver.get_type()
    if not isinstance(receiver_class, pyobjects.PyClass):
        return None
    module, _ = attribute.get_definition_location()
    if module is None:
        return None
    index = module.get_source_binding_index()
    storage = {"class": [], "instance": []}
    for assignment in getattr(attribute, "assignments", ()):
        context = index.context_for_node(assignment.ast_node)
        if context is None or assignment.levels:
            continue
        owner = context.structural_scope
        if owner.get_kind() == "Class" and owner.pyobject is receiver_class:
            kind = "class"
        elif (
            owner.get_kind() == "Function"
            and owner.pyobject.parent is receiver_class
            and owner.pyobject.get_name() == "__init__"
            and owner.pyobject.get_kind() == "method"
        ):
            kind = "instance"
        else:
            continue
        if any(
            isinstance(statement, (ast.Assign, ast.AnnAssign))
            and statement.value is assignment.ast_node
            for statement in owner.pyobject.get_ast().body
        ):
            storage[kind].append((assignment, context))
    if not storage["class"] or not storage["instance"]:
        return None
    assignment, context = storage["class" if class_access else "instance"][-1]
    value = evaluate.eval_node(context.environment, assignment.ast_node)
    function = value.get_object() if value is not None else None
    if isinstance(function, SourceLambdaFunction):
        return SourceValueName(attribute, function)
    return None


class OpaqueSourceName(pynames.PyName):
    is_refactoring_identity_safe = False

    def __init__(self, environment, name, node, candidates):
        self.environment = environment
        self.name = name
        self.node = node
        self.reason = "generic annotation resolver identity is not established"
        self.candidate_environments = tuple(candidates)

    def get_object(self):
        return pyobjects.get_unknown()

    def get_definition_location(self):
        return self.environment.get_module(), self.node.lineno

    @property
    def candidate_binders(self):
        result = []
        for environment in self.candidate_environments:
            candidate = environment.lookup(self.name)
            if candidate is not None and candidate is not self:
                if (
                    not isinstance(candidate, OpaqueSourceName)
                    and candidate not in result
                ):
                    result.append(candidate)
        return tuple(result)

    def may_reference(self, pyname):
        from rope.refactor.occurrences import same_pyname

        return any(
            same_pyname(candidate, pyname) for candidate in self.candidate_binders
        )


class UnsupportedFormalName(OpaqueSourceName):
    """A readable lexical binder outside the ordinary function's old protocol."""

    def __init__(self, environment, name, node):
        super().__init__(environment, name, node, ())
        self.binding_scope = environment
        self.reason = "ordinary function parameter category is not supported"


@dataclass(frozen=True)
class OpaqueReference:
    node: object
    context: SourceContext
    pyname: OpaqueSourceName

    def may_reference(self, pyname):
        return self.pyname.may_reference(pyname)


class _SourceObject(pyobjects.PyObject):
    def __init__(self, environment):
        super().__init__(pyobjects.get_base_type("Unknown"))
        self.environment = environment

    def get_module(self):
        return self.environment.get_module()

    def get_scope(self):
        return self.environment

    def get_ast(self):
        return self.environment.node

    def get_attributes(self):
        return self.environment.get_names()

    def get_kind(self):
        return self.environment.get_kind()


class BindingEnvironment(pyscopes.Scope):
    def __init__(self, index, node, parent, structural_scope, kind):
        self.index = index
        self.node = node
        self.structural_reference = structural_scope
        self.kind = kind
        self.names = {}
        self.children = []
        self.capture_parent = parent
        super().__init__(index.pymodule.pycore, _SourceObject(self), parent)

    @property
    def structural_scope(self):
        return _resolved(self.structural_reference)

    def get_module(self):
        return self.index.pymodule

    def get_names(self):
        return self.names

    def get_defined_names(self):
        return self.names

    def _create_scopes(self):
        return []

    def get_binding_scopes(self):
        return tuple(self.children)

    def get_kind(self):
        return self.kind

    def get_start(self):
        return self.node.lineno

    def get_end(self):
        return getattr(self.node, "end_lineno", self.node.lineno)

    def get_body_start(self):
        return self.get_start()

    def get_logical_end(self):
        return self.get_end()

    def get_region(self):
        return self.index._span(self.node)

    def _get_global_scope(self):
        return self.index.pymodule.get_scope()

    start = property(get_start)
    end = property(get_end)
    logical_end = property(get_logical_end)


class AnnotationEnvironment(BindingEnvironment):
    def __init__(
        self, index, node, entry, owner, policy, generic_names, candidates=None
    ):
        super().__init__(index, node, entry, owner, "Annotation")
        self.policy = policy
        self.capture_parent = index._capture(entry)
        self.generic_names = generic_names
        self.candidates = candidates
        self.opaque_names = {}

    def lookup(self, name):
        if name in self.generic_names:
            if name not in self.opaque_names:
                candidates = self.candidates or self.index._candidate_environments(
                    self.parent
                )
                self.opaque_names[name] = OpaqueSourceName(
                    self, name, self.node, candidates
                )
            return self.opaque_names[name]
        class_reference = self.parent
        if isinstance(class_reference, _GenericOwnerEnvironment):
            class_reference = class_reference.structural_reference
        if (
            self.policy.mode in ("eager", "lazy")
            and isinstance(class_reference, _StructuralReference)
            and class_reference.get_kind() == "Class"
        ):
            cutoff = self.node if self.policy.mode == "eager" else None
            status = self.index._class_binding_before(
                class_reference.node, name, cutoff
            )
            if status == "absent":
                return self.index._class_fallback(class_reference, name).lookup(name)
            if status == "ambiguous":
                if name not in self.opaque_names:
                    fallback = self.index._class_fallback(class_reference, name)
                    self.opaque_names[name] = OpaqueSourceName(
                        self, name, self.node, (class_reference, fallback)
                    )
                return self.opaque_names[name]
        return self.parent.lookup(name)

    def _propagated_lookup(self, name):
        return self.lookup(name)

    def get_names(self):
        names = set(self.generic_names)
        environment = self.parent
        direct = True
        while environment is not None:
            visible = (
                environment.get_names()
                if direct
                else environment.get_propagated_names()
            )
            names.update(visible)
            if not isinstance(environment, TypeParameterEnvironment):
                direct = False
            environment = environment.parent
        result = {}
        for name in names:
            binding = self.lookup(name)
            if binding is not None:
                result[name] = binding
        return result

    def get_propagated_names(self):
        return self.get_names()


class TypeAliasEnvironment(AnnotationEnvironment):
    """A lazy alias resolver with its own canonical type parameters."""

    def __init__(self, index, node, entry, generic, owner):
        super().__init__(
            index,
            node,
            generic,
            owner,
            index.alias_policy,
            index._generic_names(generic),
        )
        self.entry_environment = entry

    def _class_reference(self):
        entry = self.entry_environment
        if isinstance(entry, _GenericOwnerEnvironment) and entry.kind == "Class":
            entry = entry.structural_reference
        if isinstance(entry, _StructuralReference) and entry.get_kind() == "Class":
            return entry
        return None

    def _parameter_environment(self, name):
        environment = self.parent
        while environment is not None:
            if (
                isinstance(environment, TypeParameterEnvironment)
                and name in environment.names
            ):
                return environment
            environment = environment.parent
        return None

    def opaque_binding(self, name):
        class_reference = self._class_reference()
        if class_reference is None:
            return None
        status = self.index._class_binding_before(class_reference.node, name, None)
        parameter = self._parameter_environment(name)
        if parameter is not None and status != "absent":
            candidates = (class_reference, parameter)
        elif parameter is None and status == "ambiguous":
            candidates = (
                class_reference,
                self.index._class_fallback(class_reference, name),
            )
        else:
            return None
        if name not in self.opaque_names:
            self.opaque_names[name] = OpaqueSourceName(
                self, name, self.node, candidates
            )
        return self.opaque_names[name]

    def lookup(self, name):
        opaque = self.opaque_binding(name)
        if opaque is not None:
            return opaque
        class_reference = self._class_reference()
        if class_reference is not None and name not in self.generic_names:
            status = self.index._class_binding_before(class_reference.node, name, None)
            if status == "absent":
                return self.index._class_fallback(class_reference, name).lookup(name)
        return self.parent.lookup(name)


class ComprehensionBindingScope(BindingEnvironment):
    pass


class LambdaBindingScope(BindingEnvironment):
    pass


class TypeParameterEnvironment(BindingEnvironment):
    def lookup(self, name):
        return self.names[name] if name in self.names else self.parent.lookup(name)


class _LambdaArgumentValues:
    """Match values locally without changing the ordinary Arguments protocol."""

    def __init__(self, function, receiver):
        self.function = function
        self.receiver_name = (
            function.positional[0]
            if receiver is not None and function.positional
            else None
        )

    def match(self, argument_nodes, argument_scope):
        from rope.base import evaluate

        values = {}
        positional = [
            name for name in self.function.positional if name != self.receiver_name
        ]
        keyword_names = set(self.function.keywords) - {self.receiver_name}
        next_position = 0
        expanded_position = False
        expanded_keyword = False
        keyword_supplied = set()
        conflicts = set()
        for node in argument_nodes:
            if isinstance(node, ast.Starred):
                expanded_position = True
            elif isinstance(node, ast.keyword):
                if node.arg is None:
                    expanded_keyword = True
                elif node.arg in keyword_names:
                    if node.arg in values:
                        conflicts.add(node.arg)
                    keyword_supplied.add(node.arg)
                    values[node.arg] = evaluate.eval_node(argument_scope, node.value)
            elif not expanded_position:
                if next_position < len(positional):
                    values[positional[next_position]] = evaluate.eval_node(
                        argument_scope, node
                    )
                next_position += 1
        for name in tuple(values):
            if (
                name in conflicts
                or (expanded_keyword and name in keyword_names)
                or (
                    expanded_position
                    and name in positional
                    and name in keyword_supplied
                )
            ):
                values[name] = None
        for name, expression in self.function.defaults.items():
            if name in values or name == self.receiver_name:
                continue
            if expanded_position and name in positional:
                continue
            if expanded_keyword and name in keyword_names:
                continue
            values[name] = evaluate.eval_node(
                _resolved(self.function.creation_scope), expression
            )
        return values


class SourceLambdaFunction(pyobjects.AbstractFunction):
    def __init__(self, index, node, creation_scope, scope):
        super().__init__()
        self.index = index
        self.node = node
        self.creation_scope = creation_scope
        self.source_function = self
        self.bound_creation_scope = None
        self.bound_receiver = None
        self.descriptor_kind = "function"
        self.scope = scope
        args = node.args
        self.posonly = [arg.arg for arg in args.posonlyargs]
        self.positional = self.posonly + [arg.arg for arg in args.args]
        self.keywords = [arg.arg for arg in args.args + args.kwonlyargs]
        self.param_names = self.positional + [arg.arg for arg in args.kwonlyargs]
        if args.vararg is not None:
            self.param_names.append(args.vararg.arg)
        if args.kwarg is not None:
            self.param_names.append(args.kwarg.arg)
        self.defaults = dict(
            zip(
                self.positional[len(self.positional) - len(args.defaults) :],
                args.defaults,
            )
        )
        self.defaults.update(
            (arg.arg, default)
            for arg, default in zip(args.kwonlyargs, args.kw_defaults)
            if default is not None
        )

    def get_parameters(self):
        return {name: self.scope.names[name] for name in self.param_names}

    def bind_creation_scope(self, scope):
        bound = object.__new__(SourceLambdaFunction)
        bound.__dict__ = dict(self.__dict__)
        bound.source_function = self.source_function
        bound.bound_creation_scope = scope
        bound.creation_scope = scope
        return bound

    def as_descriptor(self, kind):
        descriptor = object.__new__(SourceLambdaFunction)
        descriptor.__dict__ = dict(self.__dict__)
        descriptor.descriptor_kind = kind
        return descriptor

    def bind_receiver(self, receiver):
        bound = object.__new__(SourceLambdaFunction)
        bound.__dict__ = dict(self.__dict__)
        bound.bound_receiver = receiver
        return bound

    def descriptor_receiver(self, primary, attribute):
        from rope.base import evaluate

        if self.bound_receiver is not None:
            return None
        receiver = primary.get_object()
        receiver_class = (
            receiver
            if isinstance(receiver, pyobjects.AbstractClass)
            else receiver.get_type()
        )
        if not isinstance(receiver_class, pyobjects.PyClass):
            return None
        module, _ = attribute.get_definition_location()
        if module is None:
            return None
        class_storage = False
        for assignment in getattr(attribute, "assignments", ()):
            context = module.get_source_binding_index().context_for_node(
                assignment.ast_node
            )
            if context is None or context.structural_scope.get_kind() != "Class":
                continue
            value = evaluate.eval_node(context.environment, assignment.ast_node)
            assigned = value.get_object() if value is not None else None
            if (
                isinstance(assigned, SourceLambdaFunction)
                and assigned.source_function is self.source_function
            ):
                class_storage = True
                break
        if not class_storage or self.descriptor_kind == "staticmethod":
            return None
        if self.descriptor_kind == "classmethod":
            return pynames.UnboundName(receiver_class)
        if not isinstance(receiver, pyobjects.AbstractClass):
            return primary
        return None

    @property
    def parent(self):
        return self.scope.structural_scope.pyobject

    def get_param_names(self, special_args=True):
        if not special_args:
            return self.positional + [arg.arg for arg in self.node.args.kwonlyargs]
        return list(self.param_names)

    def get_positional_param_names(self):
        return list(self.positional)

    def get_keyword_param_names(self):
        return list(self.keywords)

    def get_parameter_defaults(self):
        return dict(self.defaults)

    def get_scope(self):
        return self.scope

    def get_module(self):
        return self.index.pymodule

    def get_ast(self):
        return self.node

    def get_name(self):
        return "lambda"

    def get_kind(self):
        return "lambda"

    def get_attributes(self):
        return {}

    def get_returned_object(self, arguments):
        from rope.base import arguments as argument_matching
        from rope.base import evaluate

        values = {}
        receiver = self.bound_receiver
        if isinstance(arguments, argument_matching.MixedArguments):
            if receiver is None:
                receiver = arguments.pyname
            arguments = arguments.args
        if arguments is not None and hasattr(arguments, "args"):
            values.update(
                _LambdaArgumentValues(self, receiver).match(
                    arguments.args, arguments.scope
                )
            )
        elif arguments is not None:
            values.update(
                zip(self.param_names, arguments.get_pynames(self.param_names))
            )
        else:
            values.update(
                _LambdaArgumentValues(self, receiver).match(
                    [], _resolved(self.creation_scope)
                )
            )
        if receiver is not None and self.positional:
            values[self.positional[0]] = receiver
        for name in self.param_names:
            if values.get(name) is None:
                values[name] = pynames.UnboundName()
        capture = self.bound_creation_scope
        if capture is None:
            capture = _resolved(self.scope.parent)
        overlay = evaluate.SourceValueScope(self.scope, capture, values)
        result = evaluate.eval_node(overlay, self.node.body)
        return result.get_object() if result is not None else pyobjects.get_unknown()


class SourceBindingIndex:
    def __init__(self, pymodule):
        self.pymodule = pymodule
        self.source = pymodule.source_code
        self.fragments = []
        self._fragment_positions = {}
        self.node_contexts = {}
        self.token_bindings = []
        self.source_callables = {}
        self.comprehensions = {}
        self.environments = []
        self._opaque_references = []
        self.lines = codeanalyze.ASTLinesAdapter(self.source)
        tree = pymodule.get_ast()
        self.global_reference = _StructuralReference(self, tree)
        self.owner_references = [self.global_reference]
        self._preparing_headers = False
        self._class_symbols = {}
        self.future_annotations = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
            and any(alias.name == "annotations" for alias in node.names)
            for node in tree.body
        )
        mode = (
            "future-string"
            if self.future_annotations
            else "lazy" if sys.version_info >= (3, 14) else "eager"
        )
        self.policy = AnnotationPolicy(
            mode,
            sys.version_info[:2],
            "default-function-hints" if self.future_annotations else "source-value",
        )
        self.alias_policy = AnnotationPolicy(
            "lazy", sys.version_info[:2], "source-value"
        )
        self.state = "BUILDING"
        self._visit(tree, self.global_reference, self.global_reference, "module", 0)
        self._owners_by_node = {
            id(owner.node): owner for owner in self.owner_references
        }
        self.fragments.sort(key=lambda item: (item.start, item.end, item.depth))
        self.state = "FROZEN"

    def _span(self, node):
        if not hasattr(node, "lineno"):
            return 0, len(self.source)
        return self.lines[node]

    def _record(self, node, environment, owner, role, depth, annotation=None):
        if not hasattr(node, "lineno") and not isinstance(node, ast.Module):
            return None
        context = SourceContext(
            environment,
            owner,
            node,
            role,
            annotation,
            (
                (
                    self.alias_policy
                    if isinstance(annotation, getattr(ast, "TypeAlias", ()))
                    else self.policy
                )
                if annotation is not None
                else None
            ),
        )
        self.node_contexts[id(node)] = context
        if hasattr(node, "lineno"):
            start, end = self._span(node)
            fragment = SourceFragment(start, end, depth, context)
            position = self._fragment_positions.get(id(node))
            if position is None:
                self._fragment_positions[id(node)] = len(self.fragments)
                self.fragments.append(fragment)
            else:
                self.fragments[position] = fragment
        return context

    def context_at(self, offset):
        matched = [item for item in self.fragments if item.start <= offset < item.end]
        if matched:
            return max(
                matched, key=lambda item: (item.depth, -item.end + item.start)
            ).context
        scope = self.pymodule.get_scope().get_structural_scope_for_offset(offset)
        return SourceContext(scope, scope, self.pymodule.get_ast(), "structure")

    def context_for_node(self, node):
        return self.node_contexts.get(id(node))

    def binding_for_token(self, offset):
        for start, end, binding in self.token_bindings:
            if start <= offset < end:
                if isinstance(binding, tuple):
                    owner, name = binding
                    return owner.resolve().get_names().get(name)
                return binding
        return None

    def callable_for_node(self, node):
        return self.source_callables.get(id(node))

    def comprehension_scope(self, node):
        return self.comprehensions.get(id(node))

    def prepare_header_bindings(self, scope=None):
        if self.state == "FROZEN" and not self._preparing_headers:
            self._preparing_headers = True
            try:
                if scope is not None:
                    owner = self._owners_by_node.get(id(scope.pyobject.get_ast()))
                    if owner is not None and (
                        owner.header_slots or owner.redirected_headers
                    ):
                        owner._scope = scope
                        owner.resolve()
                else:
                    for owner in self.owner_references:
                        if (
                            owner.header_slots or owner.redirected_headers
                        ) and owner.get_kind() in ("Module", "Class"):
                            owner.resolve()
            finally:
                self._preparing_headers = False

    def install_unsupported_formals(self, scope):
        owner = self._owners_by_node.get(id(scope.pyobject.get_ast()))
        if owner is not None:
            scope.names.update(owner.unsupported_formals)

    def opaque_references(self):
        known = {id(reference.node) for reference in self._opaque_references}
        for context in tuple(self.node_contexts.values()):
            node = context.source_node
            if (
                context.annotation_owner is not None
                and isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and id(node) not in known
            ):
                binding = context.environment.lookup(node.id)
                if isinstance(binding, OpaqueSourceName):
                    self._opaque_references.append(
                        OpaqueReference(node, context, binding)
                    )
                    known.add(id(node))
        return tuple(self._opaque_references)

    def children_of(self, environment):
        if isinstance(environment, BindingEnvironment):
            return tuple(environment.children)
        return tuple(
            candidate
            for candidate in self.environments
            if _resolved(candidate.parent) is environment
        )

    def _capture(self, environment):
        if isinstance(environment, TypeAliasEnvironment):
            return environment.capture_parent
        if isinstance(environment, AnnotationEnvironment):
            if environment.generic_names:
                capture = AnnotationEnvironment(
                    self,
                    environment.node,
                    environment.capture_parent,
                    environment.structural_reference,
                    environment.policy,
                    environment.generic_names,
                    environment.candidates,
                )
                capture.opaque_names = environment.opaque_names
                return self._environment(capture)
            return environment.capture_parent
        if (
            isinstance(environment, _GenericOwnerEnvironment)
            and environment.kind == "Class"
        ):
            return _PropagationView(environment.parent)
        if isinstance(environment, TypeParameterEnvironment):
            return _PropagationView(environment)
        if (
            isinstance(environment, _StructuralReference)
            and environment.get_kind() == "Class"
        ):
            return self._capture(environment.entry)
        return environment

    def _candidate_environments(self, environment):
        result = []
        while environment is not None:
            if environment not in result:
                result.append(environment)
            environment = environment.parent
        if self.global_reference not in result:
            result.append(self.global_reference)
        return result

    def _environment(self, environment):
        self.environments.append(environment)
        if isinstance(environment.parent, BindingEnvironment):
            environment.parent.children.append(environment)
        return environment

    def _token(self, node, name, binding):
        start = self._span(node)[0]
        while self.source[start : start + 1] == "*":
            start += 1
        self.token_bindings.append((start, start + len(name), binding))

    def _generic_names(self, environment):
        names = set()
        while environment is not None:
            if isinstance(environment, TypeParameterEnvironment):
                names.update(environment.names)
            environment = environment.parent
        return names

    def _class_fallback(self, reference, name):
        names, globals_, nonlocals = self._class_lexical_symbols(reference.node)
        if name in globals_ or (name in names and name not in nonlocals):
            return self.global_reference
        return _PropagationView(reference.entry)

    def _class_lexical_symbols(self, node):
        cached = self._class_symbols.get(id(node))
        if cached is not None:
            return cached
        names, globals_, nonlocals = set(), set(), set()

        def visit(expression):
            if isinstance(expression, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(expression.name)
                headers = expression.decorator_list + expression.args.defaults
                headers += [
                    value for value in expression.args.kw_defaults if value is not None
                ]
                if self.policy.mode == "eager":
                    arguments = (
                        expression.args.posonlyargs
                        + expression.args.args
                        + expression.args.kwonlyargs
                    )
                    arguments += [
                        arg
                        for arg in (expression.args.vararg, expression.args.kwarg)
                        if arg is not None
                    ]
                    headers += [
                        arg.annotation
                        for arg in arguments
                        if arg.annotation is not None
                    ]
                    if expression.returns is not None:
                        headers.append(expression.returns)
                for header in headers:
                    visit(header)
                return
            if isinstance(expression, ast.ClassDef):
                names.add(expression.name)
                for header in expression.decorator_list + expression.bases:
                    visit(header)
                for keyword in expression.keywords:
                    visit(keyword.value)
                return
            if isinstance(expression, ast.Lambda):
                for default in expression.args.defaults + [
                    value for value in expression.args.kw_defaults if value is not None
                ]:
                    visit(default)
                return
            if isinstance(
                expression, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
            ):
                visit(expression.generators[0].iter)
                return
            if isinstance(expression, ast.Name) and isinstance(
                expression.ctx, (ast.Store, ast.Del)
            ):
                names.add(expression.id)
            elif isinstance(expression, ast.Global):
                globals_.update(expression.names)
            elif isinstance(expression, ast.Nonlocal):
                nonlocals.update(expression.names)
            elif isinstance(expression, (ast.Import, ast.ImportFrom)):
                names.update(
                    alias.asname or alias.name.split(".")[0]
                    for alias in expression.names
                )
            elif isinstance(expression, ast.ExceptHandler) and expression.name:
                names.add(expression.name)
            elif (
                isinstance(expression, (ast.MatchAs, ast.MatchStar)) and expression.name
            ):
                names.add(expression.name)
            elif isinstance(expression, ast.MatchMapping) and expression.rest:
                names.add(expression.rest)
            for child in ast.iter_child_nodes(expression):
                visit(child)

        for statement in node.body:
            visit(statement)
        result = names, globals_, nonlocals
        self._class_symbols[id(node)] = result
        return result

    def _class_binding_before(self, node, name, expression):
        status = "absent"
        for statement in node.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                headers = list(statement.decorator_list) + list(statement.args.defaults)
                headers.extend(
                    value for value in statement.args.kw_defaults if value is not None
                )
                if self.policy.mode == "eager":
                    arguments = statement.args.posonlyargs + statement.args.args
                    arguments += (
                        [statement.args.vararg]
                        if statement.args.vararg is not None
                        else []
                    )
                    arguments += statement.args.kwonlyargs
                    arguments += (
                        [statement.args.kwarg]
                        if statement.args.kwarg is not None
                        else []
                    )
                    headers.extend(
                        arg.annotation
                        for arg in arguments
                        if arg.annotation is not None
                    )
                    if statement.returns is not None:
                        headers.append(statement.returns)
                for header in headers:
                    if expression is header:
                        if self._header_binding_status(header, name) != "absent":
                            return "ambiguous"
                        return status
                    if expression is not None and statement.lineno > expression.lineno:
                        break
                    header_status = self._header_binding_status(header, name)
                    if header_status != "absent":
                        status = header_status
                if expression is not None and statement.lineno >= expression.lineno:
                    break
                if statement.name == name:
                    status = "bound"
                continue
            if expression is not None and statement.lineno >= expression.lineno:
                break
            if isinstance(statement, ast.ClassDef):
                if statement.name == name:
                    status = "bound"
                continue
            if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                if isinstance(statement, ast.AnnAssign) and statement.value is None:
                    continue
                targets = (
                    statement.targets
                    if isinstance(statement, ast.Assign)
                    else [statement.target]
                )
                if any(
                    isinstance(child, ast.Name)
                    and child.id == name
                    and isinstance(child.ctx, ast.Store)
                    for target in targets
                    for child in ast.walk(target)
                ):
                    status = "bound"
                continue
            if isinstance(statement, (ast.Import, ast.ImportFrom)):
                if any(
                    (alias.asname or alias.name.split(".")[0]) == name
                    for alias in statement.names
                ):
                    status = "bound"
                continue
            if isinstance(statement, ast.Delete):
                if any(
                    isinstance(child, ast.Name) and child.id == name
                    for child in ast.walk(statement)
                ):
                    status = "absent"
                continue
            if any(
                (
                    isinstance(child, ast.Name)
                    and child.id == name
                    and isinstance(child.ctx, (ast.Store, ast.Del))
                )
                or (
                    isinstance(child, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar))
                    and child.name == name
                )
                or (isinstance(child, ast.MatchMapping) and child.rest == name)
                for child in ast.walk(statement)
            ):
                status = "ambiguous"
        return status

    def _header_binding_status(self, expression, name):
        if isinstance(expression, ast.NamedExpr) and expression.target.id == name:
            return "bound"
        if isinstance(expression, ast.Lambda):
            expressions = expression.args.defaults + [
                value for value in expression.args.kw_defaults if value is not None
            ]
            statuses = [
                self._header_binding_status(value, name) for value in expressions
            ]
            return next(
                (status for status in reversed(statuses) if status != "absent"),
                "absent",
            )
        if any(
            isinstance(child, ast.NamedExpr) and child.target.id == name
            for child in ast.walk(expression)
        ):
            return "ambiguous"
        return "absent"

    def _header_binding_owner(self, owner, name):
        if owner.parent is None:
            return owner
        _, globals_, nonlocals = self._class_lexical_symbols(owner.node)
        if name in globals_:
            return self.global_reference
        if name not in nonlocals:
            return owner
        outer = owner.parent
        while outer is not None:
            if outer.get_kind() == "Function":
                names, outer_globals, outer_nonlocals = self._class_lexical_symbols(
                    outer.node
                )
                args = outer.node.args
                parameters = args.posonlyargs + args.args + args.kwonlyargs
                parameters += [
                    arg for arg in (args.vararg, args.kwarg) if arg is not None
                ]
                locals_ = names | {arg.arg for arg in parameters}
                if (
                    name in locals_
                    and name not in outer_globals
                    and name not in outer_nonlocals
                ):
                    return outer
            outer = outer.parent
        raise exceptions.RefactoringError(
            "Cannot resolve the declared nonlocal source binding."
        )

    def _register_header_binding(self, owner, target, value):
        declaring = self._header_binding_owner(owner, target.id)
        declaring.header_slots.setdefault(target.id, []).append(
            pynames.AssignmentValue(value)
        )
        if declaring is not owner:
            owner.redirected_headers[target.id] = declaring
        self._token(target, target.id, (declaring, target.id))
        return declaring

    def _typeparams(self, node, entry, owner, depth, visit_expressions=True):
        parameters = getattr(node, "type_params", ())
        if not parameters:
            return entry
        environment = self._environment(
            TypeParameterEnvironment(self, node, entry, owner, "TypeParameters")
        )
        for parameter in parameters:
            name = parameter.name
            binding = TypeParameterName(environment, name, parameter)
            environment.names[name] = binding
            self._record(parameter, environment, owner, "type-parameter-token", depth)
            self._token(parameter, name, binding)
        if visit_expressions:
            for parameter in parameters:
                for field in ("bound", "default_value"):
                    expression = getattr(parameter, field, None)
                    if expression is not None:
                        self._visit(
                            expression,
                            environment,
                            owner,
                            "type-parameter-expression",
                            depth + 1,
                        )
        return environment

    def _visit(self, node, environment, owner, role, depth, annotation=None):
        if node is None:
            return
        context = self._record(node, environment, owner, role, depth, annotation)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._function(node, environment, owner, depth)
            return
        if isinstance(node, getattr(ast, "TypeAlias", ())):
            generic = self._typeparams(
                node, environment, owner, depth + 1, visit_expressions=False
            )
            alias_environment = self._environment(
                TypeAliasEnvironment(self, node, environment, generic, owner)
            )
            self._visit(node.name, environment, owner, "type-alias-name", depth + 1)
            for parameter in node.type_params:
                for field in ("bound", "default_value"):
                    expression = getattr(parameter, field, None)
                    if expression is not None:
                        self._visit(
                            expression,
                            alias_environment,
                            owner,
                            "type-parameter-expression",
                            depth + 2,
                            node,
                        )
            self._visit(
                node.value,
                alias_environment,
                owner,
                "type-alias-value",
                depth + 1,
                node,
            )
            return
        if isinstance(node, ast.ClassDef):
            class_owner = _StructuralReference(self, node, owner, environment)
            self.owner_references.append(class_owner)
            generic = self._typeparams(node, environment, class_owner, depth + 1)
            for expression in node.decorator_list:
                self._visit(expression, environment, owner, "decorator", depth + 1)
            for expression in node.bases:
                self._visit(expression, generic, class_owner, "class-base", depth + 1)
            for keyword in node.keywords:
                self._visit(
                    keyword.value, generic, class_owner, "class-keyword", depth + 1
                )
            body_env = class_owner
            if self._generic_names(generic):
                body_env = self._environment(
                    _GenericOwnerEnvironment(self, node, generic, class_owner, "Class")
                )
            self._record(node, body_env, class_owner, "class-body", depth)
            for statement in node.body:
                self._visit(statement, body_env, class_owner, "class-body", depth + 1)
            return
        if isinstance(node, ast.Lambda):
            self._lambda(node, environment, owner, depth, annotation)
            return
        if isinstance(
            node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
        ):
            self._comprehension(node, environment, owner, depth, annotation)
            return
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and annotation is not None
        ):
            candidate = self._opaque_binding(environment, node.id)
            if candidate is not None:
                self._opaque_references.append(
                    OpaqueReference(node, context, candidate)
                )
        if isinstance(node, ast.NamedExpr):
            target_env = environment
            while isinstance(target_env, ComprehensionBindingScope):
                target_env = target_env.parent
            if isinstance(target_env, BindingEnvironment) and not isinstance(
                target_env, AnnotationEnvironment
            ):
                if node.target.id not in target_env.names:
                    target_env.names[node.target.id] = SourceLocalName(
                        target_env, node.target.id, node.target
                    )
                self._token(
                    node.target, node.target.id, target_env.names[node.target.id]
                )
            elif isinstance(target_env, _StructuralReference):
                target_env = self._register_header_binding(
                    target_env, node.target, node.value
                )
            elif (
                isinstance(target_env, AnnotationEnvironment)
                and target_env.policy.mode == "eager"
            ):
                declaring = target_env.parent
                while isinstance(declaring, BindingEnvironment):
                    declaring = declaring.parent
                if isinstance(declaring, _StructuralReference):
                    target_env = self._register_header_binding(
                        declaring, node.target, node.value
                    )
            self._visit(
                node.target,
                target_env,
                owner,
                "named-expression-target",
                depth + 1,
                annotation,
            )
            self._visit(node.value, environment, owner, role, depth + 1, annotation)
            return
        for child in ast.iter_child_nodes(node):
            self._visit(child, environment, owner, role, depth + 1, annotation)

    def _opaque_binding(self, environment, name):
        while isinstance(environment, BindingEnvironment):
            if name in environment.names:
                return None
            if isinstance(environment, TypeAliasEnvironment):
                return environment.opaque_binding(name)
            if isinstance(environment, AnnotationEnvironment):
                if name in environment.generic_names:
                    return environment.lookup(name)
                class_reference = environment.parent
                if isinstance(class_reference, _GenericOwnerEnvironment):
                    class_reference = class_reference.structural_reference
                if (
                    environment.policy.mode in ("eager", "lazy")
                    and isinstance(class_reference, _StructuralReference)
                    and class_reference.get_kind() == "Class"
                ):
                    cutoff = (
                        environment.node if environment.policy.mode == "eager" else None
                    )
                    if (
                        self._class_binding_before(class_reference.node, name, cutoff)
                        == "ambiguous"
                    ):
                        if name not in environment.opaque_names:
                            fallback = self._class_fallback(class_reference, name)
                            environment.opaque_names[name] = OpaqueSourceName(
                                environment,
                                name,
                                environment.node,
                                (class_reference, fallback),
                            )
                        return environment.opaque_names[name]
                return None
            environment = environment.parent
        return None

    def _function(self, node, entry, parent_owner, depth):
        owner = _StructuralReference(self, node, parent_owner, entry)
        self.owner_references.append(owner)
        generic = self._typeparams(node, entry, owner, depth + 1)
        args = node.args
        parameters = args.posonlyargs + args.args + args.kwonlyargs
        parameters += [arg for arg in (args.vararg, args.kwarg) if arg is not None]
        for parameter in parameters:
            self._record(parameter, owner, owner, "formal-token", depth + 1)
            if parameter in args.posonlyargs + args.kwonlyargs:
                binding = UnsupportedFormalName(owner, parameter.arg, parameter)
                owner.unsupported_formals[parameter.arg] = binding
                self._token(parameter, parameter.arg, binding)
            else:
                self._token(parameter, parameter.arg, (owner, parameter.arg))
        for expression in node.decorator_list:
            self._visit(expression, entry, parent_owner, "decorator", depth + 1)
        for expression in args.defaults + [
            value for value in args.kw_defaults if value is not None
        ]:
            self._visit(expression, entry, parent_owner, "function-default", depth + 1)
        annotated_parameters = args.posonlyargs + args.args
        annotated_parameters += [args.vararg] if args.vararg is not None else []
        annotated_parameters += args.kwonlyargs
        annotated_parameters += [args.kwarg] if args.kwarg is not None else []
        annotations = [
            (arg.annotation, "parameter-annotation") for arg in annotated_parameters
        ]
        annotations.append((node.returns, "return-annotation"))
        for expression, role in annotations:
            if expression is None:
                continue
            resolver = self.global_reference if self.future_annotations else generic
            names = self._generic_names(generic)
            candidates = None
            if self.future_annotations:
                own_parameters = getattr(node, "type_params", ())
                names = set(generic.names) if own_parameters else set()
                candidates = (
                    (generic, self.global_reference)
                    if own_parameters
                    else (self.global_reference,)
                )
            annotation_env = self._environment(
                AnnotationEnvironment(
                    self, expression, resolver, owner, self.policy, names, candidates
                )
            )
            self._visit(expression, annotation_env, owner, role, depth + 2, node)
        body_env = owner
        if self._generic_names(generic):
            body_env = self._environment(
                _GenericOwnerEnvironment(self, node, generic, owner, "Function")
            )
        self._record(node, body_env, owner, "function-body", depth)
        for statement in node.body:
            self._visit(statement, body_env, owner, "function-body", depth + 1)

    def _lambda(self, node, entry, owner, depth, annotation):
        environment = self._environment(
            LambdaBindingScope(self, node, self._capture(entry), owner, "Lambda")
        )
        callable_ = SourceLambdaFunction(self, node, entry, environment)
        environment.pyobject = callable_
        self._record(node, environment, owner, "lambda-body", depth, annotation)
        self.source_callables[id(node)] = callable_
        parameters = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
        parameters += [
            arg for arg in (node.args.vararg, node.args.kwarg) if arg is not None
        ]
        for number, parameter in enumerate(parameters):
            binding = LambdaParameterName(callable_, parameter.arg, number, parameter)
            environment.names[parameter.arg] = binding
            self._record(
                parameter, environment, owner, "lambda-formal", depth + 1, annotation
            )
            self._token(parameter, parameter.arg, binding)
        self._predeclare_walrus(node.body, environment)
        for expression in node.args.defaults + [
            value for value in node.args.kw_defaults if value is not None
        ]:
            self._visit(
                expression, entry, owner, "lambda-default", depth + 1, annotation
            )
        self._visit(node.body, environment, owner, "lambda-body", depth + 1, annotation)

    def _predeclare_walrus(self, node, environment):
        if isinstance(node, ast.Lambda):
            return
        if isinstance(node, ast.NamedExpr):
            if node.target.id not in environment.names:
                environment.names[node.target.id] = SourceLocalName(
                    environment, node.target.id, node.target
                )
            binding = environment.names[node.target.id]
            if isinstance(binding, SourceLocalName):
                binding.assignments.append(pynames.AssignmentValue(node.value))
        for child in ast.iter_child_nodes(node):
            self._predeclare_walrus(child, environment)

    def _comprehension(self, node, entry, owner, depth, annotation):
        environment = self._environment(
            ComprehensionBindingScope(
                self, node, self._capture(entry), owner, "Comprehension"
            )
        )
        self.comprehensions[id(node)] = environment
        self._record(node, environment, owner, "comprehension-inner", depth, annotation)
        for generator in node.generators:
            for child in ast.walk(generator.target):
                if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                    if child.id not in environment.names:
                        environment.names[child.id] = SourceLocalName(
                            environment, child.id, child
                        )
                    self._token(child, child.id, environment.names[child.id])
            for name, levels in nameanalyze.get_name_levels(generator.target):
                environment.names[name].assignments.append(
                    pynames.AssignmentValue(
                        generator.iter, levels, ".__iter__().next()"
                    )
                )
        for number, generator in enumerate(node.generators):
            self._visit(
                generator.iter,
                entry if number == 0 else environment,
                owner,
                "comprehension-first-iter" if number == 0 else "comprehension-inner",
                depth + 1,
                annotation,
            )
            self._visit(
                generator.target,
                environment,
                owner,
                "comprehension-store",
                depth + 1,
                annotation,
            )
            for condition in generator.ifs:
                self._visit(
                    condition,
                    environment,
                    owner,
                    "comprehension-inner",
                    depth + 1,
                    annotation,
                )
        for field in ("elt", "key", "value"):
            expression = getattr(node, field, None)
            if expression is not None:
                self._visit(
                    expression,
                    environment,
                    owner,
                    "comprehension-inner",
                    depth + 1,
                    annotation,
                )


class _GenericOwnerEnvironment(BindingEnvironment):
    def lookup(self, name):
        own = self.structural_scope.get_names().get(name)
        return own if own is not None else self.parent._propagated_lookup(name)

    def _propagated_lookup(self, name):
        if self.kind == "Class":
            return self.parent._propagated_lookup(name)
        return self.lookup(name)

    def get_names(self):
        return self.structural_scope.get_names()
