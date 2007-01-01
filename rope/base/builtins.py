"""This module trys to support some of the builtin types and
functions.
"""

from rope.base import pyobjects
from rope.base import pynames


def _create_builtin_type_getter(cls):
    def _get_builtin(*args):
        if not hasattr(cls, '_generated'):
            cls._generated = {}
        if args not in cls._generated:
            cls._generated[args] = cls(*args)
        return cls._generated[args]
    return _get_builtin

def _create_builtin_getter(cls):
    type_getter = _create_builtin_type_getter(cls)
    def _get_builtin(*args):
        return pyobjects.PyObject(type_getter(*args))
    return _get_builtin


class List(pyobjects.PyObject):
    
    def __init__(self, holding=None):
        super(List, self).__init__(pyobjects.PyObject.get_base_type('Type'))
        self.holding = holding
        self.attributes = {
            '__getitem__': BuiltinName(BuiltinFunction(self.holding)),
            '__getslice__': BuiltinName(BuiltinFunction(self)),
            'pop': BuiltinName(BuiltinFunction(self.holding)),
            '__iter__': BuiltinName(BuiltinFunction(Iterator(self.holding))),
            'append': BuiltinName(BuiltinFunction()),
            'count': BuiltinName(BuiltinFunction()),
            'extend': BuiltinName(BuiltinFunction()),
            'index': BuiltinName(BuiltinFunction()),
            'insert': BuiltinName(BuiltinFunction()),
            'remove': BuiltinName(BuiltinFunction()),
            'reverse': BuiltinName(BuiltinFunction()),
            'sort': BuiltinName(BuiltinFunction())}
    
    def get_attributes(self):
        return self.attributes
    
get_list = _create_builtin_getter(List)
get_list_type = _create_builtin_type_getter(List)


class Dict(pyobjects.PyObject):
    
    def __init__(self, keys=None, values=None):
        super(Dict, self).__init__(pyobjects.PyObject.get_base_type('Type'))
        self.keys = keys
        self.values = values
        item = get_tuple(self.keys, self.values)
        self.attributes = {
            '__getitem__': BuiltinName(BuiltinFunction(self.values)),
            '__iter__': BuiltinName(BuiltinFunction(Iterator(self.keys))),
            'pop': BuiltinName(BuiltinFunction(self.values)),
            'get': BuiltinName(BuiltinFunction(self.keys)),
            'keys': BuiltinName(List(self.keys)),
            'values': BuiltinName(List(self.values)),
            'iterkeys': BuiltinName(Iterator(self.keys)),
            'itervalues': BuiltinName(Iterator(self.values)),
            'items': BuiltinName(List(item)),
            'iteritems': BuiltinName(Iterator(item)),
            'copy': BuiltinName(BuiltinFunction(self)),
            'clear': BuiltinName(BuiltinFunction()),
            'has_key': BuiltinName(BuiltinFunction()),
            'popitem': BuiltinName(BuiltinFunction()),
            'setdefault': BuiltinName(BuiltinFunction()),
            'update': BuiltinName(BuiltinFunction())}
    
    def get_attributes(self):
        return self.attributes
    
get_dict = _create_builtin_getter(Dict)
get_dict_type = _create_builtin_type_getter(Dict)


class Tuple(pyobjects.PyObject):
    
    def __init__(self, *objects):
        super(Tuple, self).__init__(pyobjects.PyObject.get_base_type('Type'))
        self.objects = objects
        first = None
        if objects:
            first = objects[0]
        self.attributes = {
            '__getitem__': BuiltinName(BuiltinFunction(first)),
            '__getslice__': BuiltinName(BuiltinFunction(self)),
            '__iter__': BuiltinName(BuiltinFunction(Iterator(first)))}
    
    def get_holding_objects(self):
        return self.objects
    
    def get_attributes(self):
        return self.attributes

get_tuple = _create_builtin_getter(Tuple)
get_tuple_type = _create_builtin_type_getter(Tuple)


