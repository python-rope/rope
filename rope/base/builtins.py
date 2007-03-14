"""This module trys to support some of the builtin types and
functions.

"""
import __builtin__
import inspect

from rope.base import pynames, pyobjects, evaluate


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


class BuiltinClass(pyobjects.AbstractClass):

    def __init__(self, builtin, attributes):
        super(BuiltinClass, self).__init__()
        self.builtin = builtin
        self.attributes = attributes

    def get_attributes(self):
        return self.attributes

    def get_doc(self):
        return self.builtin.__doc__

    def get_name(self):
        return self.builtin.__name__


class List(BuiltinClass):

    def __init__(self, holding=None):
        self.holding = holding
        attributes = {}
        def add(name, returned=None, function=None):
            attributes[name] = BuiltinName(
                BuiltinFunction(returned=returned, function=function,
                                builtin=getattr(list, name)))

        add('__getitem__', self.holding)
        add('__getslice__', pyobjects.PyObject(self))
        add('pop', self.holding)
        add('__iter__', Iterator(self.holding))
        add('__new__', function=self._new_list)
        for method in ['append', 'count', 'extend', 'index', 'insert',
                       'remove', 'reverse', 'sort']:
            add(method)
        super(List, self).__init__(list, attributes)

    def _new_list(self, args):
        return _create_builtin(args, get_list)


get_list = _create_builtin_getter(List)
get_list_type = _create_builtin_type_getter(List)


class Dict(BuiltinClass):

    def __init__(self, keys=None, values=None):
        self.keys = keys
        self.values = values
        item = get_tuple(self.keys, self.values)
        attributes = {}
        def add(name, returned=None, function=None):
            attributes[name] = BuiltinName(
                BuiltinFunction(returned=returned, function=function,
                                builtin=getattr(dict, name)))
        add('__getitem__', self.values)
        add('__iter__', Iterator(self.keys))
        add('__new__', function=self._new_dict)
        add('pop', self.values)
        add('get', self.keys)
        add('keys', List(self.keys))
        add('values', List(self.values))
        add('iterkeys', Iterator(self.keys))
        add('itervalues', Iterator(self.values))
        add('items', List(item))
        add('iteritems', Iterator(item))
        add('copy', pyobjects.PyObject(self))
        add('popitem', item)
        for method in ['clear', 'has_key', 'setdefault', 'update']:
            add(method)
        super(Dict, self).__init__(dict, attributes)

    def _new_dict(self, args):
        def do_create(holding):
            type = holding.get_type()
            if isinstance(type, Tuple) and len(type.get_holding_objects()) == 2:
                return get_dict(*type.get_holding_objects())
        return _create_builtin(args, do_create)

get_dict = _create_builtin_getter(Dict)
get_dict_type = _create_builtin_type_getter(Dict)


class Tuple(BuiltinClass):

    def __init__(self, *objects):
        self.objects = objects
        first = None
        if objects:
            first = objects[0]
        attributes = {
            '__getitem__': BuiltinName(BuiltinFunction(first)),
            '__getslice__': BuiltinName(BuiltinFunction(pyobjects.PyObject(self))),
            '__new__': BuiltinName(BuiltinFunction(function=self._new_tuple)),
            '__iter__': BuiltinName(BuiltinFunction(Iterator(first)))}
        super(Tuple, self).__init__(tuple, attributes)

    def get_holding_objects(self):
        return self.objects

    def _new_tuple(self, args):
        return _create_builtin(args, get_tuple)


get_tuple = _create_builtin_getter(Tuple)
get_tuple_type = _create_builtin_type_getter(Tuple)


