from rope.base import pyobjects, builtins, evaluate
from rope.base.oi import dynamicoi, staticoi


class ObjectInfer(object):
    """A class for inferring objects

    For more information see the documentation in `rope.base.oi`
    package.

    """

    def __init__(self, pycore):
        self.soi = staticoi.StaticObjectInference(pycore)
        self.doi = dynamicoi.DynamicObjectInference(pycore)
        self.call_info = pycore.call_info
        self.ois = [self.soi, self.doi]

    def infer_returned_object(self, pyobject, args):
        """Infer the `PyObject` this callable `PyObject` returns after calling"""
        result = self.call_info.get_exact_returned(pyobject, args)
        if result is not None:
            return result
        result = self.soi.infer_returned_object(pyobject, args)
        if result is not None:
            if args and pyobject.get_module().get_resource() is not None:
                params = args.get_arguments(
                    pyobject.get_param_names(special_args=False))
                self.call_info.function_called(pyobject, params, result)
            return result
        return self.call_info.get_returned(pyobject, args)

    def infer_parameter_objects(self, pyobject):
        """Infer the `PyObject`\s of parameters of this callable `PyObject`"""
        for oi in reversed(self.ois):
            result = oi.infer_parameter_objects(pyobject)
            if result is not None:
                return result

    def infer_assigned_object(self, pyname):
        if not pyname.assignments:
            return
        for assignment in reversed(pyname.assignments):
            result = self._infer_assignment(assignment, pyname.module)
            if result is not None:
                return result

    def _infer_assignment(self, assignment, pymodule):
        try:
            pyobject = self._infer_pyobject_for_assign_node(
                assignment.ast_node, pymodule)
            if pyobject is None:
                return None
            return self._infer_assignment_object(assignment, pyobject)
        except pyobjects.IsBeingInferredError:
            pass

    def _infer_assignment_object(self, assignment, pyobject):
        for index in assignment.levels:
            if isinstance(pyobject.get_type(), builtins.Tuple):
                holdings = pyobject.get_type().get_holding_objects()
                pyobject = holdings[min(len(holdings) - 1, index)]
            elif isinstance(pyobject.get_type(), builtins.List):
                pyobject = pyobject.get_type().holding
            else:
                pyobject = None
            if pyobject is None:
                break
        return pyobject

    def _infer_pyobject_for_assign_node(self, assign_node, pymodule, lineno=None):
        try:
            if lineno is None and hasattr(assign_node, 'lineno') and \
               assign_node.lineno is not None:
                lineno = assign_node.lineno
            if lineno is None:
                lineno = 1
            holding_scope = pymodule.get_scope().get_inner_scope_for_line(lineno)
            pyname = evaluate.get_statement_result(holding_scope, assign_node)
            if pyname is not None:
                result = pyname.get_object()
                if isinstance(result.get_type(), builtins.Property) and \
                   holding_scope.get_kind() == 'Class':
                    return result.get_type().get_property_object()
                return result
        except pyobjects.IsBeingInferredError:
            pass

    def evaluate_object(self, evaluated):
        pyobject = self._infer_pyobject_for_assign_node(
            evaluated.assignment.ast_node, evaluated.module, evaluated.lineno)
        pyname = evaluated
        tokens = evaluated.evaluation.split('.')
        for token in tokens:
            call = token.endswith('()')
            if call:
                token = token[:-2]
            if token:
                pyname2 = self._get_attribute(pyobject, token)
                if pyname2 is not None:
                    pyobject = pyname2.get_object()
            if pyobject is not None and call:
                args = evaluate.ObjectArguments(pyname, [])
                pyobject = pyobject.get_returned_object(args)
                pyname = None
            if pyobject is None:
                break
        if evaluated is None:
            return pyobject
        return self._infer_assignment_object(evaluated.assignment, pyobject)

    def _get_attribute(self, pyobject, name):
        if pyobject is not None and name in pyobject.get_attributes():
            return pyobject.get_attribute(name)
