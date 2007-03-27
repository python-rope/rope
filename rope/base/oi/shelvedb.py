import os
import shelve

import rope.base.oi.memorydb


# FIXME: Adapt to the new ObjectDB interface
class ShelveObjectDB(object):
    
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

    def _get_file_dict(self, path, readonly=True):
        if path not in self.cache:
            if path not in self.index:
                # TODO: Use better and shorter names
                self.index[path] = os.path.basename(path) + \
                                   str(hash(path)) + '.shelve'
            name = self.index[path]
            resource = self.project.get_file(self.root.path + '/' + name)
            if readonly and not resource.exists():
                return
            self.cache[path] = shelve.open(resource.real_path, writeback=True)
        return self.cache[path]

    def get_scope_info(self, path, key, readonly=True):
        key = str(key)
        file_dict = self._get_file_dict(path, readonly=readonly)
        if file_dict is None:
            return
        if key not in file_dict:
            if not readonly:
                file_dict[key] = {}
            else:
                return
        return rope.base.oi.memorydb._CallInformationOrganizer(file_dict[key])

    def sync(self):
        self.index.close()
        for file_dict in self.cache.values():
            file_dict.close()
        self._index = None
        self.cache.clear()