class Set(BuiltinClass):

    def __init__(self, holding=None):
        self.holding = holding
        attributes = {}
        def add(name, returned=None, function=None):
            attributes[name] = BuiltinName(
                BuiltinFunction(returned=returned, function=function,
                                builtin=getattr(set, name)))
        add('pop', self.holding)
        add('__iter__', Iterator(self.holding))
        add('__new__', function=self._new_set)

        self_methods = ['copy', 'difference', 'intersection',
                        'symmetric_difference', 'union']
        for method in self_methods:
            add(method, pyobjects.PyObject(self))
        normal_methods = ['add', 'symmetric_difference_update',
                          'difference_update', 'discard', 'remove',
                          'issuperset', 'issubset', 'clear', 'update']
        for method in normal_methods:
            add(method)
        super(Set, self).__init__(set, attributes)

    def _new_set(self, args):
        return _create_builtin(args, get_set)

get_set = _create_builtin_getter(Set)
get_set_type = _create_builtin_type_getter(Set)


class Str(BuiltinClass):

    def __init__(self):
        self_object = pyobjects.PyObject(self)
        attributes = {}
        def add(name, returned=None, function=None):
            builtin = getattr(str, name, None)
            attributes[name] = BuiltinName(
                BuiltinFunction(returned=returned, function=function, builtin=builtin))
        add('__iter__', Iterator(self_object))

        self_methods = ['__getitem__', '__getslice__', 'captialize', 'center',
                        'decode', 'encode', 'expandtabs', 'join', 'ljust',
                        'lower', 'lstrip', 'replace', 'rjust', 'rstrip', 'strip',
                        'swapcase', 'title', 'translate', 'upper', 'zfill']
        for method in self_methods:
            add(method, self_object)

        for method in ['rsplit', 'split', 'splitlines']:
            add(method, get_list(self_object))

        for method in ['count', 'endswith', 'find', 'index', 'isalnum',
                       'isalpha', 'isdigit', 'islower', 'isspace', 'istitle',
                       'isupper', 'rfind', 'rindex', 'startswith']:
            add(method)
        super(Str, self).__init__(str, attributes)

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

class BuiltinFunction(pyobjects.AbstractFunction):

    def __init__(self, returned=None, function=None, builtin=None):
        super(BuiltinFunction, self).__init__()
        self.returned = returned
        self.function = function
        self.builtin = builtin

    def get_returned_object(self, args=None):
        if self.function is not None:
            return self.function(args)
        return self.returned

    def get_doc(self):
        if self.builtin:
            return self.builtin.__doc__

    def get_name(self):
        if self.builtin:
            return self.builtin.__name__


class Iterator(pyobjects.AbstractClass):

    def __init__(self, holding=None):
        super(Iterator, self).__init__()
        self.holding = holding
        self.attributes = {
            'next': BuiltinName(BuiltinFunction(self.holding)),
            '__iter__': BuiltinName(BuiltinFunction(self))}

    def get_attributes(self):
        return self.attributes

    def get_returned_object(self):
        return self.holding

get_iterator = _create_builtin_getter(Iterator)


class Generator(pyobjects.AbstractClass):

    def __init__(self, holding=None):
        super(Generator, self).__init__()
        self.holding = holding
        self.attributes = {
            'next': BuiltinName(BuiltinFunction(self.holding)),
            '__iter__': BuiltinName(BuiltinFunction(get_iterator(self.holding))),
            'close': BuiltinName(BuiltinFunction()),
            'send': BuiltinName(BuiltinFunction()),
            'throw': BuiltinName(BuiltinFunction())}

    def get_attributes(self):
        return self.attributes

    def get_returned_object(self):
        return self.holding

get_generator = _create_builtin_getter(Generator)


class File(BuiltinClass):

    def __init__(self):
        self_object = pyobjects.PyObject(self)
        str_object = get_str()
        str_list = get_list(get_str())
        attributes = {}
        def add(name, returned=None, function=None):
            builtin = getattr(file, name, None)
            attributes[name] = BuiltinName(
                BuiltinFunction(returned=returned, function=function,
                                builtin=builtin))
        add('__iter__', get_iterator(str_object))
        for method in ['next', 'read', 'readline', 'readlines']:
            add(method, str_list)
        for method in ['close', 'flush', 'lineno', 'isatty', 'seek', 'tell',
                       'truncate', 'write', 'writelines']:
            add(method)
        super(File, self).__init__(file, attributes)


