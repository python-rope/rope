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
    for target in ast.walk(module.get_ast()):
        if (
            isinstance(target, ast.Attribute)
            and target.attr == attribute
            and isinstance(target.ctx, (ast.Store, ast.Del))
        ):
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
