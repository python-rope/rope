class ObjectDB(object):

#    def __init__(self, validation):
#        self.validation = validation
#        self.observers = observers

    def get_scope_info(self, path, key, readonly=True):
        pass

    def get_returned(self, path, key, args):
        scope_info = self.get_scope_info(path, key, readonly=True)
        return scope_info.get_returned(args)

    def get_pername(self, path, key, name):
        scope_info = self.get_scope_info(path, key, readonly=True)
        return scope_info.get_per_name(name)

    def get_callinfos(self, path, key):
        scope_info = self.get_scope_info(path, key, readonly=True)
        return scope_info.get_call_infos()

    def add_callinfo(self, path, key, args, returned):
        scope_info = self.get_scope_info(path, key, readonly=False)
        scope_info.add_call(args, returned)

    def add_pername(self, path, key, name, value):
        scope_info = self.get_scope_info(path, key, readonly=False)
        scope_info.save_per_name(name, value)

    def get_files(self):
        pass

    def validate_files(self):
        pass

    def validate_file(self, file):
        pass

    def file_moved(self, file, newfile):
        pass

    def add_file_list_observer(self, observer):
        self.observers.append(observer)

    def sync(self):
        pass


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
