"""Inspect native ancestry against explicit source roots without importing targets."""

import argparse
import json
from pathlib import Path

from rope.base import ast, evaluate, pynames, pynamesdef, pyobjects, pyscopes
from rope.base.project import Project


def describe(value):
    """Describe existing native identities without resolving another binding.

    Object and type ids are process-local witnesses. Type module and resource
    metadata is included only when the native object exposes that origin;
    unresolved kinds do not acquire an assumed name or declaring module.
    Getter failures propagate instead of substituting a different object.
    """
    if value is None:
        return None
    result = {
        "native_type": type(value).__qualname__,
        "native_id": hex(id(value)),
    }
    if isinstance(value, (pyobjects.AbstractClass, pyobjects.PyFunction)):
        result["name"] = value.get_name()
        module = value.get_module()
        if module is not None:
            result["module"] = module.get_name()
    if isinstance(value, pyobjects.PyObject):
        value_type = value.get_type()
        result["object_type"] = type(value_type).__qualname__
        result["object_type_id"] = hex(id(value_type))
        if isinstance(value_type, pyobjects.AbstractClass):
            result["object_type_name"] = value_type.get_name()
        type_module = value_type.get_module()
        if type_module is not None:
            result["object_type_module"] = type_module.get_name()
            resource = type_module.get_resource()
            if resource is not None:
                result["object_type_resource"] = resource.real_path
        if isinstance(value, pyobjects.AbstractFunction):
            result["name"] = value.get_name()
    return result


def describe_base(owner, base):
    result = describe(base)
    if isinstance(base, pyobjects.UnresolvedBase):
        result["expression"] = ast.unparse(base.node)
        result["inferred"] = describe(base.pyobject)
        base_binding = evaluate.eval_node(owner.parent.get_scope(), base.node)
        if base_binding is not None:
            base_object = base_binding.get_object()
            result["base_binding"] = describe(base_object)
            result["has_mro_entries"] = (
                "__mro_entries__" in base_object.get_attributes()
            )
        if isinstance(base.node, ast.Subscript):
            binding = evaluate.eval_node(owner.parent.get_scope(), base.node.value)
            if binding is not None:
                receiver = binding.get_object()
                result["subscription_receiver"] = describe(receiver)
                hook = receiver.get_attributes().get("__class_getitem__")
                if hook is not None:
                    function = hook.get_object()
                    result["subscription_hook"] = describe(function)
                    module = function.get_module()
                    if module is not None:
                        result["hook_module"] = module.get_name()
                    if isinstance(function, pyobjects.PyFunction):
                        scope = function.get_scope()
                        result["hook_parameters"] = {
                            name: describe(parameter.get_object())
                            for name, parameter in function.get_parameters().items()
                        }
                        result.update(describe_parameter_flow(function))
                        result["hook_bindings"] = {
                            name: {
                                "assignments": [
                                    ast.unparse(assignment.ast_node)
                                    for assignment in binding.assignments
                                ],
                                "inferred": describe(binding.get_object()),
                            }
                            for name, binding in scope.get_names().items()
                            if isinstance(binding, pynames.AssignedName)
                        }
                        result["hook_returns"] = []
                        for expression in scope._get_returned_asts():
                            returned = evaluate.eval_node(scope, expression)
                            result["hook_returns"].append(
                                {
                                    "expression": ast.unparse(expression),
                                    "inferred": describe(
                                        returned.get_object()
                                        if returned is not None
                                        else None
                                    ),
                                }
                            )
                        result["assigned_call_frames"] = []
                        for binding in scope.get_names().values():
                            if not isinstance(binding, pynames.AssignedName):
                                continue
                            for assignment in binding.assignments:
                                expression = assignment.ast_node
                                if not isinstance(expression, ast.Call):
                                    continue
                                called = evaluate.eval_node(scope, expression.func)
                                if called is None:
                                    continue
                                callable_object = called.get_object()
                                if isinstance(callable_object, pyobjects.PyFunction):
                                    result["assigned_call_frames"].append(
                                        describe_frame(callable_object)
                                    )
    return result


def describe_frame(function, preassignment_names=()):
    """Report a native function frame and its elected module resource, or None."""
    module = function.get_module()
    scope = function.get_scope()
    resource = module.get_resource()
    result = {
        "name": function.get_name(),
        "module": module.get_name(),
        "resource": resource.real_path if resource is not None else None,
        "parameters": {
            name: describe(parameter.get_object())
            for name, parameter in function.get_parameters().items()
        },
        "locals": {
            name: {
                "assignments": [
                    ast.unparse(assignment.ast_node)
                    for assignment in binding.assignments
                ],
                "inferred": describe(binding.get_object()),
                "assignment_values": [
                    describe_expression(scope, assignment.ast_node)
                    for assignment in binding.assignments
                ],
            }
            for name, binding in scope.get_names().items()
            if isinstance(binding, pynames.AssignedName)
        },
    }
    result["preassignment_witnesses"] = {
        name: describe_preassignment(scope, scope.get_name(name))
        for name in preassignment_names
    }
    return result


