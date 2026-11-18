"""Bound access values for ordinary functions stored in a class body."""

from rope.base import arguments, ast, pynames, pyobjects


class BoundFunction(pyobjects.AbstractFunction):
    def __init__(self, function, receiver):
        super().__init__()
        self.function = function
        self.receiver = receiver

    def get_name(self):
        return self.function.get_name()

    def get_doc(self):
        return self.function.get_doc()

    def get_param_names(self, special_args=True):
        return self.function.get_param_names(special_args)

    def bind_arguments(self, args):
        return arguments.MixedArguments(self.receiver, args, None)

    def get_returned_object(self, args):
        return self.function.get_returned_object(self.bind_arguments(args))


class BoundAccessName(pynames.PyName):
    def __init__(self, canonical, function, receiver):
        self.canonical = canonical
        self.value = BoundFunction(function, receiver)

    def get_object(self):
        return self.value

    def get_definition_location(self):
        return self.canonical.get_definition_location()

    def __eq__(self, other):
        if isinstance(other, BoundAccessName):
            other = other.canonical
        return self.canonical == other

    def __hash__(self):
        return hash(self.canonical)


def canonical_function(value):
    if isinstance(value, BoundFunction):
        return value.function
    return value


def instance_access(primary, attribute, pyname, access_scope):
    if not isinstance(pyname, pynames.AssignedName):
        return pyname
    instance = primary.get_object()
    if isinstance(instance, pyobjects.AbstractClass):
        return pyname
    owner = instance.get_type()
    if not isinstance(owner, pyobjects.PyClass):
        return pyname
    function = pyname.get_object()
    if not isinstance(function, pyobjects.PyFunction):
        return pyname
    if not isinstance(function.parent, pyobjects.PyModule):
        return pyname
    node = function.get_ast()
    if (
        not node.args.args
        or node.args.posonlyargs
        or node.args.kwonlyargs
        or node.decorator_list
        or getattr(node, "type_params", ())
    ):
        return pyname
    assignments = pyname.assignments
    if len(assignments) != 1 or not isinstance(assignments[0].ast_node, ast.Name):
        return pyname
    assignment = assignments[0]
    if assignment.levels or assignment.evaluation or assignment.assign_type:
        return pyname
    module, _ = pyname.get_definition_location()
    if module is None:
        return pyname
    storage_scope = module.get_scope().get_inner_scope_for_line(assignment.get_lineno())
    if storage_scope.get_kind() != "Class":
        return pyname
    storage = storage_scope.pyobject
    storage_node = storage.get_ast()
    if storage_node.decorator_list or storage_node.keywords:
        return pyname
    if not any(
        isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Name)
        and statement.targets[0].id == attribute
        and statement.value is assignment.ast_node
        for statement in storage_node.body
    ):
        return pyname
    modules = (module, owner.get_module(), access_scope.pyobject.get_module())
    for current in dict.fromkeys(modules):
        if _has_override(current, primary, owner, storage, attribute):
            return pyname
    return BoundAccessName(pyname, function, primary)


def _has_override(module, primary, owner, storage, attribute):
    # Instance dictionary functions remain ordinary unbound function values.
    from rope.base import evaluate

    receiver = primary.get_object()
    for target in module._get_source_binding_index().attribute_writes(attribute):
        if not isinstance(target.value, ast.Name):
            return True
        scope = module.get_scope().get_inner_scope_for_line(target.lineno)
        target_name = evaluate.eval_node(scope, target.value)
        if target_name == primary:
            return True
        if target_name is not None:
            target_object = target_name.get_object()
            if (
                target_object is receiver
                or target_object is owner
                or target_object is storage
            ):
                return True
    return False


def descriptor_access(primary, attribute, pyname, access_scope):
    """Resolve a source descriptor that returns its unchanged constructor value."""
    if not isinstance(pyname, pynames.AssignedName) or len(pyname.assignments) != 1:
        return pyname
    receiver = primary.get_object()
    owner = (
        receiver
        if isinstance(receiver, pyobjects.AbstractClass)
        else receiver.get_type()
    )
    if not isinstance(owner, pyobjects.PyClass):
        return pyname
    assignment = pyname.assignments[0]
    call = assignment.ast_node
    if (
        not isinstance(call, ast.Call)
        or assignment.levels
        or assignment.evaluation
        or assignment.assign_type
    ):
        return pyname
    module, _ = pyname.get_definition_location()
    if module is None:
        return pyname
    scope = module.get_scope().get_inner_scope_for_line(assignment.get_lineno())
    if scope.get_kind() != "Class" or scope.pyobject not in owner.get_mro():
        return pyname
    from rope.base import evaluate

    constructor = evaluate.eval_node(scope, call.func)
    if constructor is None or not isinstance(
        constructor.get_object(), pyobjects.PyClass
    ):
        return pyname
    descriptor = constructor.get_object()
    declaration = descriptor.get_ast()
    statements = declaration.body
    if (
        statements
        and isinstance(statements[0], ast.Expr)
        and isinstance(statements[0].value, ast.Constant)
        and isinstance(statements[0].value.value, str)
    ):
        statements = statements[1:]
    # Any other class-body statement could rebind __init__ or __get__.
    methods = {
        node.name: node for node in statements if isinstance(node, ast.FunctionDef)
    }
    if (
        declaration.bases
        or declaration.keywords
        or declaration.decorator_list
        or len(statements) != 2
        or set(methods) != {"__init__", "__get__"}
    ):
        return pyname
    initializer, getter = methods["__init__"], methods["__get__"]
    if initializer.decorator_list or getter.decorator_list:
        return pyname
    bodies = []
    for method in (initializer, getter):
        body = method.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body = body[1:]
        bodies.append(body)
    if len(bodies[0]) != 1 or len(bodies[1]) != 1:
        return pyname
    store, returned = bodies[0][0], bodies[1][0]
    positional = (*initializer.args.posonlyargs, *initializer.args.args)
    get_positional = (*getter.args.posonlyargs, *getter.args.args)
    if len(positional) != 2 or len(get_positional) != 3:
        return pyname
    if (
        not isinstance(store, ast.Assign)
        or len(store.targets) != 1
        or not isinstance(store.value, ast.Name)
    ):
        return pyname
    target = store.targets[0]
    if (
        not isinstance(target, ast.Attribute)
        or not isinstance(target.value, ast.Name)
        or target.value.id != positional[0].arg
        or store.value.id != positional[1].arg
    ):
        return pyname
    if (
        not isinstance(returned, ast.Return)
        or not isinstance(returned.value, ast.Attribute)
        or not isinstance(returned.value.value, ast.Name)
        or returned.value.value.id != get_positional[0].arg
        or returned.value.attr != target.attr
    ):
        return pyname
    if any(
        _has_override(current, primary, owner, scope.pyobject, attribute)
        for current in dict.fromkeys(
            (module, owner.get_module(), access_scope.pyobject.get_module())
        )
    ):
        return pyname
    function = descriptor["__init__"].get_object()
    supplied = arguments.create_arguments(
        None, function, call, scope, ignore_instance=True
    )
    supplied = arguments.MixedArguments(
        pynames.UnboundName(pyname.get_object()), supplied, scope
    )
    value = supplied.get_pynames(function.get_param_names())[1]
    return value if value is not None else pyname
