from rope.base.evaluate import ScopeNameFinder
from rope.base.exceptions import AttributeNotFoundError
from rope.base.pyobjects import PyClass, PyFunction


def get_superfunc(pyfunc):

    if not isinstance(pyfunc.parent, PyClass):
        return

    for cls in get_mro(pyfunc.parent)[1:]:
        try:
            superfunc = cls.get_attribute(pyfunc.get_name()).get_object()
        except AttributeNotFoundError:
            pass
        else:
            if isinstance(superfunc, PyFunction):
                return superfunc


def get_mro(pyclass):
    # FIXME: to use real mro() result
    l = [pyclass]
    for cls in l:
        for super_cls in cls.get_superclasses():
            if isinstance(super_cls, PyClass) and super_cls not in l:
                l.append(super_cls)
    return l


def resolve_type(type_name, pyobj):
    type_ = None
    if '.' not in type_name:
        try:
            type_ = pyobj.get_module().get_scope().get_name(type_name).get_object()
        except Exception:
            pass
    else:
        mod_name, attr_name = type_name.rsplit('.', 1)
        try:
            mod_finder = ScopeNameFinder(pyobj.get_module())
            mod = mod_finder._find_module(mod_name).get_object()
            type_ = mod.get_attribute(attr_name).get_object()
        except Exception:
            pass
    return type_
