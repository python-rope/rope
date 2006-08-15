from rope.pyobjects import *
import rope.codeanalyze


class ObjectInfer(object):

    def __init__(self):
        pass
    
    def infer_object(self, pyname):
        """Infers the `PyObject` this `PyName` references"""
        if not pyname.assigned_asts:
            return
        for assign_node in reversed(pyname.assigned_asts):
            try:
                lineno = assign_node.lineno
                if lineno is None:
                    lineno = 1
                holding_scope = pyname.module.get_scope().\
                                get_inner_scope_for_line(lineno)
                resulting_pyname = rope.codeanalyze.StatementEvaluator.\
                                   get_statement_result(holding_scope, assign_node)
                if resulting_pyname is None:
                    return None
                return resulting_pyname.get_object()
            except IsBeingInferredException:
                pass
    
    def infer_returned_object(self, pyobject):
        """Infers the `PyObject` this callable `PyObject` returns after calling"""
        scope = pyobject.get_scope()
        if not scope._get_returned_asts():
            return
        for returned_node in reversed(scope._get_returned_asts()):
            try:
                resulting_pyname = rope.codeanalyze.StatementEvaluator.\
                                   get_statement_result(scope, returned_node)
                if resulting_pyname is None:
                    return None
                return resulting_pyname.get_object()
            except IsBeingInferredException:
                pass
        
