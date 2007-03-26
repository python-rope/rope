import os
import re
import shelve

import rope.base.project
from rope.base import pyobjects


class ObjectInfoManager(object):

    def __init__(self, project):
        self.project = project
        self.to_textual = _PyObjectToTextual(project)
        self.to_pyobject = _TextualToPyObject(project)
        self.per_object = {}
        prefered_db = project.get_prefs().get('objectdb_type', 'memory')
        if prefered_db == 'memory' or \
           isinstance(project, rope.base.project.NoProject) or \
           project.ropefolder is None:
            self.objectdb = _MemoryObjectDB()
        else:
            self.objectdb = _DiskObjectDB(project)

    def get_returned(self, pyobject, args):
        organizer = self.find_organizer(pyobject)
        if organizer:
            return self.to_pyobject.transform(
                organizer.get_returned(self._args_to_textual(pyobject, args)))

    def get_exact_returned(self, pyobject, args):
        organizer = self.find_organizer(pyobject)
        if organizer:
            return self.to_pyobject.transform(
                organizer.get_exact_returned(self._args_to_textual(pyobject, args)))

    def _args_to_textual(self, pyfunction, args):
        parameters = list(pyfunction.get_param_names(special_args=False))
        arguments = args.get_arguments(parameters)[:len(parameters)]
        textual_args = tuple([self.to_textual.transform(arg)
                              for arg in arguments])
        return textual_args

    def get_parameter_objects(self, pyobject):
        organizer = self.find_organizer(pyobject)
        if organizer is not None:
            pyobjects = [self.to_pyobject.transform(parameter)
                         for parameter in organizer.get_parameters()]
            return pyobjects

    def doi_data_received(self, data):
        self._save_data(data[0], data[1], data[2])

    def function_called(self, pyfunction, params, returned=None):
        function_text = self.to_textual.transform(pyfunction)
        params_text = tuple([self.to_textual.transform(param)
                             for param in params])
        returned_text = ('unknown',)
        if returned is not None:
            returned_text = self.to_textual.transform(returned)
        self._save_data(function_text, params_text, returned_text)

    def save_per_name(self, scope, name, data):
        key = (self.to_textual.transform(scope.pyobject), name)
        self.per_object[key] = self.to_textual.transform(data)

    def get_per_name(self, scope, name):
        key = (self.to_textual.transform(scope.pyobject), name)
        data = self.per_object.get(key, ('unknown',))
        return self.to_pyobject.transform(data)

    def _save_data(self, function, args, returned=('unknown',)):
        self.objectdb.get_call_info(function[1], function[2], create=True).\
             add_call_information(args, returned)

    def find_organizer(self, pyobject):
        resource = pyobject.get_module().get_resource()
        if resource is None:
            return
        path = os.path.abspath(resource.real_path)
        lineno = pyobject.get_ast().lineno
        return self.objectdb.get_call_info(path, lineno, create=False)

    def close(self):
        self.objectdb.close()


class _MemoryObjectDB(object):

    def __init__(self):
        self.files = {}

    def get_call_info(self, path, key, create=True):
        if path not in self.files:
            if create:
                self.files[path] = {}
            else:
                return
        if key not in self.files[path]:
            if create:
                self.files[path][key] = {}
            else:
                return
        return _CallInformationOrganizer(self.files[path][key])

    def close(self):
        pass


