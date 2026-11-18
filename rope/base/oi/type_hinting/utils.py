from __future__ import annotations

import collections.abc
import logging
import sys
import types
import typing
from typing import TYPE_CHECKING, Optional, Union

import rope.base.utils as base_utils
from rope.base import builtins, evaluate, pyobjects
from rope.base.exceptions import AttributeNotFoundError
from rope.base.pyobjects import (
    AbstractClass,
    PyClass,
    PyDefinedObject,
    PyFunction,
    PyObject,
)


def hint_instance(value):
    """Materialize a class hint without wrapping a modeled instance twice."""
    if isinstance(value, AbstractClass) or value.get_type() is value:
        return PyObject(value)
    return value


def _hint_binding_value(binding):
    """Authenticate stdlib declarations before assigning their native models."""
    value = binding.get_object()
    if isinstance(value, pyobjects.SampledValue):
        return None
    module, line = binding.get_definition_location()
    resource = module.get_resource() if module is not None else None
    trusted = (typing, collections.abc, sys.modules.get("_collections_abc"))
    if resource is not None and any(
        base_utils.same_file_path(resource.real_path, item.__file__)
        for item in trusted
        if item is not None
    ):
        declared = module.get_scope().get_name("Sequence")
        if declared.get_definition_location() == (module, line):
            return builtins.get_sequence_type()
    if resource is not None and base_utils.same_file_path(
        resource.real_path, types.__file__
    ):
        declared = module.get_scope().get_name("NoneType")
        if declared.get_definition_location() == (module, line):
            return builtins._runtime_class(type(None))
    if isinstance(value, (builtins.BuiltinClass, builtins.BuiltinUnknown)) and (
        value.builtin is collections.abc.Sequence or value.builtin is typing.Sequence
    ):
        return builtins.get_sequence_type()
    return _hint_value(value)


def _hint_value(value):
    if isinstance(value, builtins.GenericAlias):
        origin = _hint_value(value.origin)
        arguments = tuple(_hint_value(argument) for argument in value.arguments)
        if origin is None or any(
            not isinstance(argument, AbstractClass) for argument in arguments
        ):
            return None
        return parametrize_type(origin, *arguments)
    return value


def get_super_func(pyfunc):
    if not isinstance(pyfunc.parent, PyClass):
        return

    for cls in _source_ancestors(pyfunc.parent):
        attributes = cls._get_own_attributes()
        if pyfunc.get_name() in attributes:
            superfunc = attributes[pyfunc.get_name()].get_object()
            if isinstance(superfunc, PyFunction):
                return superfunc


def get_super_assignment(pyname):
    """
    :type pyname: rope.base.pynamesdef.AssignedName
    :type: rope.base.pynamesdef.AssignedName
    """
    try:
        pyclass, attr_name = get_class_with_attr_name(pyname)
    except TypeError:
        return
    else:
        for super_pyclass in _source_ancestors(pyclass):
            attributes = super_pyclass._get_own_attributes()
            if attr_name in attributes:
                return attributes[attr_name]


def get_class_with_attr_name(pyname):
    """
    :type pyname: rope.base.pynamesdef.AssignedName
    :return: rope.base.pyobjectsdef.PyClass, str
    :rtype: tuple
    """
    import rope.base.pynamesdef

    if not isinstance(pyname, rope.base.pynamesdef.AssignedName):
        return None
    lineno = get_lineno_for_node(pyname.assignments[0].ast_node)
    holding_scope = pyname.module.get_scope().get_inner_scope_for_line(lineno)
    pyobject = holding_scope.pyobject
    if isinstance(pyobject, PyClass):
        pyclass = pyobject
    elif isinstance(pyobject, PyFunction) and isinstance(pyobject.parent, PyClass):
        pyclass = pyobject.parent
    else:
        return
    for name, attr in pyclass.get_attributes().items():
        if attr is pyname:
            return (pyclass, name)


def get_lineno_for_node(assign_node):
    if hasattr(assign_node, "lineno") and assign_node.lineno is not None:
        return assign_node.lineno
    return 1


def _source_ancestors(pyclass):
    """Return the ancestors with source, in method resolution order

    A hierarchy Python refuses to create has no method resolution order;
    its ancestors follow the bases as `get_mro()` lists them.

    """
    mro = pyclass.get_consistent_mro()
    if mro is None:
        mro = get_mro(pyclass)
    return [cls for cls in mro[1:] if isinstance(cls, PyClass)]


def get_mro(pyclass):
    # FIXME: to use real mro() result
    class_list = [pyclass]
    for cls in class_list:
        for super_cls in cls.get_superclasses():
            if isinstance(super_cls, PyClass) and super_cls not in class_list:
                class_list.append(super_cls)
    return class_list


def _source_ancestors(pyclass):
    """Return the ancestors with source, in method resolution order

    A hierarchy Python refuses to create has no method resolution order;
    its ancestors follow the bases as `get_mro()` lists them.

    """
    from rope.base.pyobjectsdef import _inheritance_order

    return [cls for cls in _inheritance_order(pyclass)[1:] if isinstance(cls, PyClass)]


