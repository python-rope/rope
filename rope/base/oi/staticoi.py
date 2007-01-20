import compiler.ast

from rope.base import pyobjects
from rope.base import pynames
from rope.base import builtins
from rope.base import evaluate


class StaticObjectInference(object):

    def __init__(self):
        pass

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
        except pyobjects.IsBeingInferredException:
            pass

    def _infer_assignment_object(self, assignment, pyobject):
        if assignment.index is not None and isinstance(pyobject.get_type(),
                                                       builtins.Tuple):
            holdings = pyobject.get_type().get_holding_objects()
            return holdings[min(len(holdings) - 1, assignment.index)]
        if assignment.index is not None and isinstance(pyobject.get_type(),
                                                       builtins.List):
            return pyobject.get_type().holding
        return pyobject

    def _infer_pyobject_for_assign_node(self, assign_node, pymodule):
        try:
            lineno = 1
            if hasattr(assign_node, 'lineno') and assign_node.lineno is not None:
                lineno = assign_node.lineno
            holding_scope = pymodule.get_scope().get_inner_scope_for_line(lineno)
            pyname = evaluate.get_statement_result(holding_scope, assign_node)
            if pyname is not None:
                result = pyname.get_object()
                if isinstance(result.get_type(), builtins.Property) and \
                   holding_scope.get_kind() == 'Class':
                    return result.get_type().get_property_object()
                return result
        except pyobjects.IsBeingInferredException:
            pass


    def infer_for_object(self, pyname):
        list_pyobject = self._infer_pyobject_for_assign_node(
            pyname.assignment.ast_node, pyname.module)
        resulting_pyobject = self._call_function(
            self._call_function(list_pyobject, '__iter__'), 'next')
        if resulting_pyobject is None:
            return None
        return self._infer_assignment_object(pyname.assignment,
                                             resulting_pyobject)

    def _call_function(self, pyfunction, function_name):
        if pyfunction is not None and \
           function_name in pyfunction.get_attributes():
            call_function = pyfunction.get_attribute(function_name)
            return call_function.get_object().get_returned_object()

    def infer_returned_object(self, pyobject, args):
        scope = pyobject.get_scope()
        if not scope._get_returned_asts():
            return
        for returned_node in reversed(scope._get_returned_asts()):
            try:
                resulting_pyname = evaluate.get_statement_result(scope,
                                                                 returned_node)
                if resulting_pyname is None:
                    return None
                return resulting_pyname.get_object()
            except pyobjects.IsBeingInferredException:
                pass

    def infer_parameter_objects(self, pyobject):
        objects = []
        if pyobject.parent.get_type() == pyobjects.PyObject.get_base_type('Type'):
            if not pyobject.decorators:
                objects.append(pyobjects.PyObject(pyobject.parent))
            elif self._is_staticmethod_decorator(pyobject.decorators.nodes[0]):
                objects.append(pyobjects.PyObject(
                               pyobjects.PyObject.get_base_type('Unknown')))
            elif self._is_classmethod_decorator(pyobject.decorators.nodes[0]):
                objects.append(pyobject.parent)
            elif pyobject.parameters[0] == 'self':
                objects.append(pyobjects.PyObject(pyobject.parent))
            else:
                objects.append(pyobjects.PyObject(
                               pyobjects.PyObject.get_base_type('Unknown')))
        else:
            objects.append(pyobjects.PyObject(
                           pyobjects.PyObject.get_base_type('Unknown')))
        for parameter in pyobject.parameters[1:]:
            objects.append(pyobjects.PyObject(
                           pyobjects.PyObject.get_base_type('Unknown')))
        return objects

    def _is_staticmethod_decorator(self, node):
        return isinstance(node, compiler.ast.Name) and node.name == 'staticmethod'

    def _is_classmethod_decorator(self, node):
        return isinstance(node, compiler.ast.Name) and node.name == 'classmethod'

