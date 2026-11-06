"""Conservative same-module class data writes, without descriptor inference."""

import io
import tokenize
from collections import Counter, defaultdict

from rope.base import (
    ast,
    codeanalyze,
    exceptions,
    pynames,
    pynamesdef,
    pyobjects,
    utils,
)

_CLASS_HOOKS = frozenset(
    {
        "__get__",
        "__set__",
        "__delete__",
        "__new__",
        "__getattribute__",
        "__getattr__",
        "__setattr__",
        "__delattr__",
    }
)
_VALUE_HOOKS = frozenset({"__getattribute__", "__getattr__", "__new__", "__call__"})


def _scope_nodes(body):
    pending = list(body)
    while pending:
        node = pending.pop()
        yield node
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
        ):
            continue
        if isinstance(node, ast.comprehension):
            pending.extend([node.iter, *node.ifs])
        else:
            pending.extend(ast.iter_child_nodes(node))


def _class_bindings(node):
    names, unmergeable = set(), set()
    for child in _scope_nodes(node.body):
        if isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)):
            names.add(child.id)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(child.name)
            unmergeable.add(child.name)
        elif isinstance(child, (ast.Import, ast.ImportFrom)):
            bound = {
                item.asname
                or (
                    item.name.split(".")[0]
                    if isinstance(child, ast.Import)
                    else item.name
                )
                for item in child.names
            }
            names.update(bound)
        elif isinstance(child, ast.ExceptHandler) and child.name:
            names.add(child.name)
        elif isinstance(child, (ast.MatchAs, ast.MatchStar)) and child.name:
            names.add(child.name)
        elif isinstance(child, ast.MatchMapping) and child.rest:
            names.add(child.rest)
    return names, unmergeable


class _Bindings(ast.NodeVisitor):
    def __init__(self):
        self.counts = Counter()
        self.wildcard_import = False

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.counts[node.id] += 1

    def visit_ClassDef(self, node):
        self.counts[node.name] += 1

    visit_FunctionDef = visit_ClassDef
    visit_AsyncFunctionDef = visit_ClassDef

    def visit_Lambda(self, node):
        pass

    def visit_Import(self, node):
        for item in node.names:
            self.counts[item.asname or item.name.split(".")[0]] += 1

    def visit_ImportFrom(self, node):
        for item in node.names:
            self.counts[item.asname or item.name] += 1
            if item.name == "*":
                self.wildcard_import = True

    def visit_ExceptHandler(self, node):
        if node.name:
            self.counts[node.name] += 1
        self.generic_visit(node)

    def visit_MatchAs(self, node):
        if node.name:
            self.counts[node.name] += 1
        self.generic_visit(node)

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node):
        if node.rest:
            self.counts[node.rest] += 1
        self.generic_visit(node)


class _UncertainDataName(pynames.PyName):
    def __init__(self, original):
        self.original = original

    def get_object(self):
        return pyobjects.get_unknown()

    def get_definition_location(self):
        return self.original.get_definition_location()