def describe_parameter_flow(function):
    module = function.get_module()
    scope = function.get_scope()
    parameters = function.get_parameters()
    result = []
    reads = []
    for context in module.get_source_binding_index().node_contexts.values():
        node = context.source_node
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            if (
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id in parameters
                and context.structural_scope.pyobject is function
            ):
                reads.append(node)
            continue
        if context.structural_scope.pyobject is not function:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if not isinstance(target, ast.Name) or target.id not in parameters:
                continue
            binder = scope.get_name(target.id)
            result.append(
                {
                    "parameter": target.id,
                    "binder_type": type(binder).__qualname__,
                    "is_formal_binder": binder is parameters[target.id],
                    "formal_value": describe(parameters[target.id].get_object()),
                    "scope_binding_value": describe(binder.get_object()),
                    "assignment": (
                        describe_expression(scope, node.value)
                        if node.value is not None
                        else None
                    ),
                }
            )
    written_names = {write["parameter"] for write in result}
    return {
        "parameter_writes": result,
        "parameter_reads": [
            {
                "line": node.lineno,
                "column": node.col_offset,
                **describe_expression(scope, node),
            }
            for node in reads
            if node.id in written_names
        ],
    }


def describe_preassignment(scope, binding):
    if not isinstance(binding, pynames.AssignedName) or len(binding.assignments) < 2:
        raise TypeError("A preassignment witness requires multiple native assignments")
    original = describe(binding.get_object())
    binding.invalidate()
    invalidated = describe(binding.get_object())
    prefix = pynamesdef.AssignedName(module=binding.module)
    prefix.assignments = binding.assignments[:-1]
    name = next(name for name, value in scope.get_names().items() if value is binding)
    temporary = pyscopes.TemporaryScope(scope.pycore, scope, {name: prefix})
    return {
        "original": original,
        "after_local_invalidation": invalidated,
        "previous_assignments": describe(prefix.get_object()),
        "last_expression_with_previous_binding": describe_expression(
            temporary, binding.assignments[-1].ast_node
        ),
    }


def describe_expression(scope, expression):
    binding = evaluate.eval_node(scope, expression)
    return {
        "expression": ast.unparse(expression),
        "inferred": describe(binding.get_object() if binding is not None else None),
    }


def describe_binding(module, binding):
    """Report a native binding and its elected module resource, or None."""
    result = {"value": describe(binding.get_object())}
    resource = module.get_resource()
    result["resource"] = resource.real_path if resource is not None else None
    if isinstance(binding, pynames.AssignedName):
        scope = module.get_scope()
        result["calls"] = []
        for assignment in binding.assignments:
            expression = assignment.ast_node
            if not isinstance(expression, ast.Call):
                continue
            call = describe_expression(scope, expression)
            call["callable"] = describe_expression(scope, expression.func)
            if isinstance(expression.func, ast.Attribute):
                call["receiver"] = describe_expression(scope, expression.func.value)
            call["arguments"] = [
                describe_expression(scope, argument) for argument in expression.args
            ]
            result["calls"].append(call)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    options = parser.parse_args()
    with options.request.open(encoding="utf-8") as source:
        request = json.load(source)
    project = Project(
        request["root"],
        ropefolder=None,
        python_path=request["python_path"],
        save_history=False,
        save_objectdb=False,
    )
    try:
        for target in request.get("bindings", []):
            module = project.get_module(target["module"])
            holder = module
            for name in target["attributes"][:-1]:
                holder = holder.get_attribute(name).get_object()
            binding = holder.get_attribute(target["attributes"][-1])
            print(
                json.dumps(
                    {"target": target, **describe_binding(module, binding)},
                    ensure_ascii=False,
                    indent=2,
                ),
                flush=True,
            )
        for target in request["targets"]:
            module = project.get_module(target["module"])
            value = module
            for name in target["attributes"]:
                value = value.get_attribute(name).get_object()
            if not isinstance(value, pyobjects.AbstractClass):
                raise TypeError("The requested binding is not a native class")
            resource = module.get_resource()
            result = {
                "target": target,
                "class": describe(value),
                "resource": resource.real_path if resource is not None else None,
                "bases": [describe_base(value, base) for base in value.get_bases()],
                "mro": [describe_base(value, base) for base in value.get_mro()],
            }
            print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        for target in request.get("frames", []):
            function = project.get_module(target["module"])
            for name in target["attributes"]:
                function = function.get_attribute(name).get_object()
            if not isinstance(function, pyobjects.PyFunction):
                raise TypeError("The requested frame is not a native source function")
            print(
                json.dumps(
                    describe_frame(function, target.get("preassignment_names", [])),
                    ensure_ascii=False,
                    indent=2,
                ),
                flush=True,
            )
    finally:
        project.close()


if __name__ == "__main__":
    main()
