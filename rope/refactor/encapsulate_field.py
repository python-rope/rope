import rope.codeanalyze
from rope.refactor.rename import RenameInModule
from rope.refactor.change import ChangeSet, ChangeFileContents

class EncapsulateFieldRefactoring(object):
    
    def __init__(self, pycore, resource, offset):
        self.pycore = pycore
        self.resource = resource
        self.offset = offset
    
    def encapsulate_field(self):
        changes = ChangeSet()
        name = rope.codeanalyze.get_name_at(self.resource, self.offset)
        pyname = rope.codeanalyze.get_pyname_at(self.pycore, self.resource, self.offset)
        getter = '\n    def get_%s(self):\n        return self.%s\n' % (name, name)
        setter = '\n    def set_%s(self, value):\n        self.%s = value\n' % (name, name)
        changes.add_change(ChangeFileContents(self.resource,
                                              self.resource.read() + getter + setter))
        rename_in_module = RenameInModule(self.pycore, [pyname], name,
                                          'get_%s()' % name)
        for file in self.pycore.get_python_files():
            if file == self.resource:
                continue
            result = rename_in_module.get_changed_module(file)
            if result is not None:
                changes.add_change(ChangeFileContents(file, result))
        return changes
