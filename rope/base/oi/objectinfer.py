from rope.base.pyobjects import *
from rope.base import builtins
import rope.base.codeanalyze
import rope.base.evaluate


class ObjectInfer(object):

    def __init__(self, pycore):
        self.pycore = pycore
    
    def infer_object(self, pyname):
        """Infers the `PyObject` this `PyName` references"""
        if not pyname.assignments:
            return
        for assignment in reversed(pyname.assignments):
            result = self._infer_assignment(assignment, pyname.module)
            if result is not None:
                return result
    
    def _infer_assignment(self, assignment, pymodule):
        try:
            pyname = self._infer_pyname_for_assign_node(
                assignment.ast_node, pymodule)
            if pyname is None:
                return None
            return self._infer_assignment_object(assignment, pyname.get_object())
        except IsBeingInferredException:
            pass

    def _infer_assignment_object(self, assignment, pyobject):
        if assignment.index is not None and isinstance(pyobject, builtins.Tuple):
            holdings = pyobject.get_holding_objects()
            return holdings[min(len(holdings) - 1, assignment.index)]
        if assignment.index is not None and isinstance(pyobject, builtins.List):
            return pyobject.holding
        return pyobject
    
    def _infer_pyname_for_assign_node(self, assign_node, pymodule):
        try:
            lineno = 1
            if hasattr(assign_node, 'lineno') and assign_node.lineno is not None:
                lineno = assign_node.lineno
            holding_scope = pymodule.get_scope().get_inner_scope_for_line(lineno)
            return rope.base.evaluate.StatementEvaluator.\
                   get_statement_result(holding_scope, assign_node)
        except IsBeingInferredException:
            pass
        

    def infer_for_object(self, pyname):
        """Infers the `PyObject` this `PyName` references"""
        list_pyname = self._infer_pyname_for_assign_node(
            pyname.assignment.ast_node, pyname.module)
        resulting_pyname = self._call_function(
            self._call_function(list_pyname, '__iter__'), 'next')
        if resulting_pyname is None:
            return None
        return self._infer_assignment_object(pyname.assignment,
                                             resulting_pyname.get_object())
    
    def _call_function(self, pyname, function_name):
        if pyname is None:
            return
        pyobject = pyname.get_object()
        if function_name in pyobject.get_attributes():
            call_function = pyobject.get_attribute(function_name)
            return rope.base.pynames.AssignedName(
                pyobject=call_function.get_object()._get_returned_object())

    def infer_returned_object(self, pyobject):
        """Infers the `PyObject` this callable `PyObject` returns after calling"""
        dynamically_inferred_object = self.pycore.dynamicoi.infer_returned_object(pyobject)
        if dynamically_inferred_object is not None:
            return dynamically_inferred_object
        scope = pyobject.get_scope()
        if not scope._get_returned_asts():
            return
        for returned_node in reversed(scope._get_returned_asts()):
            try:
                resulting_pyname = rope.base.evaluate.StatementEvaluator.\
                                   get_statement_result(scope, returned_node)
                if resulting_pyname is None:
                    return None
                return resulting_pyname.get_object()
            except IsBeingInferredException:
                pass
    
    def infer_parameter_objects(self, pyobject):
        """Infers the `PyObject` of parameters of this callable `PyObject`"""
        dynamically_inferred_object = self.pycore.dynamicoi.infer_parameter_objects(pyobject)
        if dynamically_inferred_object is not None:
            return dynamically_inferred_object
        
