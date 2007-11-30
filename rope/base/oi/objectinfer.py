from rope.base import evaluate, pyobjects, builtins, pynames
from rope.base.oi import staticoi


_ignore_inferred = staticoi._ignore_inferred

class ObjectInfer(object):
    """A class for inferring objects

    For more information see the documentation in `rope.base.oi`
    package.

    """

    def __init__(self, pycore):
        self.object_info = pycore.object_info

    def infer_returned_object(self, pyfunction, args):
        """Infer the `PyObject` this `PyFunction` returns after calling"""
        result = self.object_info.get_exact_returned(pyfunction, args)
        if result is not None:
            return result
        result = _infer_returned(pyfunction, args)
        if result is not None:
            if args and pyfunction.get_module().get_resource() is not None:
                params = args.get_arguments(
                    pyfunction.get_param_names(special_args=False))
                self.object_info.function_called(pyfunction, params, result)
            return result
        return self.object_info.get_returned(pyfunction, args)

    def infer_parameter_objects(self, pyfunction):
        """Infer the `PyObject`\s of parameters of this `PyFunction`"""
        result = self.object_info.get_parameter_objects(pyfunction)
        if result is None:
            result = _parameter_objects(pyfunction)
        self._handle_first_parameter(pyfunction, result)
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
            statically_inferred = _parameter_objects(pyfunction)
            if len(statically_inferred) > parameter_index:
                result.append(statically_inferred[parameter_index])
        return result

    @_ignore_inferred
    def _infer_assignment(self, assignment, pymodule):
        pyobject = self._infer_pyobject_for_assign_node(
            assignment.ast_node, pymodule)
        if pyobject is None:
            return None
        return self._infer_assignment_object(assignment, pyobject)

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

    @_ignore_inferred
    def _infer_pyobject_for_assign_node(self, assign_node, pymodule, lineno=None):
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

    @_ignore_inferred
    def _infer_pyname_for_assign_node(self, assign_node, pymodule, lineno=None):
        if lineno is None:
            lineno = self._get_lineno_for_node(assign_node)
        holding_scope = pymodule.get_scope().get_inner_scope_for_line(lineno)
        return evaluate.get_statement_result(holding_scope, assign_node)

    def _get_lineno_for_node(self, assign_node):
        if hasattr(assign_node, 'lineno') and \
           assign_node.lineno is not None:
            return assign_node.lineno
        return 1

    @_ignore_inferred
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


def _infer_returned(pyobject, args):
    if args:
        # HACK: Setting parameter objects manually
        # This is not thread safe and might cause problems if `args`
        # does not come from a good call site
        pyobject.get_scope().invalidate_data()
        pyobject._set_parameter_pyobjects(
            args.get_arguments(pyobject.get_param_names(special_args=False)))
    scope = pyobject.get_scope()
    if not scope._get_returned_asts():
        return
    for returned_node in reversed(scope._get_returned_asts()):
        try:
            resulting_pyname = evaluate.get_statement_result(scope,
                                                             returned_node)
            if resulting_pyname is None:
                return
            pyobject = resulting_pyname.get_object()
            if pyobject == pyobjects.get_unknown():
                return
            if not scope._is_generator():
                return pyobject
            else:
                return builtins.get_generator(pyobject)
        except pyobjects.IsBeingInferredError:
            pass

def _parameter_objects(pyobject):
    params = pyobject.get_param_names(special_args=False)
    return [pyobjects.get_unknown()] * len(params)
