import UserDict


class ObjectDB(object):

    def __init__(self, validation):
        self.validation = validation
        self.observers = []

    def validate_files(self):
        for file in self.files:
            if not self.validation.is_file_valid(file):
                del self.files[file]
                self._file_removed(file)

    def validate_file(self, file):
        if file not in self.files:
            return
        for key in list(self.files[file]):
            if not self.validation.is_scope_valid(file, key):
                del self.files[file][key]

    def file_moved(self, file, newfile):
        if file not in self.files:
            return
        self.files.rename(file, newfile)
        self._file_removed(file)
        self._file_added(newfile)

    def get_files(self):
        return self.files.keys()

    def get_returned(self, path, key, args):
        scope_info = self._get_scope_info(path, key, readonly=True)
        return scope_info.get_returned(args)

    def get_pername(self, path, key, name):
        scope_info = self._get_scope_info(path, key, readonly=True)
        return scope_info.get_per_name(name)

    def get_callinfos(self, path, key):
        scope_info = self._get_scope_info(path, key, readonly=True)
        return scope_info.get_call_infos()

    def add_callinfo(self, path, key, args, returned):
        scope_info = self._get_scope_info(path, key, readonly=False)
        scope_info.add_call(args, returned)

    def add_pername(self, path, key, name, value):
        scope_info = self._get_scope_info(path, key, readonly=False)
        scope_info.save_per_name(name, value)

    def add_file_list_observer(self, observer):
        self.observers.append(observer)

    def sync(self):
        pass

    def _get_scope_info(self, path, key, readonly=True):
        if path not in self.files:
            if readonly:
                return _NullScopeInfo()
            self.files.create(path)
            self._file_added(path)
        if key not in self.files[path]:
            if readonly:
                return _NullScopeInfo()
            self.files[path][key] = ScopeInfo()
        result = self.files[path][key]
        result._set_validation(self.validation)
        return result

    def _file_removed(self, path):
        for observer in self.observers:
            observer.removed(path)

    def _file_added(self, path):
        for observer in self.observers:
            observer.added(path)


class _NullScopeInfo(object):

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


class FileListObserver(object):

    def added(self, path):
        pass

    def removed(self, path):
        pass


class FileDict(UserDict.DictMixin):

    def create(self, key):
        pass

    def rename(self, key, new_key):
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
