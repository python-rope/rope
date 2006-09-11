import re

import rope.codeanalyze
from rope.refactor.change import (ChangeSet, ChangeFileContents,
                                  MoveResource, CreateFolder)
from rope.refactor.rename import RenameRefactoring
from rope.refactor.extract import ExtractMethodRefactoring


class Refactoring(object):

    def local_rename(self, source_code, offset, new_name, resource=None):
        """Returns the changed source_code or ``None`` if nothing has been changed"""
    
    def rename(self, resource, offset, new_name):
        pass
    
    def extract_method(self, source_code, start_offset, end_offset,
                       extracted_name, resource=None):
        pass
    
    def transform_module_to_package(self, resource):
        pass
    
    def undo_last_refactoring(self):
        pass


class PythonRefactoring(Refactoring):

    def __init__(self, pycore):
        self.pycore = pycore
        self.last_changes = ChangeSet()

    def local_rename(self, source_code, offset, new_name, resource=None):
        return RenameRefactoring(self.pycore).\
               local_rename(source_code, offset, new_name, resource)
    
    def rename(self, resource, offset, new_name):
        changes = RenameRefactoring(self.pycore).rename(resource, offset, new_name)
        changes.do()
        self.last_changes = changes
    
    def extract_method(self, source_code, start_offset, end_offset,
                       extracted_name, resource=None):
        return ExtractMethodRefactoring(self.pycore).\
               extract_method(source_code, start_offset, end_offset,
                              extracted_name, resource)
    
    def transform_module_to_package(self, resource):
        changes = ChangeSet()
        parent = resource.get_parent()
        name = resource.get_name()[:-3]
        changes.add_change(CreateFolder(parent, name))
        new_path = parent.get_path() + '/%s/__init__.py' % name
        changes.add_change(MoveResource(resource, new_path))
        self.last_changes = changes
        changes.do()
    
    def undo_last_refactoring(self):
        self.last_changes.undo()


class NoRefactoring(Refactoring):
    pass
