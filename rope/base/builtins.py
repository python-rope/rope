"""This module tries to support builtin types and functions."""

import collections.abc
import inspect
import io
import sys
import types
import typing
from functools import partial

import rope.base.evaluate
from rope.base import arguments, ast, pynames, pyobjects, utils


class BuiltinModule(pyobjects.AbstractModule):
    def __init__(self, name, pycore=None, initial=None):
        if initial is None:
            initial = {}
        super().__init__()
        self.name = name
        self.pycore = pycore
        self.initial = initial

    parent = None

    def get_attributes(self):
        return self.attributes

    def get_doc(self):
        if self.module:
            return self.module.__doc__

    def get_name(self):
        return self.name.split(".")[-1]

    @utils.saveit
    def get_scope(self):
        # Module scope over the native attribute mapping; builtin modules
        # carry no source, so the usual parsed-module scope does not apply.
        import rope.base.pyscopes

        return rope.base.pyscopes.BuiltinModuleScope(self)

    @property
    @utils.saveit
    def attributes(self):
        result = _object_attributes(self.module, self)
        result.update(self.initial)
        if self.pycore is not None:
            submodules = self.pycore._builtin_submodules(self.name)
            for name, module in submodules.items():
                result[name] = rope.base.builtins.BuiltinName(module)
        return result

    @property
    @utils.saveit
    def module(self):
        try:
            result = __import__(self.name)
            for token in self.name.split(".")[1:]:
                result = getattr(result, token, None)
            return result
        except ImportError:
            return


class _BuiltinElement:
    def __init__(self, builtin, parent=None):
        self.builtin = builtin
        self._parent = parent

    def get_doc(self):
        if self.builtin:
            return getattr(self.builtin, "__doc__", None)

    def get_name(self):
        if self.builtin:
            return getattr(self.builtin, "__name__", None)

    @property
    def parent(self):
        if self._parent is None:
            return builtins
        return self._parent


class BuiltinClass(_BuiltinElement, pyobjects.AbstractClass):
    def __init__(self, builtin, attributes, parent=None):
        _BuiltinElement.__init__(self, builtin, parent)
        pyobjects.AbstractClass.__init__(self)
        self.initial = attributes

    @utils.saveit
    def get_attributes(self):
        result = _object_attributes(self.builtin, self)
        typing_alias = any(
            self.builtin is owner for owner in (typing.Generic, typing.Protocol)
        )
        if typing_alias or (
            inspect.isclass(self.builtin)
            and self.builtin.__module__ == "builtins"
            and hasattr(self.builtin, "__class_getitem__")
        ):
            parent = self.parent
            project = (
                parent.pycore.project
                if isinstance(parent, BuiltinModule) and parent.pycore
                else None
            )
            result["__class_getitem__"] = _class_getitem(self, project, typing_alias)
        result.update(self.initial)
        return result

    @utils.saveit
    def get_superclasses(self):
        if not inspect.isclass(self.builtin):
            return []
        return [_runtime_class(base) for base in self.builtin.__bases__]

    @utils.saveit
    def get_mro(self):
        if not inspect.isclass(self.builtin):
            return [self]
        return [self] + [_runtime_class(cls) for cls in self.builtin.__mro__[1:]]

    def get_consistent_mro(self):
        return self.get_mro()

    def _get_own_attributes(self):
        if not inspect.isclass(self.builtin):
            return self.get_attributes()
        own = vars(self.builtin)
        return {
            name: pyname
            for name, pyname in self.get_attributes().items()
            if name in own or name in self.initial
        }

    def get_module(self):
        return builtins

    def get_metaclass(self):
        return _runtime_class(type(self.builtin))


_runtime_classes = {}


def _runtime_class(cls):
    """Return the rope class standing for the runtime class `cls`

    A class of the ``builtins`` module is the object the builtins module
    exposes, so it is the same object a source class names as a base.

    """
    if cls.__module__ == "builtins":
        pyname = builtins.get_attributes().get(cls.__name__)
        if pyname is not None:
            pyobject = pyname.get_object()
            if isinstance(pyobject, BuiltinClass) and pyobject.builtin is cls:
                return pyobject
    if cls not in _runtime_classes:
        _runtime_classes[cls] = BuiltinClass(cls, {})
    return _runtime_classes[cls]


def _is_runtime_class(value, runtime_class, *, binding=None, attribute=None):
    """Authenticate a native class against its runtime library declaration."""
    if isinstance(value, BuiltinClass):
        return value.builtin is runtime_class
    if isinstance(binding, pynames.ImportedName):
        module = binding.imported_module.get_object()
        attribute = binding.imported_name
    elif isinstance(binding, pynames.ImportedModule):
        module = binding.get_object()
    else:
        module = None
    if isinstance(module, pyobjects.PyModule) and attribute is not None:
        resource = module.get_resource()
        name = module.get_name()
        observed = sys.modules.get(name)
        if (
            name.partition(".")[0] in sys.stdlib_module_names
            and isinstance(observed, types.ModuleType)
            and resource is not None
            and isinstance(vars(observed).get("__file__"), str)
            and utils.same_file_path(resource.real_path, vars(observed)["__file__"])
            and vars(observed).get(attribute) is runtime_class
        ):
            return True
    if not isinstance(value, pyobjects.PyClass):
        return False
    module = value.get_module()
    resource = module.get_resource()
    runtime_module = inspect.getmodule(runtime_class)
    return (
        value.parent is module
        and value.get_name() == runtime_class.__name__
        and resource is not None
        and runtime_module is not None
        and utils.same_file_path(resource.real_path, runtime_module.__file__)
    )


def _is_runtime_form(value, runtime_form):
    """Authenticate a typing special form against its runtime declaration.

    ``typing.Unpack`` is a ``_SpecialForm``-decorated function, not a class,
    so class authentication does not apply: builtin-side values match by
    identity, source-side functions by their declaring module and name.
    """
    if isinstance(value, (BuiltinFunction, BuiltinUnknown)):
        return value.builtin is runtime_form
    if not isinstance(value, pyobjects.PyFunction):
        return False
    module = value.get_module()
    resource = module.get_resource()
    runtime_module = inspect.getmodule(runtime_form)
    return (
        value.parent is module
        and value.get_name() == getattr(runtime_form, "__name__", None)
        and resource is not None
        and runtime_module is not None
        and utils.same_file_path(resource.real_path, runtime_module.__file__)
    )


