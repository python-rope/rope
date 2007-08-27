import rope.base.pyobjects
from rope.base.exceptions import (ModuleNotFoundError,
                                  AttributeNotFoundError)


class PyName(object):
    """References to `PyObject`\s inside python programs"""

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
        return (self.pyobject.get_module(), self.pyobject.get_ast().lineno)


class AssignedName(PyName):

    def __init__(self, lineno=None, module=None, pyobject=None):
        self.lineno = lineno
        self.module = module
        self.assignments = []
        self.pyobject = _Inferred(self._get_inferred,
                                  _get_concluded_data(module))
        self.pyobject.set(pyobject)

    def _get_inferred(self):
        if self.module is not None:
            object_infer = self.module.pycore._get_object_infer()
            return object_infer.infer_assigned_object(self)

    def get_object(self):
        return self.pyobject.get()

    def get_definition_location(self):
        """Returns a (module, lineno) tuple"""
        if self.lineno is None and self.assignments:
            self.lineno = self.assignments[0].get_lineno()
        return (self.module, self.lineno)

    def invalidate(self):
        """Forget the `PyObject` this `PyName` holds"""
        self.pyobject.set(None)


class UnboundName(PyName):
    
    def __init__(self, pyobject=None):
        self.pyobject = pyobject
        if self.pyobject is None:
            self.pyobject = rope.base.pyobjects.get_unknown()

    def get_object(self):
        return self.pyobject

    def get_definition_location(self):
        return (None, None)


class _Assigned(object):
    """An assigned expression"""

    def __init__(self, ast_node, levels=None):
        """The `level` is `None` for simple assignments and is
        a list of numbers for tuple assignments for example in::

           a, (b, c) = x

        The levels for for `a` is ``[0]``, for `b` is ``[1, 0]`` and for
        `c` is ``[1, 1]``.

        """
        self.ast_node = ast_node
        if levels == None:
            self.levels = []
        else:
            self.levels = levels

    def get_lineno(self):
        return self.ast_node.lineno


class EvaluatedName(PyName):
    """A `PyName` that will be assigned an expression"""

    def __init__(self, assignment=None, module=None, evaluation= '',
                 lineno=None):
        """
        `evaluation` is a `str` that specifies what to do with the
        `assignment`.  For example for a for object the evaluation is
        '.__iter__().next()'.  That means first call the `__iter__()`
        method and then call `next()` from the resulting object.  As
        another example for with variables it is '.__enter__()'

        """
        self.module = module
        self.assignment = assignment
        self.lineno = lineno
        self.evaluation = evaluation
        self.pyobject = _Inferred(self._get_inferred,
                                  _get_concluded_data(module))

    def _get_inferred(self):
        object_infer = self.module.pycore._get_object_infer()
        return object_infer.evaluate_object(self)

    def get_object(self):
        return self.pyobject.get()

    def get_definition_location(self):
        return (self.module, self.lineno)

    def invalidate(self):
        """Forget the `PyObject` this `PyName` holds"""
        self.pyobject.set(None)


class ParameterName(PyName):

    def __init__(self, pyfunction, index):
        self.pyfunction = pyfunction
        self.index = index

    def get_object(self):
        result = self.pyfunction.get_parameter(self.index)
        if result is None:
            result = rope.base.pyobjects.get_unknown()
        return result

    def get_objects(self):
        """Returns the list of objects passed as this parameter"""
        object_infer = self.pyfunction.pycore._get_object_infer()
        return object_infer.get_passed_objects(self.pyfunction, self.index)

    def get_definition_location(self):
        return (self.pyfunction.get_module(), self.pyfunction.get_ast().lineno)


class ImportedModule(PyName):

    def __init__(self, importing_module, module_name=None,
                 level=0, resource=None):
        self.importing_module = importing_module
        self.module_name = module_name
        self.level = level
        self.resource = resource
        self.pymodule = _get_concluded_data(self.importing_module)

    def _get_current_folder(self):
        resource = self.importing_module.get_module().get_resource()
        if resource is None:
            return None
        return resource.parent

    def _get_pymodule(self):
        if self.pymodule.get() is None:
            pycore = self.importing_module.pycore
            if self.resource is not None:
                self.pymodule.set(pycore.resource_to_pyobject(self.resource))
            elif self.module_name is not None:
                try:
                    if self.level == 0:
                        self.pymodule.set(
                            pycore.get_module(self.module_name,
                                              self._get_current_folder()))
                    else:
                        self.pymodule.set(pycore.get_relative_module(
                                          self.module_name,
                                          self._get_current_folder(),
                                          self.level))
                except ModuleNotFoundError:
                    pass
        return self.pymodule.get()

    def get_object(self):
        if self._get_pymodule() is None:
            return rope.base.pyobjects.get_unknown()
        return self._get_pymodule()

    def get_definition_location(self):
        if self._get_pymodule() is None:
            return (None, None)
        return (self._get_pymodule().get_module(), 1)


class ImportedName(PyName):

    def __init__(self, imported_module, imported_name):
        self.imported_module = imported_module
        self.imported_name = imported_name

    def _get_imported_pyname(self):
        try:
            return self.imported_module.get_object().get_attribute(
                self.imported_name)
        except AttributeNotFoundError:
            return AssignedName()

    def get_object(self):
        return self._get_imported_pyname().get_object()

    def get_definition_location(self):
        return self._get_imported_pyname().get_definition_location()


class StarImport(object):

    def __init__(self, imported_module):
        self.imported_module = imported_module

    def get_names(self):
        result = {}
        imported = self.imported_module.get_object()
        for name, pyname in imported.get_attributes().items():
            if not name.startswith('_'):
                result[name] = ImportedName(self.imported_module, name)
        return result


def _get_concluded_data(module):
    if module is None:
        return rope.base.pyobjects._ConcludedData()
    return module._get_concluded_data()


class _Inferred(object):

    def __init__(self, get_inferred, concluded=None):
        self.get_inferred = get_inferred
        self.concluded = concluded
        self.is_being_inferred = False
        if self.concluded is None:
            self.temp = None

    def get(self, *args, **kwds):
        if self.is_being_inferred:
            raise rope.base.pyobjects.IsBeingInferredError(
                'Circular Object Inference')
        if self.concluded is None or self.concluded.get() is None:
            self.is_being_inferred = True
            try:
                self.set(self.get_inferred(*args, **kwds))
            finally:
                self.is_being_inferred = False
        if self._get() is None:
            self.set(rope.base.pyobjects.get_unknown())
        return self._get()

    def set(self, pyobject):
        if self.concluded is not None:
            self.concluded.set(pyobject)
        self.temp = pyobject

    def _get(self):
        if self.concluded is not None:
            return self.concluded.get()
        return self.temp
