import rope.pyobjects


class PyName(object):

    def get_object(self):
        """Return the `PyObject` object referenced by this `PyName`"""
    
    def get_definition_location(self):
        """Return a (module, lineno) tuple"""


class DefinedName(PyName):
    
    def __init__(self, pyobject):
        self.pyobject = pyobject
    
    def get_object(self):
        return self.pyobject
    
    def get_definition_location(self):
        return (self.pyobject.get_module(), self.pyobject._get_ast().lineno)
    

class AssignedName(PyName):
    
    def __init__(self, lineno=None, module=None, pyobject=None):
        self.pyobject = pyobject
        self.lineno = lineno
        self.module = module
        self.is_being_inferred = False
        self.assigned_asts = []

    def get_object(self):
        if self.is_being_inferred:
            raise rope.pyobjects.IsBeingInferredException('Circular assignments')
        if self.pyobject is None and self.module is not None:
            self.is_being_inferred = True
            try:
                object_infer = self.module.pycore._get_object_infer()
                inferred_object = object_infer.infer_object(self)
                self.pyobject = inferred_object
            finally:
                self.is_being_inferred = False
        if self.pyobject is None:
            self.pyobject = rope.pyobjects.PyObject(rope.pyobjects.
                                                  PyObject.get_base_type('Unknown'))
        return self.pyobject
    
    def get_definition_location(self):
        """Returns a (module, lineno) tuple"""
        if self.lineno is None and self.assigned_asts:
            self.lineno = self.assigned_asts[0].lineno
        return (self.module, self.lineno)


class ImportedName(PyName):
    
    def __init__(self, imported_pyname):
        self.imported_pyname = imported_pyname
    
    def get_object(self):
        return self.imported_pyname.get_object()
    
    def get_definition_location(self):
        return self.imported_pyname.get_definition_location()


class ImportedModule(PyName):
    
    def __init__(self, pyobject=None):
        self.pyobject = pyobject
    
    def get_object(self):
        if self.pyobject is None:
            return rope.pyobjects.PyObject(rope.pyobjects.PyObject.get_base_type('Unknown'))
        return self.pyobject
    
    def get_definition_location(self):
        if self.pyobject is None:
            return (None, None)
        return (self.pyobject.get_module(), 1)


class ParameterName(PyName):
    
    def __init__(self, pyfunction, index):
        self.pyfunction = pyfunction
        self.index = index
        self.pyobject = None
    
    def get_object(self):
        if self.pyobject is None:
            self.pyobject = self.pyfunction._get_parameter(self.index)
        return self.pyobject
    
    def get_definition_location(self):
        return (self.pyfunction.get_module(), self.pyfunction._get_ast().lineno)