def _runtime_unpack(value):
    """Return the runtime ``Unpack`` form `value` stands for, if any."""
    for form in (
        getattr(typing, "Unpack", None),
        getattr(sys.modules.get("typing_extensions"), "Unpack", None),
    ):
        if form is not None and _is_runtime_form(value, form):
            return form
    return None


def _class_getitem(owner, project, typing_alias):
    return BuiltinName(
        BuiltinFunction(
            function=partial(
                _generic_alias, project=project, typing_alias=typing_alias
            ),
            argnames=["cls", "key"],
            parent=owner,
        )
    )


def _generic_alias(context, project, typing_alias):
    origin = context.get_argument("cls")
    key = context.get_argument("key")
    if origin is None or key is None:
        # A subscript whose origin or key could not be inferred yields no
        # alias and raises nothing; callers handle the absence.
        return None
    arguments_ = (
        key.get_type().get_holding_objects()
        if key is not None and isinstance(key.get_type(), Tuple)
        else (key,)
    )
    if any(
        _is_runtime_class(origin, owner) for owner in (typing.Generic, typing.Protocol)
    ):
        variables = tuple(
            typing.__dict__[name]
            for name in ("TypeVar", "ParamSpec", "TypeVarTuple")
            if name in typing.__dict__
        )
        direct = tuple(
            typing.__dict__[name]
            for name in ("TypeVar", "ParamSpec")
            if name in typing.__dict__
        )
        unwrapped = []
        invalid = None
        for argument in arguments_:
            # PEP 646: a TypeVarTuple parameter enters only unpacked — the
            # ``*Ts`` subscription marker or an explicit ``Unpack[Ts]``
            # alias; a raw ``Cls[Ts]`` subscript is the TypeError the
            # runtime raises.
            if isinstance(argument, UnpackedTypeVarTuple):
                allowed = variables
                argument = argument.target
            elif (
                isinstance(argument, GenericAlias)
                and argument.typing_alias
                and len(argument.arguments) == 1
                and _runtime_unpack(argument.origin) is not None
            ):
                allowed = variables
                argument = argument.arguments[0]
            else:
                allowed = direct
            if argument is None or not any(
                _is_runtime_class(argument.get_type(), variable) for variable in allowed
            ):
                invalid = argument
                break
            unwrapped.append(argument)
        if invalid is not None or not unwrapped:
            error = TypeError(f"{origin.get_name()} parameters must be type variables")
            notes = [
                (
                    f"alias origin={type(origin).__name__}@{id(origin):x} "
                    f"key={type(key).__name__}@{id(key):x}"
                )
            ]
            try:
                for index, argument in enumerate(arguments_):
                    if argument is None:
                        notes.append(f"argument[{index}]=None")
                        continue
                    for label, value in (
                        ("object", argument),
                        ("type", argument.get_type()),
                    ):
                        module = value.get_module()
                        resource = module.get_resource() if module is not None else None
                        module_name = module.get_name() if module is not None else None
                        resource_path = (
                            resource.real_path if resource is not None else None
                        )
                        name = (
                            value.get_name()
                            if isinstance(value, pyobjects.AbstractClass)
                            else None
                        )
                        notes.append(
                            f"argument[{index}].{label}="
                            f"{type(value).__name__}@{id(value):x} name={name!r} "
                            f"module={module_name!r} resource={resource_path!r}"
                        )
            except Exception as diagnostic_error:
                notes.append(f"generic argument context failed: {diagnostic_error!r}")
            error.__dict__["__notes__"] = notes
            raise error
        if len({id(argument) for argument in unwrapped}) != len(unwrapped):
            raise TypeError(f"{origin.get_name()} parameters must be unique")
        # The alias keeps the arguments as subscribed, like the runtime's
        # ``__args__``; unwrapping is validation-internal.
    return GenericAlias(origin, arguments_, project, typing_alias)


class GenericAlias(pyobjects.PyObject):
    """The native value of a standard-library class subscription."""

    def __init__(self, origin, arguments_, project, typing_alias):
        super().__init__(
            _runtime_class(typing._GenericAlias if typing_alias else types.GenericAlias)
        )
        self.origin = origin
        self.arguments = arguments_
        self.project = project
        self.typing_alias = typing_alias

    def __eq__(self, other):
        if not isinstance(other, GenericAlias):
            return NotImplemented
        return (
            self.origin is other.origin
            and len(self.arguments) == len(other.arguments)
            and all(
                left is right for left, right in zip(self.arguments, other.arguments)
            )
        )

    def __ne__(self, other):
        equal = self.__eq__(other)
        return NotImplemented if equal is NotImplemented else not equal

    def __hash__(self):
        return hash(
            (id(self.origin), tuple(id(argument) for argument in self.arguments))
        )

    def get_attributes(self):
        return {
            "__origin__": BuiltinName(self.origin),
            "__args__": BuiltinName(get_tuple(*self.arguments)),
            "__mro_entries__": BuiltinName(
                BuiltinFunction(function=self._mro_entries, argnames=["self", "bases"])
            ),
        }

    def _mro_entries(self, context):
        original = context.get_argument("bases").get_type().get_holding_objects()
        if _is_runtime_class(self.origin, typing.Generic):
            protocol = self.project.get_module("typing")["Protocol"].get_object()
            if any(base is protocol for base in original):
                return get_tuple()
            # Alias equality is origin plus arguments: an instance rebuilt
            # from the same signature is not found by identity, and a
            # missing alias must not leak StopIteration.
            position = next(
                (index for index, base in enumerate(original) if base == self),
                None,
            )
            if position is not None and any(
                isinstance(base, GenericAlias) and base.typing_alias and base != self
                for base in original[position + 1 :]
            ):
                return get_tuple()
        return get_tuple(self.origin)


