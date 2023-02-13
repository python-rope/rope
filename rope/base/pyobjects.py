from typing import Optional

from rope.base import ast, exceptions, utils


class PyObject:
    def __init__(self, type_):
        self.type = type_ or self

    def get_attributes(self):
        if self.type is self:
            return {}
        return self.type.get_attributes()

    def get_attribute(self, name):
        if name not in self.get_attributes():
            raise exceptions.AttributeNotFoundError("Attribute %s not found" % name)
        return self.get_attributes()[name]

    def get_type(self):
        return self.type

    def __getitem__(self, key):
        """The same as ``get_attribute(key)``"""
        return self.get_attribute(key)

    def __contains__(self, key):
        """The same as ``key in self.get_attributes()``"""
        return key in self.get_attributes()

    def __eq__(self, obj):
        """Check the equality of two `PyObject`

        Currently it is assumed that instances (the direct instances
        of `PyObject`, not the instances of its subclasses) are equal
        if their types are equal.  For every other object like
        defineds or builtins rope assumes objects are reference
        objects and their identities should match.

        """
        if self.__class__ != obj.__class__:
            return False
        if type(self) == PyObject:
            if self is not self.type:
                return self.type == obj.type
            else:
                return self.type is obj.type
        return self is obj

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def __hash__(self):
        """See docs for `__eq__()` method"""
        if type(self) == PyObject and self != self.type:
            return hash(self.type) + 1
        else:
            return super().__hash__()

    def __iter__(self):
        """The same as ``iter(self.get_attributes())``"""
        return iter(self.get_attributes())


_anchor_types = None


def get_base_type(name: str) -> PyObject:
    """Return the base type with name `name`.

    The base types are 'Type', 'Function', 'Module' and 'Unknown'.  It
    was used to check the type of a `PyObject` but currently its use
    is discouraged.  Use classes defined in this module instead.
    For example instead of
    ``pyobject.get_type() == get_base_type('Function')`` use
    ``is_abstract_function(pyobject)``.

    You can use `is_abstract_class` for classes, `is_abstract_functions` for
    functions, and `is_abstract_module` for modules.

    """
    global _anchor_types
    if _anchor_types is None:
        base_type = PyObject(None)
        _anchor_types = {
            "Function": PyObject(base_type),
            "Module": PyObject(base_type),
            "Type": base_type,  # a Class.
            "Unknown": PyObject(base_type),
        }
    return _anchor_types[name]


def get_unknown() -> PyObject:
    """Return a pyobject whose type is unknown.

    Note that two unknown objects are equal.

    For example you can write::

      if pyname.get_object() == get_unknown():
          print('cannot determine what this pyname holds')

    Rope could have used `None` for indicating unknown objects but
    we had to check that in many places.
    """
    return get_base_type("Unknown")


class PyDefinedObject:
    """Python defined names that rope can access their sources"""

    def __init__(self, pycore, ast_node, parent):
        self.pycore = pycore
        self.ast_node = ast_node
        self.scope = None
        self.parent = parent
        self.structural_attributes = None
        self.concluded_attributes = self.get_module()._get_concluded_data()
        self.attributes = self.get_module()._get_concluded_data()
        self.defineds = None

    def __repr__(self):
        return '<{}.{} "{}" at {}>'.format(
            self.__class__.__module__,
            self.__class__.__name__,
            self.absolute_name,
            hex(id(self)),
        )

    @property
    def absolute_name(self):
        obj_name = self.get_name()
        return self.get_module().get_name() + ("::" + obj_name if obj_name else "")

    visitor_class = None

    @utils.prevent_recursion(lambda: {})
    def _get_structural_attributes(self):
        if self.structural_attributes is None:
            self.structural_attributes = self._create_structural_attributes()
        return self.structural_attributes

    @utils.prevent_recursion(lambda: {})
    def _get_concluded_attributes(self):
        if self.concluded_attributes.get() is None:
            self._get_structural_attributes()
            self.concluded_attributes.set(self._create_concluded_attributes())
        return self.concluded_attributes.get()

    def get_attributes(self):
        if self.attributes.get() is None:
            result = dict(self._get_concluded_attributes())
            result.update(self._get_structural_attributes())
            self.attributes.set(result)
        return self.attributes.get()

    def get_attribute(self, name):
        if name in self._get_structural_attributes():
            return self._get_structural_attributes()[name]
        if name in self._get_concluded_attributes():
            return self._get_concluded_attributes()[name]
        raise exceptions.AttributeNotFoundError("Attribute %s not found" % name)

    def get_scope(self):
        if self.scope is None:
            self.scope = self._create_scope()
        return self.scope

    def get_module(self):
        current_object = self
        while current_object.parent is not None:
            current_object = current_object.parent
        return current_object

    def get_doc(self) -> Optional[str]:
        if len(self.get_ast().body) > 0:
            expr = self.get_ast().body[0]
            if isinstance(expr, ast.Expr) and isinstance(expr.value, ast.Str):
                docstring = expr.value.s
                assert isinstance(docstring, str)
                return docstring
        return None

    def _get_defined_objects(self):
        if self.defineds is None:
            self._get_structural_attributes()
        return self.defineds

    def _create_structural_attributes(self):
        if self.visitor_class is None:
            return {}
        new_visitor = self.visitor_class(self.pycore, self)
        for child in ast.iter_child_nodes(self.ast_node):
            new_visitor.visit(child)
        self.defineds = new_visitor.defineds
        return new_visitor.names

    def _create_concluded_attributes(self):
        return {}

    def get_ast(self):
        return self.ast_node

    def _create_scope(self):
        pass


class PyFunction(PyDefinedObject, PyObject): ###, AbstractFunction):
    ### pass
    def __init__(self, pycore, ast_node, parent):
        PyObject.__init__(self, get_base_type("Function"))
        PyDefinedObject.__init__(self, pycore, ast_node, parent)




class PyComprehension(PyDefinedObject, PyObject):
    pass

    def get_name(self):
        return "<comprehension>"


class PyClass(PyDefinedObject, PyObject):  ###, AbstractClass):
    ### pass
    def __init__(self, pycore, ast_node, parent):
        PyObject.__init__(self, get_base_type("Type"))
        PyDefinedObject.__init__(self, pycore, ast_node, parent)


class _ConcludedData:
    def __init__(self):
        self.data_ = None

    def set(self, data):
        self.data_ = data

    def get(self):
        return self.data_

    data = property(get, set)

    def _invalidate(self):
        self.data = None

    def __str__(self):
        return "<" + str(self.data) + ">"


class _PyModule(PyDefinedObject, PyObject):  ###, AbstractModule):
    def __init__(self, pycore, ast_node, resource):
        self.resource = resource
        self.concluded_data = []
        ### AbstractModule.__init__(self)
        PyObject.__init__(self, get_base_type("Module"))
        PyDefinedObject.__init__(self, pycore, ast_node, None)

    @property
    def absolute_name(self) -> str:
        return self.get_name()

    def _get_concluded_data(self):
        new_data = _ConcludedData()
        self.concluded_data.append(new_data)
        return new_data

    def _forget_concluded_data(self):
        for data in self.concluded_data:
            data._invalidate()

    def get_resource(self):
        return self.resource


class PyModule(_PyModule):
    pass


class PyPackage(_PyModule):
    pass


class IsBeingInferredError(exceptions.RopeError):
    pass
