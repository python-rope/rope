from rope.base import evaluate, pyobjects, builtins, pynames
from rope.base.oi import staticoi


class ObjectInfer(object):
    """A class for inferring objects

    For more information see the documentation in `rope.base.oi`
    package.

    """

    def __init__(self, pycore):
        self.soi = staticoi.StaticObjectInference(pycore)
        self.object_info = pycore.object_info

    def infer_returned_object(self, pyobject, args):
        """Infer the `PyObject` this callable `PyObject` returns after calling"""
        result = self.object_info.get_exact_returned(pyobject, args)
        if result is not None:
            return result
        result = self.soi.infer_returned_object(pyobject, args)
        if result is not None:
            if args and pyobject.get_module().get_resource() is not None:
                params = args.get_arguments(
                    pyobject.get_param_names(special_args=False))
                self.object_info.function_called(pyobject, params, result)
            return result
        return self.object_info.get_returned(pyobject, args)

    def infer_parameter_objects(self, pyobject):
        """Infer the `PyObject`\s of parameters of this callable `PyObject`"""
        result = self.object_info.get_parameter_objects(pyobject)
        if result is None:
            result = self.soi.infer_parameter_objects(pyobject)
        self._handle_first_parameter(pyobject, result)
        return result

    def _handle_first_parameter(self, pyobject, parameters):
        kind = pyobject.get_kind()
        if parameters is None or kind not in ['method', 'classmethod']:
            pass
        if not parameters:
            if not pyobject.get_param_names(special_args=False):
                return
            parameters.append(pyobjects.get_unknown())
        if kind == 'method':
            parameters[0] = pyobjects.PyObject(pyobject.parent)
        if kind == 'classmethod':
            parameters[0] = pyobject.parent

    def infer_assigned_object(self, pyname):
        if not pyname.assignments:
            return
        for assignment in reversed(pyname.assignments):
            result = self._infer_assignment(assignment, pyname.module)
            if result is not None:
                return result

    def get_passed_objects(self, pyfunction, parameter_index):
        result = self.object_info.get_passed_objects(pyfunction,
                                                     parameter_index)
        if not result:
            statically_inferred = self.soi.infer_parameter_objects(pyfunction)
            if len(statically_inferred) > parameter_index:
                result.append(statically_inferred[parameter_index])
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
            if lineno is None:
                lineno = self._get_lineno_for_node(assign_node)
            holding_scope = pymodule.get_scope().get_inner_scope_for_line(lineno)
            primary, pyname = evaluate.get_primary_and_result(holding_scope,
                                                              assign_node)
            if pyname is not None:
                result = pyname.get_object()
                if isinstance(result.get_type(), builtins.Property) and \
                   holding_scope.get_kind() == 'Class':
                    arg = pynames.UnboundName(pyobjects.PyObject(
                                              holding_scope.pyobject))
                    return result.get_type().get_property_object(
                        evaluate.ObjectArguments([arg]))
                return result
        except pyobjects.IsBeingInferredError:
            pass

    def _infer_pyname_for_assign_node(self, assign_node, pymodule, lineno=None):
        try:
            if lineno is None:
                lineno = self._get_lineno_for_node(assign_node)
            holding_scope = pymodule.get_scope().get_inner_scope_for_line(lineno)
            return evaluate.get_statement_result(holding_scope, assign_node)
        except pyobjects.IsBeingInferredError:
            pass

    def _get_lineno_for_node(self, assign_node):
        if hasattr(assign_node, 'lineno') and \
           assign_node.lineno is not None:
            return assign_node.lineno
        return 1

    def evaluate_object(self, evaluated):
        pyobject = self._infer_pyobject_for_assign_node(
            evaluated.assignment.ast_node, evaluated.module, evaluated.lineno)
        pyname = self._infer_pyname_for_assign_node(
            evaluated.assignment.ast_node, evaluated.module, evaluated.lineno)
        new_pyname = pyname
        tokens = evaluated.evaluation.split('.')
        for token in tokens:
            call = token.endswith('()')
            if call:
                token = token[:-2]
            if token:
                pyname = new_pyname
                new_pyname = self._get_attribute(pyobject, token)
                if new_pyname is not None:
                    pyobject = new_pyname.get_object()
            if pyobject is not None and call:
                if isinstance(pyobject, pyobjects.AbstractFunction):
                    args = evaluate.ObjectArguments([pyname])
                    pyobject = pyobject.get_returned_object(args)
                else:
                    pyobject = None
            if pyobject is None:
                break
        if evaluated is None or pyobject is None:
            return pyobject
        return self._infer_assignment_object(evaluated.assignment, pyobject)

    def _get_attribute(self, pyobject, name):
        if pyobject is not None and name in pyobject.get_attributes():
            return pyobject.get_attribute(name)
