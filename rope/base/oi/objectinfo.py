import os

import rope.base.oi.transform
import rope.base.project
from rope.base.oi import memorydb, shelvedb


class ObjectInfoManager(object):

    def __init__(self, project):
        self.project = project
        self.to_textual = rope.base.oi.transform.PyObjectToTextual(project)
        self.to_pyobject = rope.base.oi.transform.TextualToPyObject(project)
        preferred = project.get_prefs().get('objectdb_type', 'memory')
        validation = TextualValidation(self.to_pyobject)
        if preferred == 'memory' or project.ropefolder is None:
            self.objectdb = memorydb.MemoryObjectDB(validation)
        else:
            self.objectdb = shelvedb.ShelveObjectDB(project, validation)

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
            if len(args) > 0 and args[0] not in ('unknown', 'none'):
                parameters = args
                break
            if parameters is None:
                parameters = args
        if parameters:
            return [self.to_pyobject.transform(parameter)
                    for parameter in parameters]

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
        path = os.path.abspath(resource.real_path)
        lineno = pyobject.get_ast().lineno
        return self.objectdb.get_scope_info(path, str(lineno),
                                            readonly=readonly)

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