get_file = _create_builtin_getter(File)
get_file_type = _create_builtin_type_getter(File)


class Property(BuiltinClass):

    def __init__(self, fget=None, fset=None, fdel=None, fdoc=None):
        self._fget = fget
        self._fdoc = fdoc
        attributes = {
            'fget': BuiltinName(BuiltinFunction()),
            'fset': BuiltinName(BuiltinFunction()),
            'fdel': BuiltinName(BuiltinFunction()),
            '__new__': BuiltinName(BuiltinFunction(function=_property_function))}
        super(Property, self).__init__(property, attributes)

    def get_property_object(self):
        if isinstance(self._fget, pyobjects.AbstractFunction):
            return self._fget.get_returned_object()


def _property_function(args):
    parameters = args.get_arguments(['fget', 'fset', 'fdel', 'fdoc'])
    return pyobjects.PyObject(Property(parameters[0]))


class Lambda(pyobjects.AbstractFunction):

    def __init__(self, node, scope):
        super(Lambda, self).__init__()
        self.node = node
        self.scope = scope

    def get_returned_object(self, args=None):
        result = evaluate.get_statement_result(
            self.scope, self.node.code)
        if result is not None:
            return result.get_object()
        else:
            return pyobjects.get_unknown()

    def get_pattributes(self):
        return {}


class BuiltinObject(BuiltinClass):

    def __init__(self):
        super(BuiltinObject, self).__init__(object, {})


class BuiltinType(BuiltinClass):

    def __init__(self):
        super(BuiltinType, self).__init__(type, {})


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
        pyclass = passed_self.get_type()
        if isinstance(pyclass, pyobjects.AbstractClass):
            supers = pyclass.get_superclasses()
            if supers:
                return pyobjects.PyObject(supers[0])
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

def _iter_function(args):
    passed = args.get_arguments(['sequence'])[0]
    if passed is None:
        holding = None
    else:
        holding = _infer_sequence_type(passed)
    return Iterator(holding)


builtins = {
    'list': BuiltinName(get_list_type()),
    'dict': BuiltinName(get_dict_type()),
    'tuple': BuiltinName(get_tuple_type()),
    'set': BuiltinName(get_set_type()),
    'str': BuiltinName(get_str_type()),
    'file': BuiltinName(get_file_type()),
    'open': BuiltinName(get_file_type()),
    'unicode': BuiltinName(get_str_type()),
    'range': BuiltinName(BuiltinFunction(function=_range_function, builtin=range)),
    'reversed': BuiltinName(BuiltinFunction(function=_reversed_function, builtin=reversed)),
    'sorted': BuiltinName(BuiltinFunction(function=_sorted_function, builtin=sorted)),
    'super': BuiltinName(BuiltinFunction(function=_super_function, builtin=super)),
    'property': BuiltinName(BuiltinFunction(function=_property_function, builtin=property)),
    'zip': BuiltinName(BuiltinFunction(function=_zip_function, builtin=zip)),
    'enumerate': BuiltinName(BuiltinFunction(function=_enumerate_function, builtin=enumerate)),
    'object': BuiltinName(BuiltinObject()),
    'type': BuiltinName(BuiltinType()),
    'iter': BuiltinName(BuiltinFunction(function=_iter_function, builtin=iter))}


for name in dir(__builtin__):
    if name not in builtins and name not in ['None']:
        obj = getattr(__builtin__, name)
        if inspect.isclass(obj):
            builtins[name] = BuiltinName(BuiltinClass(obj, {}))
        else:
            builtins[name] = BuiltinName(BuiltinFunction(builtin=obj))