class BuiltinFunction(_BuiltinElement, pyobjects.AbstractFunction):
    def __init__(
        self, returned=None, function=None, builtin=None, argnames=None, parent=None
    ):
        if argnames is None:
            argnames = []
        _BuiltinElement.__init__(self, builtin, parent)
        pyobjects.AbstractFunction.__init__(self)
        self.argnames = argnames
        self.returned = returned
        self.function = function

    def get_returned_object(self, args):
        if self.function is not None:
            return self.function(_CallContext(self.argnames, args))
        else:
            return self.returned

    def get_param_names(self, special_args=True):
        return self.argnames


class BuiltinUnknown(_BuiltinElement, pyobjects.PyObject):
    def __init__(self, builtin):
        super().__init__(pyobjects.get_unknown())
        self.builtin = builtin
        self.type = pyobjects.get_unknown()

    def get_name(self):
        return getattr(type(self.builtin), "__name__", None)

    @utils.saveit
    def get_attributes(self):
        return _object_attributes(self.builtin, self)


def _object_attributes(obj, parent):
    attributes = {}
    for name in dir(obj):
        if name == "None":
            continue
        try:
            child = getattr(obj, name)
        except AttributeError:
            # descriptors are allowed to raise AttributeError
            # even if they are in dir()
            continue
        pyobject = None
        if inspect.isclass(child):
            pyobject = BuiltinClass(child, {}, parent=parent)
        elif inspect.isroutine(child):
            pyobject = BuiltinFunction(builtin=child, parent=parent)
        else:
            pyobject = BuiltinUnknown(builtin=child)
        attributes[name] = BuiltinName(pyobject)
    return attributes


def _create_builtin_type_getter(cls):
    def _get_builtin(*args):
        if not hasattr(cls, "_generated"):
            cls._generated = {}
        # Identity-keyed: plain ``PyObject``s hash and compare by type,
        # so a value-keyed cache collapses distinct inferred objects
        # (each module's own ``TypeVar``/``TypeVarTuple``) onto one
        # cached builtin.  The cached instance holds its arguments
        # strongly, so an id cannot be reused while its entry lives.
        key = tuple(id(arg) for arg in args)
        if key not in cls._generated:
            cls._generated[key] = cls(*args)
        return cls._generated[key]

    return _get_builtin


def _create_builtin_getter(cls):
    type_getter = _create_builtin_type_getter(cls)

    def _get_builtin(*args):
        return pyobjects.PyObject(type_getter(*args))

    return _get_builtin


class _CallContext:
    def __init__(self, argnames, args):
        self.argnames = argnames
        self.args = args

    def _get_scope_and_pyname(self, pyname):
        # A value overlay keeps the source name its per-name data belongs to.
        from rope.base.sourcebindings import SourceValueName

        if isinstance(pyname, SourceValueName):
            pyname = pyname.source_pyname
        if pyname is not None and isinstance(pyname, pynames.AssignedName):
            pymodule, lineno = pyname.get_definition_location()
            if pymodule is None:
                return None, None
            if lineno is None:
                lineno = 1
            scope = pymodule.get_scope().get_inner_scope_for_line(lineno)
            name = None
            while name is None and scope is not None:
                for current in scope.get_names():
                    if scope[current] is pyname:
                        name = current
                        break
                else:
                    scope = scope.parent
            return scope, name
        return None, None

    def get_argument(self, name):
        if self.args:
            args = self.args.get_arguments(self.argnames)
            return args[self.argnames.index(name)]

    def get_pyname(self, name):
        if self.args:
            args = self.args.get_pynames(self.argnames)
            if name in self.argnames:
                return args[self.argnames.index(name)]

    def get_arguments(self, argnames):
        if self.args:
            return self.args.get_arguments(argnames)

    def get_pynames(self, argnames):
        if self.args:
            return self.args.get_pynames(argnames)

    def get_per_name(self):
        if self.args is None:
            return None
        pyname = self.args.get_instance_pyname()
        scope, name = self._get_scope_and_pyname(pyname)
        if name is not None:
            pymodule = pyname.get_definition_location()[0]
            return pymodule.pycore.object_info.get_per_name(scope, name)
        return None

    def save_per_name(self, value):
        if self.args is None:
            return None
        pyname = self.args.get_instance_pyname()
        scope, name = self._get_scope_and_pyname(pyname)
        if name is not None:
            pymodule = pyname.get_definition_location()[0]
            # Per-name container state records element types, not positions,
            # so a value sampled from another container keeps its type.
            pymodule.pycore.object_info.save_per_name(
                scope, name, pyobjects.unsampled(value)
            )


class _AttributeCollector:
    def __init__(self, type):
        self.attributes = {}
        self.type = type

    def __call__(
        self,
        name,
        returned=None,
        function=None,
        argnames=None,
        check_existence=True,
        parent=None,
    ):
        if argnames is None:
            argnames = ["self"]
        try:
            builtin = getattr(self.type, name)
        except AttributeError:
            if check_existence:
                raise
            builtin = None
        self.attributes[name] = BuiltinName(
            BuiltinFunction(
                returned=returned,
                function=function,
                argnames=argnames,
                builtin=builtin,
                parent=parent,
            )
        )

    def __setitem__(self, name, value):
        self.attributes[name] = value


def _read_mutable_holding(value, origin):
    return pyobjects.sampled_value(value, origin)


class Sequence(BuiltinClass):
    """A read-only native sequence retaining its element object."""

    def __init__(self, holding=None):
        self.holding = holding
        collector = _AttributeCollector(collections.abc.Sequence)
        collector(
            "__getitem__", function=self._item, argnames=["self", "key"], parent=self
        )
        for name in ("__iter__", "__reversed__"):
            collector(name, returned=get_iterator(holding), parent=self)
        for name in ("__len__", "index", "count"):
            collector(
                name,
                returned=pyobjects.PyObject(builtins["int"].get_object()),
                parent=self,
            )
        collector(
            "__contains__",
            returned=pyobjects.PyObject(builtins["bool"].get_object()),
            parent=self,
        )
        super().__init__(collections.abc.Sequence, collector.attributes)

    def get_holding_objects(self):
        return (self.holding,)

    def _item(self, context):
        key = context.get_argument("key")
        if key is None:
            return pyobjects.get_unknown()
        if key.get_type() == builtins["slice"].get_object():
            return get_sequence(self.holding)
        if key.get_type() in (
            builtins["int"].get_object(),
            builtins["bool"].get_object(),
        ):
            return self.holding
        return pyobjects.get_unknown()


