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
        return (self.pyobject.get_module(), self.pyobject._get_ast().lineno)


class AssignedName(PyName):

    def __init__(self, lineno=None, module=None, pyobject=None):
        self.lineno = lineno
        self.module = module
        self.is_being_inferred = False
        self.assignments = []
        self.pyobject = _get_concluded_data(module)
        self.pyobject.set(pyobject)

    def get_object(self):
        if self.is_being_inferred:
            raise rope.base.pyobjects.IsBeingInferredError('Circular assignments')
        if self.pyobject.get() is None and self.module is not None:
            self.is_being_inferred = True
            try:
                object_infer = self.module.pycore._get_object_infer()
                inferred_object = object_infer.infer_assigned_object(self)
                self.pyobject.set(inferred_object)
            finally:
                self.is_being_inferred = False
        if self.pyobject.get() is None:
            self.pyobject.set(rope.base.pyobjects.PyObject(rope.base.pyobjects.
                                                      get_base_type('Unknown')))
        return self.pyobject.get()

    def get_definition_location(self):
        """Returns a (module, lineno) tuple"""
        if self.lineno is None and self.assignments:
            self.lineno = self.assignments[0].ast_node.lineno
        return (self.module, self.lineno)


class _Assignment(object):

    def __init__(self, ast_node, index=None):
        self.ast_node = ast_node
        self.index = index


class ForName(PyName):

    def __init__(self, assignment=None, module=None):
        self.module = module
        self.pyobject = _get_concluded_data(module)
        self.assignment = assignment

    def get_object(self):
        if self.pyobject.get() is None:
            object_infer = self.module.pycore._get_object_infer()
            inferred_object = object_infer.infer_for_object(self)
            self.pyobject.set(inferred_object)
        if self.pyobject.get() is None:
            self.pyobject.set(rope.base.pyobjects.PyObject(
                              rope.base.pyobjects.get_base_type('Unknown')))
        return self.pyobject.get()

    def get_definition_location(self):
        return (self.module, self.assignment.ast_node.lineno)


class ParameterName(PyName):

    def __init__(self, pyfunction, index):
        self.pyfunction = pyfunction
        self.index = index
        self.pyobject = _get_concluded_data(self.pyfunction.get_module())

    def get_object(self):
        if self.pyobject.get() is None:
            self.pyobject.set(self.pyfunction.get_parameter(self.index))
        return self.pyobject.get()

    def get_definition_location(self):
        return (self.pyfunction.get_module(), self.pyfunction._get_ast().lineno)


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
                self.pymodule.get()._add_dependant(self.importing_module)
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
            return rope.base.pyobjects.PyObject(
                rope.base.pyobjects.get_base_type('Unknown'))
        return self._get_pymodule()

    def get_definition_location(self):
        if self._get_pymodule() is None:
            return (None, None)
        return (self._get_pymodule().get_module(), 1)


class ImportedName(PyName):

    def __init__(self, imported_module, imported_name):
        self.imported_module = imported_module
        self.imported_name = imported_name
        self.imported_pyname = _get_concluded_data(imported_module.importing_module)

    def _get_imported_pyname(self):
        if self.imported_pyname.get() is None:
            try:
                self.imported_pyname.set(self.imported_module.get_object()\
                                         .get_attribute(self.imported_name))
            except AttributeNotFoundError:
                pass
        if self.imported_pyname.get() is None:
            self.imported_pyname.set(AssignedName())
        return self.imported_pyname.get()

    def get_object(self):
        return self._get_imported_pyname().get_object()

    def get_definition_location(self):
        return self._get_imported_pyname().get_definition_location()


class StarImport(object):

    def __init__(self, imported_module):
        self.imported_module = imported_module
        self.names = _get_concluded_data(imported_module.importing_module)

    def get_names(self):
        if self.names.get() is None:
            if isinstance(self.imported_module.get_object(), rope.base.pyobjects.PyPackage):
                return {}
            result = {}
            for name, pyname in self.imported_module.get_object().get_attributes().iteritems():
                if not name.startswith('_'):
                    result[name] = ImportedName(self.imported_module, name)
            self.names.set(result)
        return self.names.get()


def _get_concluded_data(module):
    if module is None:
        return rope.base.pyobjects._ConcludedData()
    return module._get_concluded_data()
