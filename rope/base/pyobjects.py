from typing import Optional

from rope.base import ast, exceptions, utils


class PyObject:
    def __init__(self, type_):
        if type_ is None:
            type_ = self
        self.type = type_

    def get_attributes(self):
        if self.type is self:
            return {}
        return self.type.get_attributes()

    def get_attribute(self, name):
        if name not in self.get_attributes():
            raise exceptions.AttributeNotFoundError("Attribute %s not found" % name)
        return self.get_attributes()[name]

    def get_holding_objects(self):
        return (self.type,) if self.type is not self else ()

    def get_module(self):
        return None

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

    _types = None
    _unknown = None

    @staticmethod
    def _get_base_type(name):
        if PyObject._types is None:
            PyObject._types = {}
            base_type = PyObject(None)
            PyObject._types["Type"] = base_type
            PyObject._types["Module"] = PyObject(base_type)
            PyObject._types["Function"] = PyObject(base_type)
            PyObject._types["Unknown"] = PyObject(base_type)
        return PyObject._types[name]


def get_base_type(name):
    """Return the base type with name `name`.

    The base types are 'Type', 'Function', 'Module' and 'Unknown'.  It
    was used to check the type of a `PyObject` but currently its use
    is discouraged.  Use classes defined in this module instead.
    For example instead of
    ``pyobject.get_type() == get_base_type('Function')`` use
    ``isinstance(pyobject, AbstractFunction)``.

    You can use `AbstractClass` for classes, `AbstractFunction` for
    functions, and `AbstractModule` for modules.  You can also use
    `PyFunction` and `PyClass` for testing if an object is
    defined somewhere and rope can access its source.  These classes
    provide more methods.

    """
    return PyObject._get_base_type(name)


def get_unknown():
    """Return a pyobject whose type is unknown

    Note that two unknown objects are equal.  So for example you can
    write::

      if pyname.get_object() == get_unknown():
          print('cannot determine what this pyname holds')

    Rope could have used `None` for indicating unknown objects but
    we had to check that in many places.  So actually this method
    returns a null object.

    """
    if PyObject._unknown is None:
        PyObject._unknown = PyObject(get_base_type("Unknown"))
    return PyObject._unknown


class SampledValue(PyObject):
    """A representative value whose container position or cursor is unproved."""

    def __init__(self, representative, origin):
        super().__init__(representative.get_type())
        self.representative = representative
        self.origin = origin

    def get_attributes(self):
        return self.representative.get_attributes()

    def get_module(self):
        return self.representative.get_module()


def sampled_value(value, origin):
    if value is None or value is get_unknown() or isinstance(value, SampledValue):
        return value
    return SampledValue(value, origin)


def unsampled(value):
    """Return the representative behind a sampled read, else ``value``."""
    while isinstance(value, SampledValue):
        value = value.representative
    return value


class AbstractClass(PyObject):
    def __init__(self):
        super().__init__(get_base_type("Type"))

    def get_name(self):
        pass

    def get_doc(self):
        pass

    def get_superclasses(self):
        return []

    def get_metaclass(self):
        """Return the governing class, or the unresolved metaclass witness."""
        from rope.base import builtins

        return builtins.builtins["type"].get_object()

    def get_bases(self):
        """Return the resolved bases in declaration order

        Each item is either a class or an `UnresolvedBase` standing
        for a base expression rope could not evaluate to a class.
        Non-class bases with `__mro_entries__` expand into their returned
        classes. PEP 695 classes also retain their implicit Generic base.
        `get_superclasses()` returns only the classes.

        """
        return self.get_superclasses()

    def get_mro(self):
        """Return the method resolution order of this class

        The order is the C3 linearization Python uses for ``__mro__``,
        starting with this class.  An `UnresolvedBase` keeps its place
        in the order and contributes no ancestors.  Builtin classes
        contribute their runtime ``__mro__``; a class whose hierarchy
        names neither ``object`` nor a builtin class does not end with
        ``object``.

        Raises `rope.base.exceptions.InconsistentHierarchyError` when
        Python would refuse to create the class.

        """
        return linearize(self, self.get_bases())

    def get_consistent_mro(self):
        """Return `get_mro()`, or `None` when Python would refuse the class

        Unlike `get_mro()`, this never raises
        `rope.base.exceptions.InconsistentHierarchyError`.

        """
        return linearize(self, self.get_bases(), strict=False)

    def _get_own_attributes(self):
        """Return the attributes this class defines itself

        These are the attributes the method resolution order selects
        from this class.

        """
        return self.get_attributes()