get_sequence = _create_builtin_getter(Sequence)
get_sequence_type = _create_builtin_type_getter(Sequence)


class List(BuiltinClass):
    def __init__(self, holding=None):
        self.holding = holding
        collector = _AttributeCollector(list)

        collector("__iter__", function=self._iterator_get, parent=self)
        collector("__new__", function=self._new_list, parent=self)

        # Adding methods
        collector(
            "append", function=self._list_add, argnames=["self", "value"], parent=self
        )
        collector(
            "__setitem__",
            function=self._list_add,
            argnames=["self", "index", "value"],
            parent=self,
        )
        collector(
            "insert",
            function=self._list_add,
            argnames=["self", "index", "value"],
            parent=self,
        )
        collector(
            "extend",
            function=self._self_set,
            argnames=["self", "iterable"],
            parent=self,
        )

        # Getting methods
        collector("__getitem__", function=self._list_get, parent=self)
        collector("pop", function=self._list_get, parent=self)
        try:
            collector("__getslice__", function=self._list_get)
        except AttributeError:
            pass

        super().__init__(list, collector.attributes)

    def get_holding_objects(self):
        return (self.holding,)

    def _new_list(self, args):
        return _create_builtin(args, get_list)

    def _list_add(self, context):
        if self.holding is not None:
            return
        holding = context.get_argument("value")
        if holding is not None and holding != pyobjects.get_unknown():
            context.save_per_name(holding)

    def _self_set(self, context):
        if self.holding is not None:
            return
        iterable = context.get_pyname("iterable")
        holding = _infer_sequence_for_pyname(iterable)
        if holding is not None and holding != pyobjects.get_unknown():
            context.save_per_name(holding)

    def _list_get(self, context):
        holding = _read_mutable_holding(
            self.holding if self.holding is not None else context.get_per_name(), self
        )
        args = context.get_arguments(["self", "key"])
        if (
            args is not None
            and len(args) > 1
            and args[1] is not None
            and args[1].get_type() == builtins["slice"].get_object()
        ):
            return get_list(holding)
        return holding

    def _iterator_get(self, context):
        return get_iterator(self._list_get(context))

    def _self_get(self, context):
        return get_list(self._list_get(context))


get_list = _create_builtin_getter(List)
get_list_type = _create_builtin_type_getter(List)


class LiteralString(pyobjects.PyObject):
    """A known string value retaining the canonical builtin string class."""

    def __init__(self, value):
        super().__init__(get_str_type())
        self.value = value

    def __eq__(self, obj):
        # Literal values are value objects: two known strings with the same
        # text are the same object, unlike reference-like builtin types.
        if isinstance(obj, LiteralString):
            return self.value == obj.value
        return NotImplemented

    def __ne__(self, obj):
        result = self.__eq__(obj)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash((LiteralString, self.value))


class UnpackedTypeVarTuple(pyobjects.PyObject):
    """PEP 646 ``*Ts`` subscription marker holding the parameter target.

    The starred subscription syntax exists only at the expression level;
    this marker carries the unpack fact from the evaluator into the typing
    alias validation, which accepts a TypeVarTuple parameter only through
    it (a raw ``Cls[Ts]`` subscript is the runtime ``TypeError``).
    """

    def __init__(self, target):
        super().__init__(pyobjects.get_base_type("Unknown"))
        self.target = target


class LiteralDict(pyobjects.PyObject):
    """A literal namespace whose exact entries remain known until mutation."""

    def __init__(self, keys, values, entries):
        super().__init__(Dict(keys, values))
        self.entries = entries
        result = self.type.get_attributes()
        if entries is not None:
            result["__getitem__"] = BuiltinName(
                BuiltinFunction(
                    function=self._lookup,
                    argnames=["self", "key"],
                    builtin=dict.__getitem__,
                )
            )
        for name in (
            "__setitem__",
            "__delitem__",
            "clear",
            "pop",
            "popitem",
            "setdefault",
            "update",
            "__ior__",
        ):
            if name in result:
                function = result[name].get_object()
                result[name] = BuiltinName(
                    BuiltinFunction(
                        function=partial(self._mutate, function=function),
                        argnames=function.get_param_names(),
                    )
                )

    def get_holding_objects(self):
        if self.entries is None:
            return (self.type,)
        return (self.type, *(entry.get_object() for entry in self.entries.values()))

    def _lookup(self, context):
        key = context.get_argument("key")
        if (
            self.entries is not None
            and isinstance(key, LiteralString)
            and key.value in self.entries
        ):
            return _read_mutable_holding(self.entries[key.value].get_object(), self)
        return pyobjects.get_unknown()

    def _mutate(self, context, function):
        self.entries = None
        return function.get_returned_object(context.args)


