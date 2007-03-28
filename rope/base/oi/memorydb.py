class MemoryObjectDB(object):

    def __init__(self, validation):
        self.files = {}
        self.validation = validation

    def get_scope_info(self, path, key, readonly=True):
        if path not in self.files:
            if readonly:
                return NullScopeInfo()
            self.files[path] = {}
        if key not in self.files[path]:
            if readonly:
                return NullScopeInfo()
            self.files[path][key] = ScopeInfo()
            self.files[path][key]._set_validation(self.validation)
        return self.files[path][key]

    def sync(self):
        pass


class ScopeInfo(object):

    def __init__(self):
        self.call_info = {}
        self.per_name = {}
        self._validation = None

    def _set_validation(self, validation):
        """Should be called after creation or unpickling"""
        self._validation = validation

    def get_per_name(self, name):
        result = self.per_name.get(name, None)
        if result is not None and not self._validation.is_value_valid(result):
            del self.per_name[name]
            return None
        return result

    def save_per_name(self, name, value):
        if name not in self.per_name or \
           self._validation.is_more_valid(value, self.per_name[name]):
            self.per_name[name] = value

    def get_returned(self, parameters):
        result = self.call_info.get(parameters, None)
        if result is not None and not self._validation.is_value_valid(result):
            self.call_info[parameters] = None
            return None
        return result

    def get_call_infos(self):
        for args, returned in self.call_info.items():
            yield CallInfo(args, returned)

    def add_call(self, parameters, returned):
        if parameters not in self.call_info or \
           self._validation.is_more_valid(returned, self.call_info[parameters]):
            self.call_info[parameters] = returned

    def __getstate__(self):
        return (self.call_info, self.per_name)

    def __setstate__(self, data):
        self.call_info, self.per_name = data


class NullScopeInfo(object):

    def __init__(self, error_on_write=True):
        self.error_on_write = error_on_write

    def get_per_name(self, name):
        pass

    def save_per_name(self, name, value):
        if self.error_on_write:
            raise NotImplementedError()

    def get_returned(self, parameters):
        pass

    def get_call_infos(self):
        return []

    def add_call(self, parameters, returned):
        if self.error_on_write:
            raise NotImplementedError()


class CallInfo(object):

    def __init__(self, args, returned):
        self.args = args
        self.returned = returned

    def get_parameters(self):
        return self.args

    def get_returned(self):
        return self.returned
