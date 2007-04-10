import os

import rope.base.oi.transform
import rope.base.project
from rope.base.oi import memorydb, shelvedb


class ObjectInfoManager(object):

    def __init__(self, project):
        self.project = project
        self.to_textual = rope.base.oi.transform.PyObjectToTextual(project)
        self.to_pyobject = rope.base.oi.transform.TextualToPyObject(project)
        self.doi_to_pyobject = rope.base.oi.transform.DOITextualToPyObject(project)
        preferred = project.get_prefs().get('objectdb_type', 'memory')
        validation = TextualValidation(self.to_pyobject)
        if preferred == 'memory' or project.ropefolder is None:
            self.objectdb = memorydb.MemoryObjectDB(validation)
        else:
            self.objectdb = shelvedb.ShelveObjectDB(project, validation)
        if project.get_prefs().get('validate_objectdb', False):
            self._init_validation()

    def _init_validation(self):
        self.objectdb.validate_files()
        observer = rope.base.project.ResourceObserver(self._resource_changed,
                                                      self._resource_removed)
        files = []
        for path in self.objectdb.get_files():
            resource = self.to_pyobject.file_to_resource(path)
            if resource is not None and resource.project == self.project:
                files.append(resource)
        self.observer = rope.base.project.FilteredResourceObserver(observer,
                                                                   files)
        self.objectdb.add_file_list_observer(_FileListObserver(self))
        self.project.add_observer(self.observer)

    def _resource_changed(self, resource):
        try:
            self.objectdb.validate_file(resource.real_path)
        except SyntaxError:
            pass

    def _resource_removed(self, resource, new_resource=None):
        self.observer.remove_resource(resource)
        if new_resource is not None:
            self.objectdb.file_moved(resource.real_path, new_resource.real_path)
            self.observer.add_resource(new_resource)

    def get_returned(self, pyobject, args):
        result = self.get_exact_returned(pyobject, args)
        if result is not None:
            return result
        scope_info = self._find_scope_info(pyobject)
        for call_info in scope_info.get_call_infos():
            returned = call_info.get_returned()
            if returned and returned[0] not in ('unknown', 'none'):
                result = returned
                break
            if result is None:
                result = returned
        if result is not None:
            return self.to_pyobject.transform(result)

    def get_exact_returned(self, pyobject, args):
        scope_info = self._find_scope_info(pyobject)
        returned = scope_info.get_returned(
            self._args_to_textual(pyobject, args))
        if returned is not None:
            return self.to_pyobject.transform(returned)

    def _args_to_textual(self, pyfunction, args):
        parameters = list(pyfunction.get_param_names(special_args=False))
        arguments = args.get_arguments(parameters)[:len(parameters)]
        textual_args = tuple([self.to_textual.transform(arg)
                              for arg in arguments])
        return textual_args

    def get_parameter_objects(self, pyobject):
        scope_info = self._find_scope_info(pyobject)
        parameters = None
        for call_info in scope_info.get_call_infos():
            args = call_info.get_parameters()
            if len(args) > 0 and args[-1][0] not in ('unknown', 'none'):
                parameters = args
                break
            if parameters is None:
                parameters = args
        if parameters:
            return [self.to_pyobject.transform(parameter)
                    for parameter in parameters]

    def get_passed_objects(self, pyfunction, parameter_index):
        scope_info = self._find_scope_info(pyfunction)
        result = set()
        for call_info in scope_info.get_call_infos():
            args = call_info.get_parameters()
            if len(args) > parameter_index:
                parameter = self.to_pyobject(args[parameter_index])
                if parameter is not None:
                    result.add(parameter)
        return result

    def doi_data_received(self, data):
        def doi_to_normal(textual):
            pyobject = self.doi_to_pyobject.transform(textual)
            return self.to_textual.transform(pyobject)
        function = doi_to_normal(data[0])
        args = tuple([doi_to_normal(textual) for textual in data[1]])
        returned = doi_to_normal(data[2])
        if function[0] == 'defined' and len(function) == 3:
            self._save_data(function, args, returned)

    def function_called(self, pyfunction, params, returned=None):
        function_text = self.to_textual.transform(pyfunction)
        params_text = tuple([self.to_textual.transform(param)
                             for param in params])
        returned_text = ('unknown',)
        if returned is not None:
            returned_text = self.to_textual.transform(returned)
        self._save_data(function_text, params_text, returned_text)

    def save_per_name(self, scope, name, data):
        scope_info = self._find_scope_info(scope.pyobject, readonly=False)
        scope_info.save_per_name(name, self.to_textual.transform(data))

    def get_per_name(self, scope, name):
        scope_info = self._find_scope_info(scope.pyobject)
        result = scope_info.get_per_name(name)
        if result is not None:
            return self.to_pyobject.transform(result)

    def _save_data(self, function, args, returned=('unknown',)):
        self.objectdb.get_scope_info(function[1], function[2], readonly=False).\
             add_call(args, returned)

    def _find_scope_info(self, pyobject, readonly=True):
        resource = pyobject.get_module().get_resource()
        if resource is None:
            return memorydb.NullScopeInfo(error_on_write=False)
        textual = self.to_textual.transform(pyobject)
        if textual[0] == 'defined':
            path = textual[1]
            if len(textual) == 3:
                key = textual[2]
            else:
                key = ''
            return self.objectdb.get_scope_info(path, key, readonly=readonly)

    def sync(self):
        self.objectdb.sync()


class TextualValidation(object):

    def __init__(self, to_pyobject):
        self.to_pyobject = to_pyobject

    def is_value_valid(self, value):
        # ???: Should none and unknown be considered valid?
        if value[0] in ('none', 'unknown'):
            return True
        return self.to_pyobject.transform(value) is not None

    def is_more_valid(self, new, old):
        return new[0] not in ('unknown', 'none')

    def is_file_valid(self, path):
        return self.to_pyobject.file_to_resource(path) is not None

    def is_scope_valid(self, path, key):
        if key == '':
            textual = ('defined', path)
        else:
            textual = ('defined', path, key)
        return self.to_pyobject.transform(textual) is not None


class _FileListObserver(object):

    def __init__(self, object_info):
        self.object_info = object_info
        self.observer = self.object_info.observer
        self.to_pyobject = self.object_info.to_pyobject

    def removed(self, path):
        resource = self.to_pyobject.file_to_resource(path)
        if resource is not None:
            self.observer.remove_resource(resource)

    def added(self, path):
        resource = self.to_pyobject.file_to_resource(path)
        if resource is not None:
            self.observer.add_resource(resource)