class _DiskObjectDB(object):
    
    def __init__(self, project):
        self.project = project
        self._root = None
        self._index = None
        self.cache = {}

    def _get_root(self):
        if self._root is None:
            self._root = self._get_resource(self.project.ropefolder,
                                            'objectdb', is_folder=True)
        return self._root

    def _get_index(self):
        if self._index is None:
            index_file = self.project.get_file(self.root.path + '/index.shelve')
            self._index = shelve.open(index_file.real_path, writeback=True)
        return self._index

    root = property(_get_root)
    index = property(_get_index)

    def _get_resource(self, parent, name, is_folder=False):
        if parent.has_child(name):
            return parent.get_child(name)
        else:
            if is_folder:
                return parent.create_folder(name)
            else:
                return parent.create_file(name)

    def _get_file_dict(self, path, create=True):
        if path not in self.cache:
            if path not in self.index:
                # TODO: Use better and shorter names
                self.index[path] = os.path.basename(path) + \
                                   str(hash(path)) + '.shelve'
            name = self.index[path]
            resource = self.project.get_file(self.root.path + '/' + name)
            if not create and not resource.exists():
                return
            self.cache[path] = shelve.open(resource.real_path, writeback=True)
        return self.cache[path]

    def get_call_info(self, path, key, create=True):
        key = str(key)
        file_dict = self._get_file_dict(path, create=create)
        if file_dict is None:
            return
        if key not in file_dict:
            if create:
                file_dict[key] = {}
            else:
                return
        return _CallInformationOrganizer(file_dict[key])

    def close(self):
        self.index.close()
        for file_dict in self.cache.values():
            file_dict.close()
        self._index = None
        self.cache.clear()


class _CallInformationOrganizer(object):

    def __init__(self, info=None):
        if info is None:
            self.info = {}
        else:
            self.info = info

    def add_call_information(self, args, returned):
        self.info[args] = returned

    def get_parameters(self):
        for args in self.info.keys():
            if len(args) > 0 and args[0] not in ('unknown', 'none'):
                return args
        return self.info.keys()[0]

    def get_returned(self, args):
        result = self.get_exact_returned(args)
        if result != ('unknown',):
            return result
        return self._get_default_returned()

    def get_exact_returned(self, args):
        if len(self.info) == 0 or args is None:
            return ('unknown',)
        if self.info.get(args, ('unknown',)) != ('unknown',):
            return self.info[args]
        return ('unknown',)

    def _get_default_returned(self):
        for returned in self.info.values():
            if returned[0] not in ('unknown'):
                return returned
        return ('unknown',)


class _TextualToPyObject(object):

    def __init__(self, project):
        self.project = project

    def transform(self, textual):
        """Transform an object from textual form to `PyObject`"""
        type = textual[0]
        try:
            method = getattr(self, type + '_to_pyobject')
            return method(textual)
        except AttributeError:
            return None

    def module_to_pyobject(self, textual):
        path = textual[1]
        return self._get_pymodule(path)

    def builtin_to_pyobject(self, textual):
        name = textual[1]
        if name == 'str':
            return rope.base.builtins.get_str()
        if name == 'list':
            holding = self.transform(textual[2])
            return rope.base.builtins.get_list(holding)
        if name == 'dict':
            keys = self.transform(textual[2])
            values = self.transform(textual[3])
            return rope.base.builtins.get_dict(keys, values)
        if name == 'tuple':
            objects = []
            for holding in textual[2:]:
                objects.append(self.transform(holding))
            return rope.base.builtins.get_tuple(*objects)
        if name == 'set':
            holding = self.transform(textual[2])
            return rope.base.builtins.get_set(holding)
        if name == 'iter':
            holding = self.transform(textual[2])
            return rope.base.builtins.get_iterator(holding)
        if name == 'generator':
            holding = self.transform(textual[2])
            return rope.base.builtins.get_generator(holding)
        if name == 'file':
            return rope.base.builtins.get_file()
        if name == 'function':
            if textual[2] in rope.base.builtins.builtins:
                return rope.base.builtins.builtins[textual[2]].get_object()
        return None

    def unknown_to_pyobject(self, textual):
        return None

    def none_to_pyobject(self, textual):
        return None

    def function_to_pyobject(self, textual):
        return self._get_pyobject_at(textual[1], textual[2])

    def class_to_pyobject(self, textual):
        path, name = textual[1:]
        pymodule = self._get_pymodule(path)
        module_scope = pymodule.get_scope()
        suspected = None
        if name in module_scope.get_names():
            suspected = module_scope.get_name(name).get_object()
        if suspected is not None and isinstance(suspected, pyobjects.PyClass):
            return suspected
        else:
            lineno = self._find_occurrence(name, pymodule.get_resource().read())
            if lineno is not None:
                inner_scope = module_scope.get_inner_scope_for_line(lineno)
                return inner_scope.pyobject

    def instance_to_pyobject(self, textual):
        type = self.class_to_pyobject(textual)
        if type is not None:
            return rope.base.pyobjects.PyObject(type)

    def _find_occurrence(self, name, source):
        pattern = re.compile(r'^\s*class\s*' + name + r'\b')
        lines = source.split('\n')
        for i in range(len(lines)):
            if pattern.match(lines[i]):
                return i + 1

    def _get_pymodule(self, path):
        root = os.path.abspath(self.project.address)
        if path.startswith(root):
            relative_path = path[len(root):]
            if relative_path.startswith('/') or relative_path.startswith(os.sep):
                relative_path = relative_path[1:]
            resource = self.project.get_resource(relative_path)
        else:
            resource = rope.base.project.get_no_project().get_resource(path)
        return self.project.get_pycore().resource_to_pyobject(resource)

    def _get_pyobject_at(self, path, lineno):
        scope = self._get_pymodule(path).get_scope()
        inner_scope = scope.get_inner_scope_for_line(lineno)
        return inner_scope.pyobject


