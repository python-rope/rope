import compiler.ast
import compiler.consts

import rope.base
from rope.base import pyobjects, evaluate


class StaticObjectInference(object):

    def __init__(self, pycore):
        self.pycore = pycore

    def infer_returned_object(self, pyobject, args):
        if args:
            # HACK: Setting parameter objects manually
            # This is not thread safe and might cause problems if `args`
            # is not a good call example
            pyobject._set_parameter_pyobjects(
                args.get_arguments(self._get_normal_params(pyobject)))
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
            except pyobjects.IsBeingInferredError:
                pass

    def infer_parameter_objects(self, pyobject):
        objects = []
        if pyobject.parent is not None and isinstance(pyobject.parent, pyobjects.PyClass):
            if not pyobject.decorators:
                objects.append(pyobjects.PyObject(pyobject.parent))
            elif self._is_staticmethod_decorator(pyobject.decorators.nodes[0]):
                objects.append(self._get_unknown())
            elif self._is_classmethod_decorator(pyobject.decorators.nodes[0]):
                objects.append(pyobject.parent)
            elif pyobject.get_param_names()[0] == 'self':
                objects.append(pyobjects.PyObject(pyobject.parent))
        params = self._get_normal_params(pyobject)
        for parameter in params[len(objects):]:
            objects.append(self._get_unknown())
        return objects

    def _get_normal_params(self, pyobject):
        node = pyobject._get_ast()
        params = list(node.argnames)
        if node.flags & compiler.consts.CO_VARKEYWORDS:
            del params[-1]
        if node.flags & compiler.consts.CO_VARARGS:
            del params[-1]
        return params

    def _get_unknown(self):
        return pyobjects.PyObject(pyobjects.get_base_type('Unknown'))

    def _is_staticmethod_decorator(self, node):
        return isinstance(node, compiler.ast.Name) and node.name == 'staticmethod'

    def _is_classmethod_decorator(self, node):
        return isinstance(node, compiler.ast.Name) and node.name == 'classmethod'

    def analyze_module(self, pymodule):
        """Analyze `pymodule` for static object inference"""
        visitor = SOIVisitor(self.pycore, pymodule)
        compiler.walk(pymodule._get_ast(), visitor)


class SOIVisitor(object):
    
    def __init__(self, pycore, pymodule):
        self.pycore = pycore
        self.pymodule = pymodule
        self.scope = pymodule.get_scope()

    def visitCallFunc(self, node):
        for child in node.getChildNodes():
            compiler.walk(child, self)
        scope = self.scope.get_inner_scope_for_line(node.lineno)
        pyname = evaluate.get_statement_result(scope, node.node)
        if pyname is None:
            return
        pyfunction = pyname.get_object()
        if '__call__' in pyfunction.get_attributes():
            pyfunction = pyfunction.get_attribute('__call__')
        if not isinstance(pyfunction, pyobjects.PyFunction):
            return
        args = evaluate.create_arguments(pyfunction, node, scope)
        self.pycore.call_info.function_called(
            pyfunction, args.get_arguments(pyfunction.get_param_names()))
