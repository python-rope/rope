"""This module trys to support builtin types and functions."""
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


class BuiltinFunction(pyobjects.AbstractFunction):

    def __init__(self, returned=None, function=None, builtin=None, argnames=[]):
        super(BuiltinFunction, self).__init__()
        self.argnames = argnames
        self.returned = returned
        self.function = function
        self.builtin = builtin

    def get_returned_object(self, args):
        if self.function is not None:
            return self.function(_CallContext(self.argnames, args))
        else:
            return self.returned

    def get_doc(self):
        if self.builtin:
            return self.builtin.__doc__

    def get_name(self):
        if self.builtin:
            return self.builtin.__name__


class _CallContext(object):

    def __init__(self, argnames, args):
        self.argnames = argnames
        self.args = args

    def _get_scope_and_pyname(self, pyname):
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
                    if scope.get_name(current) is pyname:
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
            return pymodule.pycore.call_info.get_per_name(scope, name)
        return None

    def save_per_name(self, value):
        if self.args is None:
            return None
        pyname = self.args.get_instance_pyname()
        scope, name = self._get_scope_and_pyname(pyname)
        if name is not None:
            pymodule = pyname.get_definition_location()[0]
            pymodule.pycore.call_info.save_per_name(scope, name, value)


class _AttributeCollector(object):

    def __init__(self, type):
        self.attributes = {}
        self.type = type

    def __call__(self, name, returned=None, function=None, argnames=['self']):
        self.attributes[name] = BuiltinName(
            BuiltinFunction(returned=returned, function=function,
                            argnames=argnames,
                            builtin=getattr(self.type, name)))

    def __setitem__(self, name, value):
        self.attributes[name] = value


class List(BuiltinClass):

    def __init__(self, holding=None):
        self.holding = holding
        collector = _AttributeCollector(list)

        collector('__iter__', function=self._iterator_get)
        collector('__new__', function=self._new_list)
        for method in ['count', 'index', 'remove', 'reverse', 'sort']:
            collector(method)

        # Adding methods
        collector('append', function=self._list_add, argnames=['self', 'value'])
        collector('__setitem__', function=self._list_add,
                  argnames=['self', 'index', 'value'])
        collector('insert', function=self._list_add,
                  argnames=['self', 'index', 'value'])
        collector('extend', function=self._self_set, 
                  argnames=['self', 'iterable'])

        # Getting methods
        collector('__getitem__', function=self._list_get)
        collector('pop', function=self._list_get)
        collector('__getslice__', function=self._self_get)

        super(List, self).__init__(list, collector.attributes)

    def _new_list(self, args):
        return _create_builtin(args, get_list)

    def _list_add(self, context):
        if self.holding is not None:
            return
        holding = context.get_argument('value')
        if holding is not None and holding != pyobjects.get_unknown():
            context.save_per_name(holding)

    def _self_set(self, context):
        if self.holding is not None:
            return
        iterable = context.get_pyname('iterable')
        holding = _infer_sequence_for_pyname(iterable)
        if holding is not None and holding != pyobjects.get_unknown():
            context.save_per_name(holding)

    def _list_get(self, context):
        if self.holding is not None:
            return self.holding
        return context.get_per_name()

    def _iterator_get(self, context):
        return Iterator(self._list_get(context))

    def _self_get(self, context):
        return get_list(self._list_get(context))


get_list = _create_builtin_getter(List)
get_list_type = _create_builtin_type_getter(List)


