from rope.base.oi import objectdb


class MemoryObjectDB(objectdb.ObjectDB, objectdb.FileDict):

    def __init__(self, validation):
        super(MemoryObjectDB, self).__init__(validation)
        self._files = {}
        self.files = self

    def keys(self):
        return self._files.keys()

    def __contains__(self, key):
        return key in self._files

    def __getitem__(self, key):
        return self._files[key]

    def create(self, path):
        self._files[path] = {}

    def rename(self, file, newfile):
        if file not in self._files:
            return
        self._files[newfile] = self._files[file]
        del self[file]

    def __delitem__(self, file):
        del self._files[file]

    def sync(self):
        pass
