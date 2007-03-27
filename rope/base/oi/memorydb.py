class MemoryObjectDB(object):

    def __init__(self):
        self.files = {}

    def get_scope_info(self, path, key, readonly=True):
        if path not in self.files:
            if readonly:
                return NullScopeInfo()
            self.files[path] = {}
        if key not in self.files[path]:
            if readonly:
                return NullScopeInfo()
            self.files[path][key] = ScopeInfo()
        return self.files[path][key]

    def sync(self):
        pass

    def validate_file(self):
        pass


class ScopeInfo(object):

    def __init__(self):
        self.call_info = {}
        self.per_name = {}

    def get_per_name(self, name):
        return self.per_name.get(name, None)

    def save_per_name(self, name, value):
        self.per_name[name] = value

    def get_returned(self, parameters):
        return self.call_info.get(parameters, None)

    def get_call_infos(self):
        for args, returned in self.call_info.items():
            yield CallInfo(args, returned)

    def add_call(self, parameters, returned):
        self.call_info[parameters] = returned


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