class Dict(BuiltinClass):
    def __init__(self, keys=None, values=None):
        self.keys = keys
        self.values = values
        collector = _AttributeCollector(dict)
        collector("__new__", function=self._new_dict, parent=self)
        collector("__setitem__", function=self._dict_add, parent=self)
        collector("popitem", function=self._item_get, parent=self)
        collector("pop", function=self._value_get, parent=self)
        collector("get", function=self._key_get, parent=self)
        collector("keys", function=self._key_list, parent=self)
        collector("values", function=self._value_list, parent=self)
        collector("items", function=self._item_list, parent=self)
        collector("copy", function=self._self_get, parent=self)
        collector("__getitem__", function=self._value_get, parent=self)
        collector("__iter__", function=self._key_iter, parent=self)
        collector("update", function=self._self_set, parent=self)
        super().__init__(dict, collector.attributes)

    def get_holding_objects(self):
        return (self.keys, self.values)

    def _new_dict(self, args):
        supplied = args.get_pynames(["sequence"])
        items = (
            pyobjects.unsampled(supplied[0].get_object())
            if supplied and supplied[0] is not None
            else None
        )
        if isinstance(items, NamespaceItems):
            # Namespace pairs describe the element type; the sampled position
            # of the read that produced them is irrelevant to their entries.
            return items.namespace

        def do_create(holding=None):
            if holding is None:
                return get_dict()
            type = holding.get_type()
            if isinstance(type, Tuple) and len(type.get_holding_objects()) == 2:
                return get_dict(*type.get_holding_objects())

        return _create_builtin(args, do_create)

    def _dict_add(self, context):
        if self.keys is not None:
            return
        key, value = context.get_arguments(["self", "key", "value"])[1:]
        if key is not None and key != pyobjects.get_unknown():
            context.save_per_name(get_tuple(key, value))

    def _item_get(self, context):
        item = context.get_per_name() if self.keys is None else None
        if item is None or not isinstance(item.get_type(), Tuple):
            holdings = (self.keys, self.values)
        else:
            holdings = item.get_type().get_holding_objects()
        return get_tuple(*(_read_mutable_holding(value, self) for value in holdings))

    def _value_get(self, context):
        item = self._item_get(context).get_type()
        return item.get_holding_objects()[1]

    def _key_get(self, context):
        item = self._item_get(context).get_type()
        return item.get_holding_objects()[0]

    def _value_list(self, context):
        return get_list(self._value_get(context))

    def _key_list(self, context):
        return get_list(self._key_get(context))

    def _item_list(self, context):
        return get_list(self._item_get(context))

    def _value_iter(self, context):
        return get_iterator(self._value_get(context))

    def _key_iter(self, context):
        return get_iterator(self._key_get(context))

    def _item_iter(self, context):
        return get_iterator(self._item_get(context))

    def _self_get(self, context):
        item = self._item_get(context).get_type()
        key, value = item.get_holding_objects()[:2]
        return get_dict(key, value)

    def _self_set(self, context):
        if self.keys is not None:
            return
        new_dict = context.get_pynames(["self", "d"])[1]
        if new_dict and isinstance(new_dict.get_object().get_type(), Dict):
            args = arguments.ObjectArguments([new_dict])
            items = (
                new_dict.get_object()["popitem"].get_object().get_returned_object(args)
            )
            context.save_per_name(items)
        else:
            holding = _infer_sequence_for_pyname(new_dict)
            if holding is not None and isinstance(holding.get_type(), Tuple):
                context.save_per_name(holding)


get_dict = _create_builtin_getter(Dict)
get_dict_type = _create_builtin_type_getter(Dict)


class Tuple(BuiltinClass):
    def __init__(self, *objects):
        self.objects = objects
        first = None
        if objects:
            first = objects[0]
        attributes = {
            "__getitem__": BuiltinName(
                BuiltinFunction(function=self._item, argnames=["self", "key"])
            ),
            "__getslice__": BuiltinName(BuiltinFunction(pyobjects.PyObject(self))),
            "__new__": BuiltinName(BuiltinFunction(function=self._new_tuple)),
            "__iter__": BuiltinName(BuiltinFunction(get_iterator(first))),
        }
        super().__init__(tuple, attributes)

    def get_holding_objects(self):
        return self.objects

    def get_item(self, index):
        if -len(self.objects) <= index < len(self.objects):
            return self.objects[index]

    def _item(self, context):
        key = context.get_argument("key")
        if (
            key is not None
            and key.get_type()
            in (
                builtins["int"].get_object(),
                builtins["bool"].get_object(),
            )
            and self.objects
            and all(value == self.objects[0] for value in self.objects)
        ):
            return self.objects[0]
        return pyobjects.get_unknown()

    def _new_tuple(self, args):
        return _create_builtin(args, get_tuple)


get_tuple = _create_builtin_getter(Tuple)
get_tuple_type = _create_builtin_type_getter(Tuple)


class Set(BuiltinClass):
    def __init__(self, holding=None):
        self.holding = holding
        collector = _AttributeCollector(set)
        collector("__new__", function=self._new_set)

        self_methods = [
            "copy",
            "difference",
            "intersection",
            "symmetric_difference",
            "union",
        ]
        for method in self_methods:
            collector(method, function=self._self_get, parent=self)
        collector("add", function=self._set_add, parent=self)
        collector("update", function=self._self_set, parent=self)
        collector("update", function=self._self_set, parent=self)
        collector("symmetric_difference_update", function=self._self_set, parent=self)
        collector("difference_update", function=self._self_set, parent=self)

        collector("pop", function=self._set_get, parent=self)
        collector("__iter__", function=self._iterator_get, parent=self)
        super().__init__(set, collector.attributes)

    def get_holding_objects(self):
        return (self.holding,)

    def _new_set(self, args):
        return _create_builtin(args, get_set)

    def _set_add(self, context):
        if self.holding is not None:
            return
        holding = context.get_arguments(["self", "value"])[1]
        if holding is not None and holding != pyobjects.get_unknown():
            context.save_per_name(holding)

    def _self_set(self, context):
        if self.holding is not None:
            return
        iterable = context.get_pyname("iterable")
        holding = _infer_sequence_for_pyname(iterable)
        if holding is not None and holding != pyobjects.get_unknown():
            context.save_per_name(holding)

    def _set_get(self, context):
        return _read_mutable_holding(
            self.holding if self.holding is not None else context.get_per_name(), self
        )

    def _iterator_get(self, context):
        return get_iterator(self._set_get(context))

    def _self_get(self, context):
        return get_list(self._set_get(context))


get_set = _create_builtin_getter(Set)
get_set_type = _create_builtin_type_getter(Set)


class Str(BuiltinClass):
    def __init__(self):
        self_object = pyobjects.PyObject(self)
        collector = _AttributeCollector(str)
        collector("__iter__", get_iterator(self_object), check_existence=False)

        self_methods = [
            "__getitem__",
            "capitalize",
            "center",
            "encode",
            "expandtabs",
            "join",
            "ljust",
            "lower",
            "lstrip",
            "replace",
            "rjust",
            "rstrip",
            "strip",
            "swapcase",
            "title",
            "translate",
            "upper",
            "zfill",
        ]
        for method in self_methods:
            collector(method, self_object, parent=self)

        py2_self_methods = ["__getslice__", "decode"]
        for method in py2_self_methods:
            try:
                collector(method, self_object)
            except AttributeError:
                pass

        for method in ["rsplit", "split", "splitlines"]:
            collector(method, get_list(self_object), parent=self)

        super().__init__(str, collector.attributes)

    def get_doc(self):
        return str.__doc__


