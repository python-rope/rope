"""This module trys to support some of the builtin types and
functions.

"""

from rope.base import pynames
from rope.base import pyobjects
from rope.base import evaluate


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
        super(List, self).__init__(pyobjects.get_base_type('Type'))
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
        super(Dict, self).__init__(pyobjects.get_base_type('Type'))
        self.keys = keys
        self.values = values
        item = get_tuple(self.keys, self.values)
        self.attributes = {
            '__getitem__': BuiltinName(BuiltinFunction(self.values)),
            '__iter__': BuiltinName(BuiltinFunction(Iterator(self.keys))),
            '__new__': BuiltinName(BuiltinFunction(function=self._new_dict)),
            'pop': BuiltinName(BuiltinFunction(self.values)),
            'get': BuiltinName(BuiltinFunction(self.keys)),
            'keys': BuiltinName(BuiltinFunction(List(self.keys))),
            'values': BuiltinName(BuiltinFunction(List(self.values))),
            'iterkeys': BuiltinName(BuiltinFunction(Iterator(self.keys))),
            'itervalues': BuiltinName(BuiltinFunction(Iterator(self.values))),
            'items': BuiltinName(BuiltinFunction(List(item))),
            'iteritems': BuiltinName(BuiltinFunction(Iterator(item))),
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
        super(Tuple, self).__init__(pyobjects.get_base_type('Type'))
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
        super(Set, self).__init__(pyobjects.get_base_type('Type'))
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
        super(Str, self).__init__(pyobjects.get_base_type('Type'))
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
            pyobjects.get_base_type('Function'))
        self.returned = returned
        self.function = function

    def get_returned_object(self, args=None):
        if self.function is not None:
            return self.function(args)
        return self.returned


class Iterator(pyobjects.PyObject):

    def __init__(self, holding=None):
        super(Iterator, self).__init__(pyobjects.get_base_type('Type'))
        self.holding = holding
        self.attributes = {
            'next': BuiltinName(BuiltinFunction(self.holding)),
            '__iter__': BuiltinName(BuiltinFunction(self))}

    def get_attributes(self):
        return self.attributes

    def get_returned_object(self):
        return self.holding


class File(pyobjects.PyObject):
    
    def __init__(self):
        super(File, self).__init__(pyobjects.get_base_type('Type'))
        self_object = pyobjects.PyObject(self)
        str_object = get_str()
        str_list = get_list(get_str())
        self.attributes = {
            '__iter__': BuiltinName(BuiltinFunction(Iterator(str_object))),
            'close': BuiltinName(BuiltinFunction()),
            'flush': BuiltinName(BuiltinFunction()),
            'lineno': BuiltinName(BuiltinFunction()),
            'isatty': BuiltinName(BuiltinFunction()),
            'next': BuiltinName(BuiltinFunction(str_object)),
            'read': BuiltinName(BuiltinFunction(str_object)),
            'readline': BuiltinName(BuiltinFunction(str_object)),
            'readlines': BuiltinName(BuiltinFunction(str_list)),
            'seek': BuiltinName(BuiltinFunction()),
            'tell': BuiltinName(BuiltinFunction()),
            'truncate': BuiltinName(BuiltinFunction()),
            'write': BuiltinName(BuiltinFunction()),
            'writelines': BuiltinName(BuiltinFunction())}

    def get_attributes(self):
        return self.attributes

get_file = _create_builtin_getter(File)
get_file_type = _create_builtin_type_getter(File)


class Property(pyobjects.PyObject):

    def __init__(self, fget=None, fset=None, fdel=None, fdoc=None):
        super(Property, self).__init__(pyobjects.get_base_type('Type'))
        self._fget = fget
        self.attributes = {
            'fget': BuiltinName(BuiltinFunction()),
            'fset': BuiltinName(BuiltinFunction()),
            'fdel': BuiltinName(BuiltinFunction()),
            '__new__': BuiltinName(BuiltinFunction(function=_property_function))}

    def get_property_object(self):
        if self._fget:
            return self._fget.get_returned_object()

    def get_attributes(self):
        return self.attributes


def _property_function(args):
    parameters = args.get_arguments(['fget', 'fset', 'fdel', 'fdoc'])
    return pyobjects.PyObject(Property(parameters[0]))


class Lambda(pyobjects.PyObject):

    def __init__(self, node, scope):
        super(Lambda, self).__init__(pyobjects.get_base_type('Function'))
        self.node = node
        self.scope = scope

    def get_returned_object(self, args=None):
        result = evaluate.get_statement_result(
            self.scope, self.node.code)
        if result is not None:
            return result.get_object()
        else:
            return pyobjects.PyObject(pyobjects.get_base_type('Unknown'))

    def get_pattributes(self):
        return {}


def _infer_sequence_type(seq):
    if '__iter__' in seq.get_attributes():
        iter = seq.get_attribute('__iter__').get_object().\
               get_returned_object()
        if iter is not None and 'next' in iter.get_attributes():
            holding = iter.get_attribute('next').get_object().\
                      get_returned_object()
            return holding


def _create_builtin(args, creator):
    passed = args.get_arguments(['sequence'])[0]
    if passed is None:
        holding = None
    else:
        holding = _infer_sequence_type(passed)
    if holding is not None:
        return creator(holding)
    else:
        return creator()


def _range_function(args):
    return get_list()

def _reversed_function(args):
    return _create_builtin(args, Iterator)

def _sorted_function(args):
    return _create_builtin(args, List)

def _super_function(args):
    passed_class, passed_self = args.get_arguments(['type', 'self'])
    if passed_self is None:
        return passed_class
    else:
        return passed_self

def _zip_function(args):
    args = args.get_arguments(['sequence'])
    objects = []
    for seq in args:
        if seq is None:
            holding = None
        else:
            holding = _infer_sequence_type(seq)
        objects.append(holding)
    tuple = get_tuple(*objects)
    return get_list(tuple)

def _enumerate_function(args):
    passed = args.get_arguments(['sequence'])[0]
    if passed is None:
        holding = None
    else:
        holding = _infer_sequence_type(passed)
    tuple = get_tuple(None, holding)
    return Iterator(tuple)


builtins = {
    'list': BuiltinName(get_list_type()),
    'dict': BuiltinName(get_dict_type()),
    'tuple': BuiltinName(get_tuple_type()),
    'set': BuiltinName(get_set_type()),
    'str': BuiltinName(get_str_type()),
    'file': BuiltinName(get_file_type()),
    'open': BuiltinName(get_file_type()),
    'unicode': BuiltinName(get_str_type()),
    'range': BuiltinName(BuiltinFunction(function=_range_function)),
    'reversed': BuiltinName(BuiltinFunction(function=_reversed_function)),
    'sorted': BuiltinName(BuiltinFunction(function=_sorted_function)),
    'super': BuiltinName(BuiltinFunction(function=_super_function)),
    'property': BuiltinName(BuiltinFunction(function=_property_function)),
    'zip': BuiltinName(BuiltinFunction(function=_zip_function)),
    'enumerate': BuiltinName(BuiltinFunction(function=_enumerate_function))}