class Dict(BuiltinClass):

    def __init__(self, keys=None, values=None):
        self.keys = keys
        self.values = values
        item = get_tuple(self.keys, self.values)
        collector = _AttributeCollector(dict)
        collector('__new__', function=self._new_dict)
        for method in ['clear', 'has_key', 'setdefault']:
            collector(method)
        collector('__setitem__', function=self._dict_add)
        collector('popitem', function=self._item_get)
        collector('pop', function=self._value_get)
        collector('get', function=self._key_get)
        collector('keys', function=self._key_list)
        collector('values', function=self._value_list)
        collector('items', function=self._item_list)
        collector('copy', function=self._self_get)
        collector('__getitem__', function=self._value_get)
        collector('iterkeys', function=self._key_iter)
        collector('itervalues', function=self._value_iter)
        collector('iteritems', function=self._item_iter)
        collector('__iter__', function=self._key_iter)
        collector('update', function=self._self_set)
        super(Dict, self).__init__(dict, collector.attributes)

    def _new_dict(self, args):
        def do_create(holding):
            type = holding.get_type()
            if isinstance(type, Tuple) and len(type.get_holding_objects()) == 2:
                return get_dict(*type.get_holding_objects())
        return _create_builtin(args, do_create)

    def _dict_add(self, context):
        if self.keys is not None:
            return
        key, value = context.get_arguments(['self', 'key', 'value'])[1:]
        if key is not None and key != pyobjects.get_unknown():
            context.save_per_name(get_tuple(key, value))

    def _item_get(self, context):
        if self.keys is not None:
            return get_tuple(self.keys, self.values)
        item = context.get_per_name()
        if item is None:
            return get_tuple(self.keys, self.values)
        return item

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
        new_dict = context.get_pynames(['self', 'd'])[1]
        if isinstance(new_dict.get_object().get_type(), Dict):
            args = evaluate.ObjectArguments([new_dict])
            items = new_dict.get_object().get_attribute('popitem').\
                    get_object().get_returned_object(args)
            context.save_per_name(items)
        else:
            holding = _infer_sequence_for_pyname(new_dict)
            if isinstance(holding.get_type(), Tuple):
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
        collector = _AttributeCollector(set)
        collector('__new__', function=self._new_set)

        self_methods = ['copy', 'difference', 'intersection',
                        'symmetric_difference', 'union']
        for method in self_methods:
            collector(method, function=self._self_get)
        normal_methods = ['discard', 'remove',
                          'issuperset', 'issubset', 'clear']
        for method in normal_methods:
            collector(method)
        collector('add', function=self._set_add)
        collector('update', function=self._self_set)
        collector('update', function=self._self_set)
        collector('symmetric_difference_update', function=self._self_set)
        collector('difference_update', function=self._self_set)

        collector('pop', function=self._set_get)
        collector('__iter__', function=self._iterator_get)
        super(Set, self).__init__(set, collector.attributes)

    def _new_set(self, args):
        return _create_builtin(args, get_set)

    def _set_add(self, context):
        if self.holding is not None:
            return
        holding = context.get_arguments(['self', 'value'])[1]
        if holding is not None and holding != pyobjects.get_unknown():
            context.save_per_name(holding)

    def _self_set(self, context):
        if self.holding is not None:
            return
        iterable = context.get_pyname('iterable')
        holding = _infer_sequence_for_pyname(iterable)
        if holding is not None and holding != pyobjects.get_unknown():
            context.save_per_name(holding)

    def _set_get(self, context):
        if self.holding is not None:
            return self.holding
        return context.get_per_name()

    def _iterator_get(self, context):
        return Iterator(self._set_get(context))

    def _self_get(self, context):
        return get_list(self._set_get(context))


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

class Iterator(pyobjects.AbstractClass):

    def __init__(self, holding=None):
        super(Iterator, self).__init__()
        self.holding = holding
        self.attributes = {
            'next': BuiltinName(BuiltinFunction(self.holding)),
            '__iter__': BuiltinName(BuiltinFunction(self))}

    def get_attributes(self):
        return self.attributes

    def get_returned_object(self, args):
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

    def get_returned_object(self, args):
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
            'fset': BuiltinName(pynames.UnboundName()),
            'fdel': BuiltinName(pynames.UnboundName()),
            '__new__': BuiltinName(BuiltinFunction(function=_property_function))}
        super(Property, self).__init__(property, attributes)

    def get_property_object(self, args):
        if isinstance(self._fget, pyobjects.AbstractFunction):
            return self._fget.get_returned_object(args)


def _property_function(args):
    parameters = args.get_arguments(['fget', 'fset', 'fdel', 'fdoc'])
    return pyobjects.PyObject(Property(parameters[0]))


class Lambda(pyobjects.AbstractFunction):

    def __init__(self, node, scope):
        super(Lambda, self).__init__()
        self.node = node
        self.scope = scope

    def get_returned_object(self, args):
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


def _infer_sequence_for_pyname(pyname):
    if pyname is None:
        return None
    seq = pyname.get_object()
    args = evaluate.ObjectArguments([pyname])
    if '__iter__' in seq.get_attributes():
        iter = seq.get_attribute('__iter__').get_object().\
               get_returned_object(args)
        if iter is not None and 'next' in iter.get_attributes():
            holding = iter.get_attribute('next').get_object().\
                      get_returned_object(args)
            return holding


def _create_builtin(args, creator):
    passed = args.get_pynames(['sequence'])[0]
    if passed is None:
        holding = None
    else:
        holding = _infer_sequence_for_pyname(passed)
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
        #pyclass = passed_self.get_type()
        pyclass = passed_class
        if isinstance(pyclass, pyobjects.AbstractClass):
            supers = pyclass.get_superclasses()
            if supers:
                return pyobjects.PyObject(supers[0])
        return passed_self

def _zip_function(args):
    args = args.get_pynames(['sequence'])
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
    passed = args.get_pynames(['sequence'])[0]
    if passed is None:
        holding = None
    else:
        holding = _infer_sequence_for_pyname(passed)
    tuple = get_tuple(None, holding)
    return Iterator(tuple)

def _iter_function(args):
    passed = args.get_pynames(['sequence'])[0]
    if passed is None:
        holding = None
    else:
        holding = _infer_sequence_for_pyname(passed)
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
