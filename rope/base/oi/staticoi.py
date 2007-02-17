import compiler.ast

from rope.base import pyobjects
from rope.base import pynames
from rope.base import builtins
from rope.base import evaluate


class StaticObjectInference(object):

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
            except pyobjects.IsBeingInferredError:
                pass

    def infer_parameter_objects(self, pyobject):
        objects = []
        if pyobject.parent.get_type() == pyobjects.get_base_type('Type'):
            if not pyobject.decorators:
                objects.append(pyobjects.PyObject(pyobject.parent))
            elif self._is_staticmethod_decorator(pyobject.decorators.nodes[0]):
                objects.append(pyobjects.PyObject(
                               pyobjects.get_base_type('Unknown')))
            elif self._is_classmethod_decorator(pyobject.decorators.nodes[0]):
                objects.append(pyobject.parent)
            elif pyobject.parameters[0] == 'self':
                objects.append(pyobjects.PyObject(pyobject.parent))
            else:
                objects.append(pyobjects.PyObject(
                               pyobjects.get_base_type('Unknown')))
        else:
            objects.append(pyobjects.PyObject(
                           pyobjects.get_base_type('Unknown')))
        for parameter in pyobject.parameters[1:]:
            objects.append(pyobjects.PyObject(
                           pyobjects.get_base_type('Unknown')))
        return objects

    def _is_staticmethod_decorator(self, node):
        return isinstance(node, compiler.ast.Name) and node.name == 'staticmethod'

    def _is_classmethod_decorator(self, node):
        return isinstance(node, compiler.ast.Name) and node.name == 'classmethod'
