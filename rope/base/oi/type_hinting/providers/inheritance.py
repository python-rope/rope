from rope.base.oi.type_hinting.providers import interfaces
from rope.base.oi.type_hinting.utils import get_superfunc, get_mro


class ParamProvider(interfaces.IParamProvider):

    def __init__(self, delegate):
        """
        :type delegate: rope.base.oi.type_hinting.providers.interfaces.IParamProvider
        """
        self._delegate = delegate

    def __call__(self, pyfunc, param_name):
        """
        :type pyfunc: rope.base.pyobjectsdef.PyFunction
        :type param_name: str
        :rtype: rope.base.pyobjects.PyDefinedObject | rope.base.pyobjects.PyObject
        """
        superfunc = pyfunc
        while superfunc:
            result = self._delegate(superfunc, param_name)
            if result:
                return result
            superfunc = get_superfunc(superfunc)


class ReturnProvider(interfaces.IReturnProvider):

    def __init__(self, delegate):
        """
        :type delegate: rope.base.oi.type_hinting.providers.interfaces.IReturnProvider
        """
        self._delegate = delegate

    def __call__(self, pyfunc):
        """
        :type pyfunc: rope.base.pyobjectsdef.PyFunction
        :rtype: rope.base.pyobjects.PyDefinedObject | rope.base.pyobjects.PyObject
        """
        superfunc = pyfunc
        while superfunc:
            result = self._delegate(superfunc)
            if result:
                return result
            superfunc = get_superfunc(superfunc)


class AttrProvider(interfaces.IAttrProvider):

    def __init__(self, delegate):
        """
        :type delegate: rope.base.oi.type_hinting.providers.interfaces.IAttrProvider
        """
        self._delegate = delegate

    def __call__(self, pyclass, attr_name):
        """
        :type pyclass: rope.base.pyobjectsdef.PyClass
        :type attr_name: str
        :rtype: rope.base.pyobjects.PyDefinedObject | rope.base.pyobjects.PyObject
        """
        for supercls in get_mro(pyclass):
            result = self._delegate(supercls, attr_name)
            if result:
                return result
