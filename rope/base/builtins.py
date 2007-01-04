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
            '__getslice__': BuiltinName(BuiltinFunction(pyobjects.PyObject(self))),
            'pop': BuiltinName(BuiltinFunction(self.holding)),
            '__iter__': BuiltinName(BuiltinFunction(Iterator(self.holding))),
            '__new__': BuiltinName(BuiltinFunction(function=self._new_list)),
            'append': BuiltinName(BuiltinFunction()),
            'count': BuiltinName(BuiltinFunction()),
            'extend': BuiltinName(BuiltinFunction()),
            'index': BuiltinName(BuiltinFunction()),
            'insert': BuiltinName(BuiltinFunction()),
            'remove': BuiltinName(BuiltinFunction()),
            'reverse': BuiltinName(BuiltinFunction()),
            'sort': BuiltinName(BuiltinFunction())}
    
    def _new_list(self, args):
        return _create_builtin(args, get_list)
    
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
            '__new__': BuiltinName(BuiltinFunction(function=self._new_dict)),
            'pop': BuiltinName(BuiltinFunction(self.values)),
            'get': BuiltinName(BuiltinFunction(self.keys)),
            'keys': BuiltinName(List(self.keys)),
            'values': BuiltinName(List(self.values)),
            'iterkeys': BuiltinName(Iterator(self.keys)),
            'itervalues': BuiltinName(Iterator(self.values)),
            'items': BuiltinName(List(item)),
            'iteritems': BuiltinName(Iterator(item)),
            'copy': BuiltinName(BuiltinFunction(pyobjects.PyObject(self))),
            'clear': BuiltinName(BuiltinFunction()),
            'has_key': BuiltinName(BuiltinFunction()),
            'popitem': BuiltinName(BuiltinFunction()),
            'setdefault': BuiltinName(BuiltinFunction()),
            'update': BuiltinName(BuiltinFunction())}
    
    def get_attributes(self):
        return self.attributes
    
    def _new_dict(self, args):
        def do_create(holding):
            type = holding.get_type()
            if isinstance(type, Tuple) and len(type.get_holding_objects()) == 2:
                return get_dict(*type.get_holding_objects())
        return _create_builtin(args, do_create)
    
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
            '__getslice__': BuiltinName(BuiltinFunction(pyobjects.PyObject(self))),
            '__new__': BuiltinName(BuiltinFunction(function=self._new_tuple)),
            '__iter__': BuiltinName(BuiltinFunction(Iterator(first)))}
    
    def get_holding_objects(self):
        return self.objects
    
    def get_attributes(self):
        return self.attributes

    def _new_tuple(self, args):
        return _create_builtin(args, get_tuple)

    
get_tuple = _create_builtin_getter(Tuple)
get_tuple_type = _create_builtin_type_getter(Tuple)


class Set(pyobjects.PyObject):

    def __init__(self, holding=None):
        super(Set, self).__init__(pyobjects.PyObject.get_base_type('Type'))
        self.holding = holding
        self.attributes = {
            'pop': BuiltinName(BuiltinFunction(self.holding)),
            '__iter__': BuiltinName(BuiltinFunction(Iterator(self.holding))),
            '__new__': BuiltinName(BuiltinFunction(function=self._new_set)),
            'add': BuiltinName(BuiltinFunction()),
            'copy': BuiltinName(BuiltinFunction(pyobjects.PyObject(self))),
            'difference': BuiltinName(BuiltinFunction(pyobjects.PyObject(self))),
            'intersection': BuiltinName(BuiltinFunction(pyobjects.PyObject(self))),
            'difference_update': BuiltinName(BuiltinFunction()),
            'symmetric_difference': BuiltinName(BuiltinFunction(pyobjects.PyObject(self))),
            'symmetric_difference_update': BuiltinName(BuiltinFunction()),
            'union': BuiltinName(BuiltinFunction(pyobjects.PyObject(self))),
            'discard': BuiltinName(BuiltinFunction()),
            'remove': BuiltinName(BuiltinFunction()),
            'issuperset': BuiltinName(BuiltinFunction()),
            'issubset': BuiltinName(BuiltinFunction()),
            'clear': BuiltinName(BuiltinFunction()),
            'update': BuiltinName(BuiltinFunction())}
    
    def get_attributes(self):
        return self.attributes
    
    def _new_set(self, args):
        return _create_builtin(args, get_set)
    