def get_hint_scope(pyobject):
    from rope.base.sourcebindings import AnnotationEnvironment

    owner = pyobject.parent if isinstance(pyobject, PyFunction) else pyobject
    scope = owner.get_scope()
    if isinstance(scope, AnnotationEnvironment) and scope.policy.mode == "eager":
        return evaluate.SourceValueScope(scope, scope, {}, source_epoch=scope.node)
    if isinstance(scope, AnnotationEnvironment) and scope.policy.mode == "lazy":
        # PEP 649 evaluates the annotation after its module has executed.
        module = owner.get_module()
        return evaluate.SourceValueScope(
            scope, scope, {}, source_epoch=module.get_ast()
        )
    return scope


def union_type(alternatives):
    """Preserve PEP 604 only when native type operators govern both operands."""
    for alternative in alternatives:
        if not isinstance(alternative, AbstractClass):
            return None
        metaclass = alternative.get_metaclass()
        if not isinstance(metaclass, AbstractClass):
            return None
        for name in ("__or__", "__ror__"):
            if name not in metaclass:
                return None
            method = metaclass[name].get_object()
            if not isinstance(
                method, builtins.BuiltinFunction
            ) or method.builtin is not getattr(type, name):
                return None
    from rope.base.oi.type_hinting.evaluate import UnionType

    return UnionType(alternatives)


def resolve_type(
    type_name: str,
    pyobject: Union[PyDefinedObject, PyObject],
) -> Optional[Union[PyDefinedObject, PyObject]]:
    """
    Find proper type object from its name.
    """
    if sys.version_info < (3, 13):
        deprecated_aliases = {"collections": "collections.abc"}
    else:
        deprecated_aliases = {"collections": "_collections_abc"}
    ret_type = None
    logging.debug(f"Looking for {type_name}")
    scope = get_hint_scope(pyobject)
    root = type_name.partition(".")[0]
    root_binding = scope.lookup(root)
    if root_binding is not None:
        binding = evaluate.eval_str(scope, type_name)
        return _hint_binding_value(binding) if binding is not None else None
    if "." in type_name:
        mod_name, attr_name = type_name.rsplit(".", 1)
        try:
            mod_finder = evaluate.ScopeNameFinder(pyobject.get_module())
            mod = mod_finder._find_module(mod_name).get_object()
            ret_type = _hint_binding_value(mod.get_attribute(attr_name))
        except AttributeNotFoundError:
            if mod_name in deprecated_aliases:
                try:
                    logging.debug(
                        f"Looking for {attr_name} in {deprecated_aliases[mod_name]}"
                    )
                    mod = mod_finder._find_module(
                        deprecated_aliases[mod_name]
                    ).get_object()
                    ret_type = mod.get_attribute(attr_name).get_object()
                except AttributeNotFoundError:
                    logging.exception(f"Cannot resolve type {attr_name} in {dir(mod)}")
    logging.debug("ret_type = %s", ret_type)
    return ret_type


def is_annotated_type(pyobject):
    return builtins._is_runtime_class(
        pyobject, typing.Annotated
    ) or builtins._is_runtime_form(pyobject, typing.Annotated)


class ParametrizeType:
    _supported_mapping = {
        "builtins.list": "rope.base.builtins.get_list",
        "builtins.tuple": "rope.base.builtins.get_tuple",
        "builtins.set": "rope.base.builtins.get_set",
        "builtins.dict": "rope.base.builtins.get_dict",
        "_collections_abc.Iterable": "rope.base.builtins.get_iterator",
        "_collections_abc.Iterator": "rope.base.builtins.get_iterator",
        "collections.abc.Iterable": "rope.base.builtins.get_iterator",  # Python3.3
        "collections.abc.Iterator": "rope.base.builtins.get_iterator",  # Python3.3
    }

    def __call__(self, pyobject, *args, **kwargs):
        """
        :type pyobject: rope.base.pyobjects.PyObject
        :rtype: rope.base.pyobjects.PyDefinedObject | rope.base.pyobjects.PyObject or None
        """
        if is_annotated_type(pyobject):
            return args[0] if len(args) >= 2 else None
        if builtins._is_runtime_form(pyobject, typing.Optional):
            if len(args) != 1 or args[0] is None:
                return None
            from rope.base.oi.type_hinting.evaluate import UnionType

            return UnionType((args[0], builtins._runtime_class(type(None))))
        if isinstance(pyobject, PyFunction):
            return None
        type_factory = self._get_type_factory(pyobject)
        if type_factory:
            parametrized_type = type_factory(
                *(
                    hint_instance(argument) if argument is not None else None
                    for argument in args
                ),
                **kwargs,
            )
            if parametrized_type:
                return parametrized_type.get_type()
        return None

    def _get_type_factory(self, pyobject):
        if isinstance(pyobject, builtins.Sequence):
            return builtins.get_sequence
        module = pyobject.get_module()
        if module is None:
            return None
        type_str = "{}.{}".format(module.get_name(), pyobject.get_name())
        if type_str in self._supported_mapping:
            return base_utils.resolve(self._supported_mapping[type_str])


parametrize_type = ParametrizeType()
