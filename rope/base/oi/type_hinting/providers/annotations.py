"""Resolve declared function annotations through the native hint resolver."""

from rope.base import ast, builtins, evaluate, pyobjects
from rope.base.oi.type_hinting import utils
from rope.base.oi.type_hinting.providers import interfaces


def _resolve_node(node, owner, resolver, late_owner):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            try:
                expression = ast.parse(node.value, mode="eval").body
            except SyntaxError:
                return None
            return _resolve_node(expression, late_owner, resolver, late_owner)
        if node.value is None:
            return builtins._runtime_class(type(None))
        return None
    if isinstance(node, (ast.Name, ast.Attribute)):
        return resolver(ast.unparse(node), owner)
    if isinstance(node, ast.Subscript):
        origin = _resolve_node(node.value, owner, resolver, late_owner)
        if origin is None:
            return None
        arguments = (
            node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
        )
        if utils.is_annotated_type(origin):
            if len(arguments) < 2:
                return None
            return _resolve_node(arguments[0], owner, resolver, late_owner)
        if isinstance(origin, pyobjects.PyClass):
            binding = evaluate.eval_node(utils.get_hint_scope(owner), node)
            value = binding.get_object() if binding is not None else None
            return value if isinstance(value, pyobjects.AbstractClass) else None
        return utils.parametrize_type(
            origin,
            *(
                _resolve_node(argument, owner, resolver, late_owner)
                for argument in arguments
            ),
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        alternatives = tuple(
            _resolve_node(part, owner, resolver, late_owner)
            for part in (node.left, node.right)
        )
        return utils.union_type(alternatives)
    return None


def _resolve_annotation(annotation, function, resolver):
    if annotation is None:
        return None
    module = function.get_module()
    context = module.get_source_binding_index().context_for_node(annotation)
    owner = context.environment.pyobject if context is not None else function
    try:
        resolved = _resolve_node(annotation, owner, resolver, module)
    except (TypeError, RecursionError):
        resolved = None
    if not isinstance(resolved, pyobjects.AbstractClass):
        return pyobjects.get_unknown()
    return resolved


class ParamProvider(interfaces.IParamProvider):
    def __init__(self, resolver):
        self._resolve = resolver

    def __call__(self, function, name):
        args = function.get_ast().args
        for argument in (*args.posonlyargs, *args.args, *args.kwonlyargs):
            if argument.arg == name:
                return _resolve_annotation(argument.annotation, function, self._resolve)


class ReturnProvider(interfaces.IReturnProvider):
    def __init__(self, resolver):
        self._resolve = resolver

    def __call__(self, function):
        return _resolve_annotation(function.get_ast().returns, function, self._resolve)