@utils.saveit
def _plans(module):
    tree = module.get_ast()
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    bindings = _Bindings()
    bindings.visit(tree)
    assignments = defaultdict(list)
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    # Explicit global writes belong to module identity even inside a function.
    for scope in ast.walk(tree):
        if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        nodes = list(_scope_nodes(scope.body))
        globals_ = {
            name
            for node in nodes
            if isinstance(node, ast.Global)
            for name in node.names
        }
        for node in nodes:
            names = set()
            if isinstance(node, ast.Name) and isinstance(
                node.ctx, (ast.Store, ast.Del)
            ):
                names.add(node.id)
            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                names.add(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names.update(
                    item.asname
                    or (
                        item.name.split(".")[0]
                        if isinstance(node, ast.Import)
                        else item.name
                    )
                    for item in node.names
                )
            elif isinstance(node, ast.ExceptHandler) and node.name:
                names.add(node.name)
            elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
                names.add(node.name)
            elif isinstance(node, ast.MatchMapping) and node.rest:
                names.add(node.rest)
            for name in names & globals_:
                bindings.counts[name] += 1
                parent = parents.get(node)
                if isinstance(parent, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                    assignments[name].append(parent)
                else:
                    assignments[name].append(node)

    writes = defaultdict(list)
    alias_writes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [
                child
                for target in node.targets
                for child in ast.walk(target)
                if isinstance(child, (ast.Name, ast.Attribute))
                and isinstance(child.ctx, ast.Store)
            ]
            for target in targets:
                if isinstance(target, ast.Name) and parents.get(node) is tree:
                    assignments[target.id].append(node)
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id in classes
                ):
                    writes[target.value.id, target.attr].append(node)
                elif isinstance(target, ast.Attribute) and isinstance(
                    target.value, ast.Name
                ):
                    alias_writes.append((target, node))
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            target = node.target
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id in classes
            ):
                writes[target.value.id, target.attr].append(node)
            elif isinstance(target, ast.Attribute) and isinstance(
                target.value, ast.Name
            ):
                alias_writes.append((target, node))

    def types(value, seen=()):
        if isinstance(value, (ast.Tuple, ast.List)):
            return set().union(*(types(item, seen) for item in value.elts))
        if isinstance(value, ast.Starred):
            return types(value.value, seen)
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            name = value.func.id
        elif isinstance(value, ast.Name):
            name = value.id
        else:
            return set()
        if name in seen:
            return set()
        result = {name} if name in classes else set()
        for assignment in assignments[name]:
            result.update(types(getattr(assignment, "value", None), (*seen, name)))
        return result

    def plain_class(name):
        node = classes[name]
        return (
            bindings.counts[name] == 1
            and not bindings.wildcard_import
            and not node.bases
            and not node.keywords
            and not node.decorator_list
            and not (_class_bindings(node)[0] & _CLASS_HOOKS)
            and not any((name, hook) in writes for hook in _CLASS_HOOKS)
        )

    def plain_rhs(value, write):
        if isinstance(value, ast.Name):
            candidates = assignments[value.id]
            if (
                bindings.counts[value.id] != 1
                or len(candidates) != 1
                or candidates[0].lineno >= write.lineno
            ):
                return False
            value = getattr(candidates[0], "value", None)
        return (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id in classes
            and plain_class(value.func.id)
            and not value.args
            and not value.keywords
            and classes[value.func.id].lineno < write.lineno
        )

    def enclosing(node, kinds):
        while node in parents:
            node = parents[node]
            if isinstance(node, kinds):
                return node
        return None

    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def returned_types(function, seeds=None, active=()):
        if function.name in active:
            return set(), True
        local_values = defaultdict(list)
        unknown_writes = set()
        returns = []
        pending = list(function.body)
        while pending:
            node = pending.pop()
            if isinstance(node, ast.Return):
                returns.append(node.value)
            elif not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
            ):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            local_values[target.id].append(node.value)
                elif (
                    isinstance(node, (ast.AnnAssign, ast.NamedExpr))
                    and isinstance(node.target, ast.Name)
                    and node.value is not None
                ):
                    local_values[node.target.id].append(node.value)
                elif isinstance(node, ast.Name) and isinstance(
                    node.ctx, (ast.Store, ast.Del)
                ):
                    parent = parents.get(node)
                    if not isinstance(
                        parent, (ast.Assign, ast.AnnAssign, ast.NamedExpr)
                    ):
                        unknown_writes.add(node.id)
                elif isinstance(node, ast.ExceptHandler) and node.name:
                    unknown_writes.add(node.name)
                elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
                    unknown_writes.add(node.name)
                elif isinstance(node, ast.MatchMapping) and node.rest:
                    unknown_writes.add(node.rest)
                pending.extend(ast.iter_child_nodes(node))

        def facts(value, seen=()):
            if value is None or isinstance(value, ast.Constant):
                return set(), False
            if isinstance(value, ast.Name):
                if value.id in seen:
                    return set(), True
                if value.id in local_values or value.id in unknown_writes:
                    results = [
                        facts(expr, (*seen, value.id))
                        for expr in local_values[value.id]
                    ]
                    if seeds and value.id in seeds:
                        results.append(seeds[value.id])
                    if value.id in unknown_writes:
                        results.append((set(), True))
                    return set().union(*(names for names, _ in results)), any(
                        unknown for _, unknown in results
                    )
                if seeds and value.id in seeds:
                    return seeds[value.id]
                names = types(value)
                return names, not names
            if isinstance(value, ast.Call):
                if isinstance(value.func, ast.Name):
                    name = value.func.id
                    if name in classes:
                        return types(value), False
                    if name in functions and bindings.counts[name] == 1:
                        callee = functions[name]
                        positional = callee.args.posonlyargs + callee.args.args
                        args = positional + callee.args.kwonlyargs
                        supplied = {
                            arg.arg: facts(expr, seen)
                            for arg, expr in zip(positional, value.args)
                        }
                        for keyword in value.keywords:
                            if keyword.arg:
                                supplied[keyword.arg] = facts(keyword.value, seen)
                        for arg in args:
                            supplied.setdefault(arg.arg, (set(), True))
                        return returned_types(
                            callee, supplied, (*active, function.name)
                        )
                if isinstance(value.func, ast.Attribute) and value.func.attr in {
                    "__getattribute__",
                    "__new__",
                }:
                    primary = value.func.value
                    if (
                        isinstance(primary, ast.Call)
                        and isinstance(primary.func, ast.Name)
                        and primary.func.id == "super"
                        and not bindings.counts["super"]
                    ):
                        return set(), False
                    if (
                        isinstance(primary, ast.Name)
                        and primary.id == "object"
                        and not bindings.counts["object"]
                    ):
                        return set(), False
            return set(), True

        results = [facts(value) for value in returns]
        return set().union(*(names for names, _ in results)), any(
            unknown for _, unknown in results
        )

    def receiver_names(value, node):
        if isinstance(value, ast.Name) and value.id in classes:
            result = {value.id}
            result.update(types(value))
            return result
        result = types(value)
        if isinstance(value, ast.Name) and not result:
            function = enclosing(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            cls = enclosing(node, (ast.ClassDef,))
            if function is not None and cls is not None and function.args.args:
                if value.id == function.args.args[0].arg:
                    return {cls.name}
        return result

    # Only augment an existing direct class-write plan; do not add alias support.
    for target, event in alias_writes:
        for owner in types(target.value):
            key = (owner, target.attr)
            if key in writes:
                writes[key].append(event)

    def hook_functions(cls, hook):
        def resolve(value, seen=()):
            if not isinstance(value, ast.Name) or value.id in seen:
                return [None]
            if value.id in functions and bindings.counts[value.id] == 1:
                return [functions[value.id]]
            if bindings.counts[value.id] == 1 and len(assignments[value.id]) == 1:
                return resolve(
                    getattr(assignments[value.id][0], "value", None), (*seen, value.id)
                )
            return [None]

        result = []
        for node in _scope_nodes(cls.body):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == hook
            ):
                result.append(node)
            elif isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == hook
                for target in node.targets
            ):
                result.extend(resolve(node.value))
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == hook
            ):
                result.extend(resolve(node.value))
            elif isinstance(node, (ast.Import, ast.ImportFrom)) and any(
                (item.asname or item.name) == hook for item in node.names
            ):
                result.append(None)
        for event in writes.get((cls.name, hook), ()):
            result.extend(resolve(getattr(event, "value", None)))
        if not result and hook in _class_bindings(cls)[0]:
            result.append(None)
        return result

    result = {}
    for (owner, attribute), events in writes.items():
        value_types = set().union(
            *(types(getattr(event, "value", None)) for event in events)
        )
        if not value_types:
            continue
        # Functions and custom data descriptors retain their existing boundary.
        if any(
            _class_bindings(classes[name])[0] & {"__get__", "__set__", "__delete__"}
            for name in value_types
        ):
            continue
        possible_owners = {owner}
        for assignment in assignments[owner]:
            aliases = types(getattr(assignment, "value", None))
            possible_owners.update(aliases or set(classes))
        for decorator in classes[owner].decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id in functions:
                returned, unknown = returned_types(functions[decorator.id])
                possible_owners.update(set(classes) if unknown else returned)
        reasons = []
        event = events[0]
        if len(events) != 1:
            reasons.append("multiple writes")
        if not (
            isinstance(event, ast.Assign)
            and len(event.targets) == 1
            and parents.get(event) is tree
        ):
            reasons.append("conditional or unsupported write")
        if not plain_class(owner) or classes[owner].lineno >= event.lineno:
            reasons.append("class identity or behavior")
        if bindings.wildcard_import:
            reasons.append("wildcard import identity")
        if any(
            any(
                isinstance(base, ast.Name) and owner in (types(base) or {base.id})
                for base in node.bases
            )
            for node in classes.values()
        ):
            reasons.append("inheritance")
        if not plain_rhs(getattr(event, "value", None), event):
            reasons.append("data value identity")
        for owner_name in possible_owners:
            cls = classes[owner_name]
            if attribute in _class_bindings(cls)[1]:
                reasons.append("existing non-assignment binding")
            for child in cls.body:
                if isinstance(child, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == attribute
                    for target in child.targets
                ):
                    value_types.update(types(child.value))
            for node in _scope_nodes(cls.body):
                if (
                    isinstance(node, ast.Name)
                    and isinstance(node.ctx, ast.Load)
                    and node.id == attribute
                ):
                    reasons.append("early class namespace reader")
            for node in ast.walk(cls):
                if (
                    isinstance(node, ast.Attribute)
                    and node.attr == attribute
                    and isinstance(node.ctx, ast.Store)
                ):
                    reasons.append("instance write")
                    assignment = parents.get(node)
                    value_types.update(types(getattr(assignment, "value", None)))
        for node in ast.walk(tree):
            if (
                not isinstance(node, ast.Attribute)
                or node.attr != attribute
                or not isinstance(node.ctx, ast.Load)
            ):
                continue
            receivers = receiver_names(node.value, node)
            if receivers and not (receivers & possible_owners):
                continue
            if not receivers:
                reasons.append("unknown reader")
            if (
                enclosing(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
                is not None
            ):
                reasons.append("deferred reader")
            elif node.lineno <= event.lineno:
                reasons.append("early reader")
        # Lookup/constructor rewrites can return another local data class.
        # They stay unknown; include explicit returns in the mutation guard.
        pending_types = list(possible_owners | value_types)
        seen_types = set()
        while pending_types:
            class_name = pending_types.pop()
            if class_name in seen_types:
                continue
            seen_types.add(class_name)
            cls = classes[class_name]
            rewrite_classes = [cls]
            for keyword in cls.keywords:
                if (
                    keyword.arg == "metaclass"
                    and isinstance(keyword.value, ast.Name)
                    and keyword.value.id in classes
                ):
                    rewrite_classes.append(classes[keyword.value.id])
            for rewrite in rewrite_classes:
                for hook in _VALUE_HOOKS:
                    for function in hook_functions(rewrite, hook):
                        if function is None:
                            added = set(classes)
                        else:
                            seeds = {}
                            parameters = function.args.posonlyargs + function.args.args
                            if parameters:
                                seeds[parameters[0].arg] = ({class_name}, False)
                            returned, unknown = returned_types(function, seeds)
                            added = set(classes) if unknown else returned
                        value_types.update(added)
                        pending_types.extend(added - seen_types)
        for owner_name in possible_owners:
            result[owner_name, attribute] = {
                "event": event,
                "allowed": not reasons,
                "reasons": tuple(sorted(set(reasons))),
                "affected_types": frozenset(value_types),
                "unaliased_import": any(
                    isinstance(node, (ast.Import, ast.ImportFrom))
                    and any(
                        alias.asname is None
                        and (
                            alias.name.split(".")[0]
                            if isinstance(node, ast.Import)
                            else alias.name
                        )
                        == attribute
                        for alias in node.names
                    )
                    for node in _scope_nodes(classes[owner_name].body)
                ),
            }
    return result


def add_class_data(pyclass, attributes):
    module = pyclass.get_module()
    if pyclass.parent is not module:
        return attributes
    for (owner, name), plan in _plans(module).items():
        if owner != pyclass.get_name():
            continue
        original = attributes.get(name)
        if plan["allowed"] and isinstance(
            original, (pynames.ImportedName, pynames.ImportedModule)
        ):
            original = pynamesdef.AssignedName(plan["event"].lineno, module)
        if original is None:
            original = pynamesdef.AssignedName(plan["event"].lineno, module)
        if plan["allowed"] and isinstance(original, pynamesdef.AssignedName):
            original.assignments.append(pynamesdef.AssignmentValue(plan["event"].value))
            original.invalidate()
            attributes[name] = original
        else:
            if plan["allowed"]:
                plan["allowed"] = False
                plan["reasons"] = (*plan["reasons"], "unsupported existing PyName")
            originals = plan.setdefault("original_values", [])
            if original not in originals:
                originals.append(original)
            attributes[name] = _UncertainDataName(original)
    return attributes


def check_rename(module, name, pyname, primary):
    modules = [module]
    defining, _ = pyname.get_definition_location()
    if defining is not None and defining not in modules:
        modules.append(defining)
    if primary is not None:
        obj = primary.get_object()
        cls = obj if isinstance(obj, pyobjects.AbstractClass) else obj.get_type()
        if isinstance(cls, pyobjects.PyDefinedObject):
            owning = cls.get_module()
            if owning not in modules:
                modules.append(owning)
    for current in modules:
        _check_module_rename(current, name, pyname)


def _check_module_rename(module, name, pyname):
    plans = _plans(module)
    classes = [
        cls
        for cls in module._get_defined_objects() or ()
        if isinstance(cls, pyobjects.AbstractClass) and cls.parent is module
    ]
    planned_owners = {owner for owner, _ in plans}
    # Resolve unsupported existing PyNames before deciding the cold guard.
    for cls in classes:
        if cls.get_name() in planned_owners:
            cls._get_structural_attributes()
    for cls in classes:
        plan = plans.get((cls.get_name(), name))
        if (
            plan is not None
            and plan.get("unaliased_import")
            and cls.get_attributes().get(name) is pyname
        ):
            raise exceptions.RefactoringError(
                "Cannot rename this import-backed class attribute without an explicit import alias."
            )
    blocked = {key: plan for key, plan in plans.items() if not plan["allowed"]}
    if not blocked:
        return
    affected = set().union(*(plan["affected_types"] for plan in blocked.values()))
    for cls in classes:
        if (
            cls.get_name() in affected or (cls.get_name(), name) in blocked
        ) and cls.get_attributes().get(name) is pyname:
            raise exceptions.RefactoringError(
                "Cannot rename this field while external class data has uncertain identity or execution order."
            )
    for plan in blocked.values():
        for container in _original_value_containers(plan):
            if container.get_attributes().get(name) is pyname:
                raise exceptions.RefactoringError(
                    "Cannot rename this field while the original class data value has uncertain uses."
                )


def _original_value_containers(plan):
    # Keep PyNames: each guard observes the current imported module cache.
    seen_modules = set()
    seen_classes = set()

    def local_source_module(module, project, root):
        if (
            not isinstance(module, pyobjects.AbstractModule)
            or not isinstance(module, pyobjects.PyDefinedObject)
            or root is None
        ):
            return False
        resource = module.get_resource()
        return (
            resource is not None
            and resource.project is project
            and (resource == root or root.contains(resource))
            and resource.pathlib.resolve().is_relative_to(root.pathlib.resolve())
        )

    for original in plan.get("original_values", ()):
        obj = original.get_object()
        if obj is pyobjects.get_unknown():
            continue
        container = (
            obj
            if isinstance(obj, (pyobjects.AbstractClass, pyobjects.AbstractModule))
            else obj.get_type()
        )
        resource = (
            container.get_module().get_resource()
            if isinstance(
                container, (pyobjects.AbstractModule, pyobjects.AbstractClass)
            )
            and isinstance(container, pyobjects.PyDefinedObject)
            else None
        )
        project = resource.project if resource is not None else None
        root = getattr(project, "root", None)
        pending = [container]
        while pending:
            current = pending.pop()
            if isinstance(current, pyobjects.AbstractClass):
                if id(current) in seen_classes:
                    continue
                seen_classes.add(id(current))
                yield current
                if isinstance(
                    current, pyobjects.PyDefinedObject
                ) and local_source_module(current.get_module(), project, root):
                    for defined in current._get_defined_objects() or ():
                        if (
                            isinstance(defined, pyobjects.AbstractClass)
                            and defined.parent is current
                        ):
                            pending.append(defined)
                continue
            if not isinstance(current, pyobjects.AbstractModule):
                continue
            if id(current) in seen_modules:
                continue
            seen_modules.add(id(current))
            yield current
            if not isinstance(current, pyobjects.PyDefinedObject):
                continue
            # Preserve the original direct-class guard for dynamic module access.
            for defined in current._get_defined_objects() or ():
                if (
                    isinstance(defined, pyobjects.AbstractClass)
                    and defined.parent is current
                ):
                    pending.append(defined)
            if not local_source_module(current, project, root):
                continue
            # Follow existing inferred exports, never arbitrary class attributes.
            for exported in current.get_attributes().values():
                value = exported.get_object()
                if value is pyobjects.get_unknown():
                    continue
                if isinstance(exported, pynames.ImportedName) and isinstance(
                    value, pyobjects.AbstractFunction
                ):
                    defining, _ = exported.get_definition_location()
                    if local_source_module(defining, project, root):
                        pending.append(defining)
                candidate = (
                    value
                    if isinstance(
                        value, (pyobjects.AbstractClass, pyobjects.AbstractModule)
                    )
                    else value.get_type()
                )
                if isinstance(candidate, pyobjects.AbstractClass):
                    pending.append(candidate)
                elif local_source_module(candidate, project, root):
                    pending.append(candidate)


def import_source_name(
    scope,
    lineno,
    offset,
    word,
    primary,
    from_module,
    from_aliased,
    from_is_module,
):
    """Preserve import source identity only for class bindings touched by this layer."""
    if (
        scope.get_kind() != "Class"
        or not isinstance(scope.pyobject, pyobjects.PyDefinedObject)
        or scope.pyobject.parent is not scope.pyobject.get_module()
    ):
        return None
    module = scope.pyobject.get_module()
    plans = _plans(module)
    owner = scope.pyobject.get_name()
    for node in _scope_nodes(scope.pyobject.get_ast().body):
        if (
            not isinstance(node, (ast.Import, ast.ImportFrom))
            or not node.lineno <= lineno <= node.end_lineno
        ):
            continue
        for alias in node.names:
            local = alias.asname or (
                alias.name.split(".")[0] if isinstance(node, ast.Import) else alias.name
            )
            if (owner, local) not in plans:
                continue
            if isinstance(node, ast.ImportFrom):
                origin = "." * node.level + (node.module or "")
                if from_module != origin:
                    continue
                imported = pynamesdef.ImportedModule(
                    module, node.module or "", node.level
                )
                if from_is_module:
                    level = len(primary) - len(primary.lstrip("."))
                    return pynamesdef.ImportedModule(module, primary.lstrip("."), level)
                if alias.name == word and (alias.asname is None or from_aliased):
                    return pynamesdef.ImportedName(imported, alias.name)
            elif alias.name == primary or alias.name.startswith(primary + "."):
                start, end = codeanalyze.ASTLinesAdapter(module.source_code)[alias]
                if start is None or end is None:
                    continue
                origin_end = end
                if alias.asname is not None:
                    segment = module.source_code[start:end]
                    for token in tokenize.generate_tokens(
                        io.StringIO(segment).readline
                    ):
                        if token.type == tokenize.NAME and token.string == "as":
                            lines = segment.split("\n")
                            origin_end = (
                                start
                                + sum(
                                    len(line) + 1
                                    for line in lines[: token.start[0] - 1]
                                )
                                + token.start[1]
                            )
                            break
                if start <= offset < origin_end:
                    return pynamesdef.ImportedModule(module, primary)
    return None
