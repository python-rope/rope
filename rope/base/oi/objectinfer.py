from rope.base.pyobjects import *
import rope.base.codeanalyze
import rope.base.oi.staticoi


class ObjectInfer(object):

    def __init__(self, pycore):
        self.ois = [rope.base.oi.staticoi.StaticObjectInference(),
                    rope.base.oi.dynamicoi.DynamicObjectInference(pycore)]
    
    def infer_assigned_object(self, pyname):
        """Infer the `PyObject` this `PyName` references"""
        for oi in self.ois:
            result = oi.infer_assigned_object(pyname)
            if result is not None:
                return result
    
    def infer_for_object(self, pyname):
        """Infer the `PyObject` this for loop variable `PyName` references"""
        for oi in self.ois:
            result = oi.infer_for_object(pyname)
            if result is not None:
                return result
    
    def infer_returned_object(self, pyobject, args):
        """Infer the `PyObject` this callable `PyObject` returns after calling"""
        for oi in reversed(self.ois):
            result = oi.infer_returned_object(pyobject, args)
            if result is not None:
                return result
    
    def infer_parameter_objects(self, pyobject):
        """Infer the `PyObject`\s of parameters of this callable `PyObject`"""
        for oi in reversed(self.ois):
            result = oi.infer_parameter_objects(pyobject)
            if result is not None:
                return result