class ConstructedClass(AbstractClass):
    """A class produced by native class construction, without a source declaration."""

    def __init__(self, name, bases, metaclass, attributes):
        super().__init__()
        self.name = name
        self.bases = list(bases)
        self.metaclass = metaclass
        self.attributes = dict(attributes)

    def get_name(self):
        return self.name

    def get_superclasses(self):
        return self.bases

    def get_metaclass(self):
        return self.metaclass

    def _get_own_attributes(self):
        return self.attributes

    def get_attributes(self):
        result = {}
        mro = self.get_consistent_mro()
        if mro is None:
            for base in reversed(self.get_superclasses()):
                result.update(base.get_attributes())
            result.update(self._get_own_attributes())
            return result
        for ancestor in reversed(mro):
            result.update(ancestor._get_own_attributes())
        return result


class UnresolvedBase(PyObject):
    """A class base that rope could not evaluate to a class

    `node` is the base expression in the class statement.  `pyobject`
    is what that expression evaluated to, or `None` when it did not
    evaluate at all.

    """

    def __init__(self, node, pyobject=None):
        super().__init__(get_base_type("Unknown"))
        self.node = node
        self.pyobject = pyobject

    def __eq__(self, obj):
        # Transient by design (never cached in `_bases`/`_mro`), so each
        # re-evaluation builds a fresh instance: unresolved bases identify
        # by their source expression and evaluation, not by identity.
        if isinstance(obj, UnresolvedBase):
            return self.node is obj.node and self.pyobject == obj.pyobject
        return NotImplemented

    def __ne__(self, obj):
        result = self.__eq__(obj)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash((UnresolvedBase, id(self.node)))

    def get_mro(self):
        return [self]

    def get_consistent_mro(self):
        return self.get_mro()

    def _get_own_attributes(self):
        return {}


def linearize(cls, bases, strict=True):
    """Return the C3 linearization of `cls` declared with `bases`

    Raises `rope.base.exceptions.InconsistentHierarchyError` for repeated
    bases and for bases whose orders cannot be merged.  When `strict` is
    false, these hierarchies, which Python refuses to create, return
    `None` instead.

    """
    for index, base in enumerate(bases):
        if any(base is previous for previous in bases[:index]):
            if not strict:
                return None
            raise exceptions.InconsistentHierarchyError(
                f"Duplicate base class in {_class_name(cls)}: {_class_name(base)}"
            )
    if strict:
        sequences = [list(base.get_mro()) for base in bases]
    else:
        sequences = [base.get_consistent_mro() for base in bases]
        if any(sequence is None for sequence in sequences):
            return None
        sequences = [list(sequence) for sequence in sequences]
    sequences.append(list(bases))
    result = [cls]
    while True:
        sequences = [sequence for sequence in sequences if sequence]
        if not sequences:
            return result
        for sequence in sequences:
            head = sequence[0]
            if not any(head is item for other in sequences for item in other[1:]):
                break
        else:
            if not strict:
                return None
            # Reporting the current heads identifies the pair of conflicting
            # hierarchies; a bare message would hide which ones dispute the
            # position. The sequence holding the unresolved head points to the
            # transient base, and the modules tell where each sequence came from.
            heads = []
            for sequence in sequences:
                head = _class_name(sequence[0])
                if isinstance(sequence[0], UnresolvedBase):
                    head = f"{head} (node={type(sequence[0].node).__name__}:{getattr(sequence[0].node, 'lineno', '?')})"
                origins = []
                for item in sequence[:3]:
                    try:
                        origins.append(
                            f"{_class_name(item)}@{item.get_module().get_name()}"
                        )
                    except Exception:
                        origins.append(_class_name(item))
                heads.append(f"{head} | first3={origins}")
            raise exceptions.InconsistentHierarchyError(
                "Cannot create a consistent method resolution order "
                f"for {_class_name(cls)} (blocked heads: {heads})"
            )
        result.append(head)
        for sequence in sequences:
            if sequence[0] is head:
                del sequence[0]