get_set = _create_builtin_getter(Set)
get_set_type = _create_builtin_type_getter(Set)


class Str(pyobjects.PyObject):
    
    def __init__(self):
        super(Str, self).__init__(pyobjects.PyObject.get_base_type('Type'))
        self_object = pyobjects.PyObject(self)
        self.attributes = {
            '__getitem__': BuiltinName(BuiltinFunction(self_object)),
            '__getslice__': BuiltinName(BuiltinFunction(self_object)),
            '__iter__': BuiltinName(BuiltinFunction(Iterator(self_object))),
            'captialize': BuiltinName(BuiltinFunction(self_object)),
            'center': BuiltinName(BuiltinFunction(self_object)),
            'count': BuiltinName(BuiltinFunction()),
            'decode': BuiltinName(BuiltinFunction(self_object)),
            'encode': BuiltinName(BuiltinFunction(self_object)),
            'endswith': BuiltinName(BuiltinFunction()),
            'expandtabs': BuiltinName(BuiltinFunction(self_object)),
            'find': BuiltinName(BuiltinFunction()),
            'index': BuiltinName(BuiltinFunction()),
            'isalnum': BuiltinName(BuiltinFunction()),
            'isalpha': BuiltinName(BuiltinFunction()),
            'isdigit': BuiltinName(BuiltinFunction()),
            'islower': BuiltinName(BuiltinFunction()),
            'isspace': BuiltinName(BuiltinFunction()),
            'istitle': BuiltinName(BuiltinFunction()),
            'isupper': BuiltinName(BuiltinFunction()),
            'join': BuiltinName(BuiltinFunction(self_object)),
            'ljust': BuiltinName(BuiltinFunction(self_object)),
            'lower': BuiltinName(BuiltinFunction(self_object)),
            'lstrip': BuiltinName(BuiltinFunction(self_object)),
            'replace': BuiltinName(BuiltinFunction(self_object)),
            'rfind': BuiltinName(BuiltinFunction()),
            'rindex': BuiltinName(BuiltinFunction()),
            'rjust': BuiltinName(BuiltinFunction(self_object)),
            'rsplit': BuiltinName(BuiltinFunction(get_list(self_object))),
            'rstrip': BuiltinName(BuiltinFunction(self_object)),
            'split': BuiltinName(BuiltinFunction(get_list(self_object))),
            'splitlines': BuiltinName(BuiltinFunction(get_list(self_object))),
            'startswith': BuiltinName(BuiltinFunction(self_object)),
            'strip': BuiltinName(BuiltinFunction(self_object)),
            'swapcase': BuiltinName(BuiltinFunction(self_object)),
            'title': BuiltinName(BuiltinFunction(self_object)),
            'translate': BuiltinName(BuiltinFunction(self_object)),
            'upper': BuiltinName(BuiltinFunction(self_object)),
            'zfill': BuiltinName(BuiltinFunction(self_object))}
    
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
    
    def __init__(self, returned=None, function=None):
        super(BuiltinFunction, self).__init__(
            pyobjects.PyObject.get_base_type('Function'))
        self.returned = returned
        self.function = function
    
    def get_returned_object(self, args=None):
        if self.function is not None:
            return self.function(args)
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

    def get_returned_object(self):
        return self.holding

def _infer_sequence_type(seq):
    if '__iter__' in seq.get_attributes():
        iter = seq.get_attribute('__iter__').get_object().\
               get_returned_object()
        if 'next' in iter.get_attributes():
            holding = iter.get_attribute('next').get_object().\
                      get_returned_object()
            return holding
    

def _create_builtin(args, creator):
    passed_pyname = args.get_arguments(['sequence'])[0]
    if passed_pyname is None:
        return None
    passed = passed_pyname.get_object()
    holding = _infer_sequence_type(passed)
    if holding is not None:
        return creator(holding)