get_str = _create_builtin_getter(Str)
get_str_type = _create_builtin_type_getter(Str)


class BuiltinName(pynames.PyName):
    def __init__(self, pyobject):
        self.pyobject = pyobject

    def get_object(self):
        return self.pyobject

    def get_definition_location(self):
        return (None, None)


class Iterator(pyobjects.AbstractClass):
    def __init__(self, holding=None):
        super().__init__()
        # The element type is proven; only the cursor position of a read is not.
        self.holding = holding
        self.attributes = {
            "next": BuiltinName(BuiltinFunction(_read_mutable_holding(holding, self))),
            "__iter__": BuiltinName(BuiltinFunction(self)),
        }

    def get_holding_objects(self):
        return (self.holding,)

    def get_attributes(self):
        return self.attributes

    def get_returned_object(self, args):
        return _read_mutable_holding(self.holding, self)


get_iterator = _create_builtin_getter(Iterator)


class Generator(pyobjects.AbstractClass):
    def __init__(self, holding=None):
        super().__init__()
        self.holding = holding
        self.attributes = {
            "next": BuiltinName(BuiltinFunction(_read_mutable_holding(holding, self))),
            "__iter__": BuiltinName(BuiltinFunction(get_iterator(holding))),
            "close": BuiltinName(BuiltinFunction()),
            "send": BuiltinName(BuiltinFunction()),
            "throw": BuiltinName(BuiltinFunction()),
        }

    def get_holding_objects(self):
        return (self.holding,)

    def get_attributes(self):
        return self.attributes

    def get_returned_object(self, args):
        return self.holding


get_generator = _create_builtin_getter(Generator)


class File(BuiltinClass):
    def __init__(self, filename=None, mode="r", *args):
        self.filename = filename
        self.mode = mode
        self.args = args
        str_object = get_str()
        str_list = get_list(get_str())
        attributes = {}

        def add(name, returned=None, function=None):
            builtin = getattr(io.TextIOBase, name, None)
            attributes[name] = BuiltinName(
                BuiltinFunction(returned=returned, function=function, builtin=builtin)
            )

        add("__iter__", get_iterator(str_object))
        add("__enter__", returned=pyobjects.PyObject(self))
        for method in ["next", "read", "readline", "readlines"]:
            add(method, str_list)
        for method in [
            "close",
            "flush",
            "lineno",
            "isatty",
            "seek",
            "tell",
            "truncate",
            "write",
            "writelines",
        ]:
            add(method)
        super().__init__(open, attributes)


get_file = _create_builtin_getter(File)
get_file_type = _create_builtin_type_getter(File)


class Property(BuiltinClass):
    def __init__(self, fget=None, fset=None, fdel=None, fdoc=None):
        self._fget = fget
        self._fdoc = fdoc
        attributes = {
            "fget": BuiltinName(BuiltinFunction()),
            "fset": BuiltinName(pynames.UnboundName()),
            "fdel": BuiltinName(pynames.UnboundName()),
            "__new__": BuiltinName(BuiltinFunction(function=_property_function)),
        }
        super().__init__(property, attributes)

    def get_property_object(self, args):
        if isinstance(self._fget, pyobjects.AbstractFunction):
            return self._fget.get_returned_object(args)


def _property_function(args):
    parameters = args.get_arguments(["fget", "fset", "fdel", "fdoc"])
    return pyobjects.PyObject(Property(parameters[0]))


class Lambda(pyobjects.AbstractFunction):
    def __init__(self, node, scope):
        super().__init__()
        self.node = node
        self.arguments = node.args
        self.scope = scope

    def get_returned_object(self, args):
        result = rope.base.evaluate.eval_node(self.scope, self.node.body)
        if result is not None:
            return result.get_object()
        else:
            return pyobjects.get_unknown()

    def get_module(self):
        return self.parent.get_module()

    def get_scope(self):
        return self.scope

    def get_kind(self):
        return "lambda"

    def get_ast(self):
        return self.node

    def get_attributes(self):
        return {}

    def get_name(self):
        return "lambda"

    def get_param_names(self, special_args=True):
        result = [node.arg for node in self.arguments.args if isinstance(node, ast.arg)]
        if self.arguments.vararg:
            result.append("*" + self.arguments.vararg.arg)
        if self.arguments.kwarg:
            result.append("**" + self.arguments.kwarg.arg)
        return result

    @property
    def parent(self):
        return self.scope.pyobject


def _attribute_access(context, *, class_access):
    receiver = context.get_pyname("self")
    name = context.get_argument("name")
    if receiver is None or not isinstance(name, LiteralString):
        return pyobjects.get_unknown()
    value = receiver.get_object()
    if (
        value is None
        or value == pyobjects.get_unknown()
        or isinstance(value, pyobjects.AbstractClass) != class_access
    ):
        return pyobjects.get_unknown()
    try:
        selected = value[name.value].get_object()
    except rope.base.exceptions.AttributeNotFoundError:
        return pyobjects.get_unknown()
    if isinstance(selected, pyobjects.PyFunction):
        for decorator in selected.decorators:
            binding = rope.base.evaluate.eval_node(
                selected.parent.get_scope(), decorator
            )
            if binding is None or getattr(
                binding.get_object(), "builtin", None
            ) not in (staticmethod, classmethod):
                return pyobjects.get_unknown()
        kind = selected.get_kind()
        if kind == "classmethod" or kind == "method" and not class_access:
            from rope.base.classfunctions import BoundFunction

            if kind == "classmethod" and not class_access:
                receiver = pynames.UnboundName(value.get_type())
            return BoundFunction(selected, receiver)
    return selected


def _attribute_access_name(owner, *, class_access):
    return BuiltinName(
        BuiltinFunction(
            function=partial(_attribute_access, class_access=class_access),
            argnames=["self", "name"],
            builtin=owner.__getattribute__,
        )
    )