class _PyObjectToTextual(object):

    def __init__(self, project):
        self.project = project

    def transform(self, pyobject):
        """Transform a `PyObject` to textual form"""
        if pyobject is None:
            return ('none',)
        object_type = type(pyobject)
        try:
            method = getattr(self, object_type.__name__ + '_to_textual')
            return method(pyobject)
        except AttributeError:
            return ('unknown',)

    def PyObject_to_textual(self, pyobject):
        if type(pyobject.get_type()) != pyobjects.PyObject:
            result = self.transform(pyobject.get_type())
            if result[0] == 'class':
                return ('instance',) + result[1:]
            return result
        return ('unknown',)

    def PyFunction_to_textual(self, pyobject):
        return ('function', self._get_pymodule_path(pyobject.get_module()),
                pyobject.get_ast().lineno)

    def PyClass_to_textual(self, pyobject):
        return ('class', self._get_pymodule_path(pyobject.get_module()),
                pyobject.get_name())

    def PyModule_to_textual(self, pyobject):
        return ('module', self._get_pymodule_path(pyobject))

    def PyPackage_to_textual(self, pyobject):
        return ('module', self._get_pymodule_path(pyobject))

    def List_to_textual(self, pyobject):
        return ('builtin', 'list', self.transform(pyobject.holding))

    def Dict_to_textual(self, pyobject):
        return ('builtin', 'dict', self.transform(pyobject.keys),
                self.transform(pyobject.values))

    def Tuple_to_textual(self, pyobject):
        objects = [self.transform(holding) for holding in pyobject.get_holding_objects()]
        return tuple(['builtin', 'tuple'] + objects)

    def Set_to_textual(self, pyobject):
        return ('builtin', 'set', self.transform(pyobject.holding))

    def Iterator_to_textual(self, pyobject):
        return ('builtin', 'iter', self.transform(pyobject.holding))

    def Generator_to_textual(self, pyobject):
        return ('builtin', 'generator', self.transform(pyobject.holding))

    def Str_to_textual(self, pyobject):
        return ('builtin', 'str')

    def File_to_textual(self, pyobject):
        return ('builtin', 'file')

    def BuiltinFunction_to_textual(self, pyobject):
        return ('builtin', 'function', pyobject.get_name())

    def _get_pymodule_path(self, pymodule):
        resource = pymodule.get_resource()
        resource_path = resource.path
        if os.path.isabs(resource_path):
            return resource_path
        return os.path.abspath(
            os.path.normpath(os.path.join(self.project.address,
                                          resource_path)))
