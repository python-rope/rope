import rope.codeanalyze
import rope.pyobjects
from rope.refactor.change import (ChangeSet, ChangeFileContents,
                                  MoveResource, CreateFolder)


class MoveRefactoring(object):
    
    def __init__(self, pycore, resource, offset, dest_resource):
        self.pycore = pycore
        self.dest_resource = dest_resource

        self.old_pyname = \
            rope.codeanalyze.get_pyname_at(self.pycore, resource, offset)
        if self.old_pyname is None or \
           not isinstance(self.old_pyname.get_object(), rope.pyobjects.PyDefinedObject):
            raise rope.exceptions.RefactoringException(
                'Move refactoring should be performed on a class/function')
        self.old_name = self.old_pyname.get_object()._get_ast().name
        self.pymodule = self.old_pyname.get_object().get_module()
        self.resource = self.pymodule.get_resource()

    def move(self):
        changes = ChangeSet()
        changes.add_change(ChangeFileContents(self.dest_resource, self.resource.read()))
        changes.add_change(ChangeFileContents(self.resource, ''))
        return changes



class _Move(object):
    pass


class _MoveModule(_Move):
    pass


class _MoveClassOrFunction(_Move):
    pass