def _getattr_function(context):
    receiver = context.get_pyname("object")
    if receiver is None:
        return pyobjects.get_unknown()
    value = receiver.get_object()
    if value is None or value == pyobjects.get_unknown():
        return pyobjects.get_unknown()
    owner = value if isinstance(value, pyobjects.AbstractClass) else value.get_type()
    for name, native in (
        ("__getattr__", None),
        ("__getattribute__", object.__getattribute__),
    ):
        hook = owner.get_attributes().get(name)
        if (
            hook is not None
            and getattr(hook.get_object(), "builtin", None) is not native
        ):
            return pyobjects.get_unknown()
    if (
        isinstance(value, pyobjects.AbstractClass)
        and value.get_metaclass() is not builtins["type"].get_object()
    ):
        return pyobjects.get_unknown()
    name = context.get_argument("name")
    default = context.get_pyname("default")
    if (
        default is not None
        and isinstance(name, LiteralString)
        and name.value not in value
    ):
        # Without access hooks, a member absent from the receiver's model
        # makes getattr() return its default.
        return default.get_object()
    return _attribute_access(
        _CallContext(
            ["self", "name"],
            arguments.ObjectArguments([receiver, context.get_pyname("name")]),
        ),
        class_access=isinstance(value, pyobjects.AbstractClass),
    )


class BuiltinObject(BuiltinClass):
    def __init__(self):
        super().__init__(
            object,
            {"__getattribute__": _attribute_access_name(object, class_access=False)},
        )


class NamespaceItems(pyobjects.PyObject):
    """Source-proven namespace pairs; undeclared members remain unknown."""

    def __init__(self, receiver, entries):
        super().__init__(get_list_type(get_tuple(get_str(), pyobjects.get_unknown())))
        self.receiver = receiver
        self.namespace = LiteralDict(get_str(), pyobjects.get_unknown(), entries)


def infer_runtime_call(function, args):
    if not has_runtime_call_model(function):
        return None
    supplied = args.get_pynames(["object", "predicate"])
    receiver = supplied[0] if supplied else None
    if receiver is None or len(supplied) > 1 and supplied[1] is not None:
        return pyobjects.get_unknown()
    value = receiver.get_object()
    if value is None or value == pyobjects.get_unknown():
        return pyobjects.get_unknown()
    owner = value if isinstance(value, pyobjects.AbstractClass) else value.get_type()
    members = owner.get_attributes()
    for name, native in (
        ("__getattr__", None),
        ("__getattribute__", object.__getattribute__),
        ("__dir__", object.__dir__),
    ):
        hook = members.get(name)
        if (
            hook is not None
            and getattr(hook.get_object(), "builtin", None) is not native
        ):
            return pyobjects.get_unknown()
    if (
        isinstance(value, pyobjects.AbstractClass)
        and value.get_metaclass() is not builtins["type"].get_object()
    ):
        return pyobjects.get_unknown()
    entries = {}
    for name in value.get_attributes():
        selected = _attribute_access(
            _CallContext(
                ["self", "name"],
                arguments.ObjectArguments(
                    [
                        receiver,
                        BuiltinName(LiteralString(name)),
                    ]
                ),
            ),
            class_access=isinstance(value, pyobjects.AbstractClass),
        )
        entries[name] = BuiltinName(selected)
    return NamespaceItems(receiver, entries)


def has_runtime_call_model(function):
    return _is_runtime_form(function, inspect.getmembers)


class BuiltinType(BuiltinClass):
    def __init__(self):
        constructor = BuiltinFunction(
            function=self._new_type,
            argnames=["metaclass", "name", "bases", "namespace"],
            parent=self,
        )
        super().__init__(
            type,
            {
                "__new__": BuiltinName(constructor),
                "__getattribute__": _attribute_access_name(type, class_access=True),
            },
        )

    @staticmethod
    def is_constructor(function):
        return (
            isinstance(function, BuiltinFunction)
            and getattr(function.function, "__func__", None) is BuiltinType._new_type
        )

    def _new_type(self, context):
        supplied = context.get_arguments(["metaclass", "name", "bases", "namespace"])
        if len(supplied) != 4:
            return pyobjects.get_unknown()
        metaclass, name, bases, namespace = supplied
        if not isinstance(metaclass, pyobjects.AbstractClass):
            return pyobjects.get_unknown()
        if self not in metaclass.get_mro():
            raise TypeError("type.__new__ requires a subtype of type")
        if not isinstance(name, LiteralString):
            return pyobjects.get_unknown()
        if bases is None or not isinstance(bases.get_type(), Tuple):
            return pyobjects.get_unknown()
        parents = bases.get_type().get_holding_objects()
        if any(base is None or base == pyobjects.get_unknown() for base in parents):
            return pyobjects.get_unknown()
        if any(not isinstance(base, pyobjects.AbstractClass) for base in parents):
            raise TypeError("type.__new__ bases must be classes")
        if not isinstance(namespace, LiteralDict) or namespace.entries is None:
            return pyobjects.get_unknown()
        winner = metaclass
        for base in parents:
            candidate = base.get_metaclass()
            if not isinstance(candidate, pyobjects.AbstractClass):
                return pyobjects.get_unknown()
            if winner in candidate.get_mro():
                winner = candidate
            elif candidate not in winner.get_mro():
                raise TypeError("metaclass conflict")
        if winner is not metaclass and not self.is_constructor(
            winner["__new__"].get_object()
        ):
            return pyobjects.get_unknown()
        result = pyobjects.ConstructedClass(
            name.value,
            parents or (builtins["object"].get_object(),),
            winner,
            namespace.entries,
        )
        result.get_mro()
        return result

    @staticmethod
    def type_of(value):
        """Resolve the one-argument operation without exposing kind markers."""
        if isinstance(value, pyobjects.AbstractClass):
            return value.get_metaclass()
        if isinstance(value, pyobjects.UnresolvedBase):
            return value
        if value is not None:
            value_type = value.get_type()
            if isinstance(value_type, BuiltinClass):
                if inspect.isclass(value_type.builtin):
                    return _runtime_class(value_type.builtin)
            elif isinstance(value_type, pyobjects.AbstractClass):
                return value_type
        return pyobjects.get_unknown()