class Set(pyobjects.PyObject):

    def __init__(self, holding=None):
        super(Set, self).__init__(pyobjects.PyObject.get_base_type('Type'))
        self.holding = holding
        self.attributes = {
            'pop': BuiltinName(BuiltinFunction(self.holding)),
            '__iter__': BuiltinName(BuiltinFunction(Iterator(self.holding))),
            'add': BuiltinName(BuiltinFunction()),
            'copy': BuiltinName(BuiltinFunction(self)),
            'difference': BuiltinName(BuiltinFunction(self)),
            'intersection': BuiltinName(BuiltinFunction(self)),
            'difference_update': BuiltinName(BuiltinFunction()),
            'symmetric_difference': BuiltinName(BuiltinFunction(self)),
            'symmetric_difference_update': BuiltinName(BuiltinFunction()),
            'union': BuiltinName(BuiltinFunction(self)),
            'discard': BuiltinName(BuiltinFunction()),
            'remove': BuiltinName(BuiltinFunction()),
            'issuperset': BuiltinName(BuiltinFunction()),
            'issubset': BuiltinName(BuiltinFunction()),
            'clear': BuiltinName(BuiltinFunction()),
            'update': BuiltinName(BuiltinFunction())}
    
    def get_attributes(self):
        return self.attributes
    
get_set = _create_builtin_getter(Set)
get_set_type = _create_builtin_type_getter(Set)


class Str(pyobjects.PyObject):
    
    def __init__(self):
        super(Str, self).__init__(pyobjects.PyObject.get_base_type('Type'))
        self.attributes = {
            '__getitem__': BuiltinName(BuiltinFunction(self)),
            '__getslice__': BuiltinName(BuiltinFunction(self)),
            '__iter__': BuiltinName(BuiltinFunction(Iterator(self))),
            'captialize': BuiltinName(BuiltinFunction(self)),
            'center': BuiltinName(BuiltinFunction(self)),
            'count': BuiltinName(BuiltinFunction()),
            'decode': BuiltinName(BuiltinFunction(self)),
            'encode': BuiltinName(BuiltinFunction(self)),
            'endswith': BuiltinName(BuiltinFunction()),
            'expandtabs': BuiltinName(BuiltinFunction(self)),
            'find': BuiltinName(BuiltinFunction()),
            'index': BuiltinName(BuiltinFunction()),
            'isalnum': BuiltinName(BuiltinFunction()),
            'isalpha': BuiltinName(BuiltinFunction()),
            'isdigit': BuiltinName(BuiltinFunction()),
            'islower': BuiltinName(BuiltinFunction()),
            'isspace': BuiltinName(BuiltinFunction()),
            'istitle': BuiltinName(BuiltinFunction()),
            'isupper': BuiltinName(BuiltinFunction()),
            'join': BuiltinName(BuiltinFunction(self)),
            'ljust': BuiltinName(BuiltinFunction(self)),
            'lower': BuiltinName(BuiltinFunction(self)),
            'lstrip': BuiltinName(BuiltinFunction(self)),
            'replace': BuiltinName(BuiltinFunction(self)),
            'rfind': BuiltinName(BuiltinFunction()),
            'rindex': BuiltinName(BuiltinFunction()),
            'rjust': BuiltinName(BuiltinFunction(self)),
            'rsplit': BuiltinName(BuiltinFunction(self)),
            'rstrip': BuiltinName(BuiltinFunction(self)),
            'split': BuiltinName(BuiltinFunction(self)),
            'splitlines': BuiltinName(BuiltinFunction(self)),
            'startswith': BuiltinName(BuiltinFunction(self)),
            'strip': BuiltinName(BuiltinFunction(self)),
            'swapcase': BuiltinName(BuiltinFunction(self)),
            'title': BuiltinName(BuiltinFunction(self)),
            'translate': BuiltinName(BuiltinFunction(self)),
            'upper': BuiltinName(BuiltinFunction(self)),
            'zfill': BuiltinName(BuiltinFunction(self))}
    
    def get_attributes(self):
        return self.attributes

get_str = _create_builtin_getter(Str)
get_str_type = _create_builtin_type_getter(Str)


class BuiltinName(pynames.PyName):
    
    def __init__(self, pyobject):
        self.pyobject = pyobject
    
    def get_object(self):
        return self.pyobject


class BuiltinFunction(pyobjects.PyObject):
    
    def __init__(self, returned=None):
        super(BuiltinFunction, self).__init__(
            pyobjects.PyObject.get_base_type('Function'))
        self.returned = returned
    
    def _get_returned_object(self):
        return self.returned


class Iterator(pyobjects.PyObject):

    def __init__(self, holding=None):
        super(Iterator, self).__init__(pyobjects.PyObject.get_base_type('Type'))
        self.holding = holding
        self.attributes = {
            'next': BuiltinName(BuiltinFunction(self.holding)),
            '__iter__': BuiltinName(BuiltinFunction(self))}
    
    def get_attributes(self):
        return self.attributes

    def _get_returned_object(self):
        return self.holding