def _class_name(pyobject):
    if isinstance(pyobject, UnresolvedBase):
        return "<unresolved base>"
    return pyobject.get_name()


class AbstractFunction(PyObject):
    def __init__(self):
        super().__init__(get_base_type("Function"))

    def get_name(self):
        pass

    def get_doc(self):
        pass

    def get_param_names(self, special_args=True):
        return []

    def get_positional_param_names(self):
        return self.get_param_names(special_args=False)

    def get_keyword_param_names(self):
        return self.get_param_names(special_args=False)

    def get_returned_object(self, args):
        return get_unknown()


class AbstractModule(PyObject):
    def __init__(self, doc=None):
        super().__init__(get_base_type("Module"))

    def get_doc(self):
        pass

    def get_resource(self):
        pass


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
            # A cache published before structural creation completes can only
            # have been computed under the recursion guard (an empty temporary
            # set or a hierarchy evaluated against a partial world), so it is
            # stale. Invalidating it on completion gives later callers the real
            # set, as the function attribute visitor already does.
            if self.attributes.get() is not None:
                self.attributes.set(None)
            if self.concluded_attributes.get() is not None:
                self.concluded_attributes.set(None)
            bases = getattr(self, "_bases", None)
            mro = getattr(self, "_mro", None)
            if bases is not None and bases.get() is not None:
                bases.set(None)
            if mro is not None and mro.get() is not None:
                mro.set(None)
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

    def get_name(self):
        return None

    def get_doc(self) -> Optional[str]:
        if len(self.get_ast().body) > 0:
            expr = self.get_ast().body[0]
            if (
                isinstance(expr, ast.Expr)
                and isinstance(expr.value, ast.Constant)
                and isinstance(expr.value.value, str)
            ):
                return expr.value.value
        return None

    def _get_defined_objects(self):
        if self.defineds is None:
            self._get_structural_attributes()
        # The recursion guard in _get_structural_attributes returns {} without
        # completing creation, and objects without a visitor (for instance
        # PyComprehension) also leave defineds as None. Callers iterate the
        # result, so an empty mapping is the correct value on these paths.
        return self.defineds if self.defineds is not None else {}

    def _create_structural_attributes(self):
        if self.visitor_class is None:
            # Objects without a visitor (for instance PyComprehension) define
            # nothing; otherwise defineds stays None and _get_defined_objects
            # returns None, which breaks scope iteration.
            self.defineds = {}
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


class PyFunction(PyDefinedObject, AbstractFunction):
    pass


class PyComprehension(PyDefinedObject, PyObject):
    pass

    def get_name(self):
        return "<comprehension>"


class PyClass(PyDefinedObject, AbstractClass):
    pass


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


class _PyModule(PyDefinedObject, AbstractModule):
    def __init__(self, pycore, ast_node, resource):
        self.resource = resource
        self.concluded_data = []
        AbstractModule.__init__(self)
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

    @utils.saveit
    def _type_checking_tests(self):
        """Branch tests of this module decided against `typing.TYPE_CHECKING`

        A decision reads other modules, so it is concluded data.
        """
        return self._get_concluded_data()

    def get_resource(self):
        return self.resource


class PyModule(_PyModule):
    pass


class PyPackage(_PyModule):
    pass


class IsBeingInferredError(exceptions.RopeError):
    pass