def _infer_sequence_for_pyname(pyname):
    if pyname is None:
        return None
    seq = pyname.get_object()
    args = arguments.ObjectArguments([pyname])
    if "__iter__" in seq:
        obj = seq["__iter__"].get_object()
        if not isinstance(obj, pyobjects.AbstractFunction):
            return None
        iter = obj.get_returned_object(args)
        if iter is not None and "next" in iter:
            holding = iter["next"].get_object().get_returned_object(args)
            return holding


def _create_builtin(args, creator):
    passed = args.get_pynames(["sequence"])[0]
    if passed is None:
        holding = None
    else:
        holding = _infer_sequence_for_pyname(passed)
    if holding is not None:
        return creator(holding)
    else:
        return creator()


def _open_function(args):
    return _create_builtin(args, get_file)


def _range_function(args):
    return get_list()


def _reversed_function(args):
    return _create_builtin(args, get_iterator)


def _sorted_function(args):
    return _create_builtin(args, get_list)


def _super_function(args):
    passed_class, passed_self = args.get_arguments(["type", "self"])
    if passed_self is None:
        return passed_class
    else:
        # pyclass = passed_self.get_type()
        pyclass = passed_class
        if isinstance(pyclass, pyobjects.AbstractClass):
            mro = pyclass.get_consistent_mro()
            if mro is None:
                # Without a method resolution order, super() follows the
                # declared bases, the first one taking precedence.
                ancestors = pyclass.get_superclasses()
            else:
                ancestors = mro[1:]
            if ancestors:
                return pyobjects.PyObject(SuperType(pyclass, ancestors, passed_self))
        return passed_self


class SuperType(pyobjects.AbstractClass):
    """The type of ``super(cls, receiver)``

    Attribute lookups follow the method resolution order of `cls` past
    `cls` itself, as Python's ``super`` does.  Methods reached through it
    bind `receiver`, see `bound_receiver()`.

    """

    def __init__(self, pyclass, ancestors, receiver):
        super().__init__()
        self.pyclass = pyclass
        self.ancestors = ancestors
        self.receiver = receiver

    def get_name(self):
        return "super"

    def get_attributes(self):
        result = {}
        for ancestor in reversed(self.ancestors):
            result.update(ancestor._get_own_attributes())
        return result


def bound_receiver(pyobject):
    """Return the object a method called on `pyobject` binds

    A method reached through ``super(cls, receiver)`` binds `receiver`;
    every other object binds itself.

    """
    if isinstance(pyobject.get_type(), SuperType):
        return pyobject.get_type().receiver
    return pyobject


def _zip_function(args):
    args = args.get_pynames(["sequence"])
    objects = []
    for seq in args:
        if seq is None:
            holding = None
        else:
            holding = _infer_sequence_for_pyname(seq)
        objects.append(holding)
    tuple = get_tuple(*objects)
    return get_list(tuple)


def _enumerate_function(args):
    passed = args.get_pynames(["sequence"])[0]
    if passed is None:
        holding = None
    else:
        holding = _infer_sequence_for_pyname(passed)
    tuple = get_tuple(None, holding)
    return get_iterator(tuple)


def _iter_function(args):
    passed = args.get_pynames(["sequence"])[0]
    if passed is None:
        holding = None
    else:
        holding = _infer_sequence_for_pyname(passed)
    return get_iterator(holding)


def _map_function(context):
    supplied = context.get_pynames(["function", "iterable"])
    if len(supplied) < 2 or supplied[0] is None:
        return pyobjects.get_unknown()
    function, receiver = rope.base.evaluate.get_callable(supplied[0])
    if function is None:
        return pyobjects.get_unknown()
    items = [_infer_sequence_for_pyname(sequence) for sequence in supplied[1:]]
    if any(item is None or item == pyobjects.get_unknown() for item in items):
        return pyobjects.get_unknown()
    passed = arguments.ObjectArguments([BuiltinName(item) for item in items])
    if receiver is not None:
        passed = arguments.MixedArguments(receiver, passed, None)
    result = infer_runtime_call(function, passed)
    if result is None:
        result = function.get_returned_object(passed)
    return get_iterator(result)


def _next_function(context):
    supplied = context.get_pynames(["iterator"])
    if not supplied or supplied[0] is None:
        return pyobjects.get_unknown()
    result = _infer_sequence_for_pyname(supplied[0])
    return result if result is not None else pyobjects.get_unknown()


def _input_function(args):
    return get_str()


_initial_builtins = {
    "getattr": BuiltinName(
        BuiltinFunction(
            function=_getattr_function,
            argnames=["object", "name", "default"],
            builtin=getattr,
        )
    ),
    "list": BuiltinName(get_list_type()),
    "dict": BuiltinName(get_dict_type()),
    "tuple": BuiltinName(get_tuple_type()),
    "set": BuiltinName(get_set_type()),
    "str": BuiltinName(get_str_type()),
    "open": BuiltinName(BuiltinFunction(function=_open_function, builtin=open)),
    "range": BuiltinName(BuiltinFunction(function=_range_function, builtin=range)),
    "reversed": BuiltinName(
        BuiltinFunction(function=_reversed_function, builtin=reversed)
    ),
    "sorted": BuiltinName(BuiltinFunction(function=_sorted_function, builtin=sorted)),
    "super": BuiltinName(BuiltinFunction(function=_super_function, builtin=super)),
    "property": BuiltinName(
        BuiltinFunction(function=_property_function, builtin=property)
    ),
    "zip": BuiltinName(BuiltinFunction(function=_zip_function, builtin=zip)),
    "enumerate": BuiltinName(
        BuiltinFunction(function=_enumerate_function, builtin=enumerate)
    ),
    "object": BuiltinName(BuiltinObject()),
    "type": BuiltinName(BuiltinType()),
    "iter": BuiltinName(BuiltinFunction(function=_iter_function, builtin=iter)),
    "map": BuiltinName(
        BuiltinClass(
            map,
            {
                "__new__": BuiltinName(
                    BuiltinFunction(function=_map_function, builtin=map.__new__)
                )
            },
        )
    ),
    "next": BuiltinName(BuiltinFunction(function=_next_function, builtin=next)),
    "input": BuiltinName(BuiltinFunction(function=_input_function, builtin=input)),
}

builtins = BuiltinModule("builtins", initial=_initial_builtins)
