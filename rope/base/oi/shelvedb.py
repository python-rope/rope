import os
import shelve
import random

from rope.base.oi import objectdb, memorydb


class ShelveObjectDB(objectdb.ObjectDB):

    def __init__(self, project, validation):
        self.project = project
        self.validation = validation
        self._root = None
        self._index = None
        self.cache = {}
        self.random = random.Random()
        self.observers = []

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

    def _get_name_for_path(self, path):
        base_name = os.path.basename(path)
        def to_hex(i):
            return hex(i).replace('0x', '', 1).replace('L', '')
        hashed = to_hex(hash(path))
        if not hashed.startswith('-'):
            hashed = '-' + hashed
        second_list = list(to_hex(id(path)) +
                           to_hex(self.random.randint(0, 255)))
        self.random.shuffle(second_list)
        shuffled = ''.join(second_list)
        return base_name + hashed + shuffled + '.shelve'

    def _get_file_dict(self, path, readonly=True):
        if path not in self.cache:
            resource = self._get_file_resource(path)
            if readonly and not resource.exists():
                return
            self.cache[path] = shelve.open(resource.real_path, writeback=True)
            for observer in self.observers:
                observer.added(path)
        return self.cache[path]

    def _get_file_resource(self, path):
        if path not in self.index:
            self.index[path] = self._add_file_for_path(path)
        name = self.index[path]
        return self.project.get_file(self.root.path + '/' + name)

    def _add_file_for_path(self, path):
        while True:
            new_name = self._get_name_for_path(path)
            new_resource = self.project.get_file(self.root.path
                                                 + '/' + new_name)
            if not new_resource.exists():
                break
        return new_name

    def get_scope_info(self, path, key, readonly=True):
        file_dict = self._get_file_dict(path, readonly=readonly)
        if file_dict is None:
            return objectdb._NullScopeInfo()
        if key not in file_dict:
            if readonly:
                return objectdb._NullScopeInfo()
            file_dict[key] = memorydb.ScopeInfo()
        result = file_dict[key]
        result._set_validation(self.validation)
        return result

    def sync(self):
        self.index.close()
        for file_dict in self.cache.values():
            file_dict.close()
        self._index = None
        self.cache.clear()

    def get_files(self):
        return self.index.keys()

    def validate_files(self):
        for file in list(self.get_files()):
            if not self.validation.is_file_valid(file) or \
               not self._get_file_resource(file).exists():
                self._remove_file(file, on_disk=False)

    def validate_file(self, file):
        if file not in self.index:
            return
        if not self._get_file_resource(file).exists():
            self._remove_file(file, on_disk=False)
            return
        file_dict = self._get_file_dict(file)
        if file_dict is None:
            return
        try:
            for key in file_dict.keys():
                if not self.validation.is_scope_valid(file, key):
                    del file_dict[key]
        except Exception, e:
            print 'Probably an error in DB: ', type(e), e
            print 'Print cleaning up! removing <%s> ... ' % file
            self._remove_file(file)

    def file_moved(self, file, newfile):
        if file not in self.index:
            return
        self.index[newfile] = self.index[file]
        self._remove_file(file, on_disk=False)

    def _remove_file(self, file, on_disk=True):
        if file not in self.index:
            return
        if file in self.cache:
            self.cache[file].close()
            del self.cache[file]
        mapping = self.index[file]
        del self.index[file]
        if on_disk:
            self.root.get_child(mapping).remove()
        for observer in self.observers:
            observer.removed(file)

    def add_file_list_observer(self, observer):
        self.observers.append(observer)
