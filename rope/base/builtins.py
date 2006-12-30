"""This module trys to support some of the builtin types and
functions.
"""

from rope.base import pyobjects
from rope.base import pynames


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


class Dict(pyobjects.PyObject):
    
    def __init__(self, keys=None, values=None):
        super(Dict, self).__init__(pyobjects.PyObject.get_base_type('Type'))
        self.keys = keys
        self.values = values
        item = Tuple(self.keys, self.values)
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

