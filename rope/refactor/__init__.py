import re

from rope.refactor.change import (ChangeSet, ChangeFileContents,
                                  MoveResource, CreateFolder)
from rope.refactor.rename import RenameRefactoring
from rope.refactor.extract import ExtractMethodRefactoring
from rope.refactor.introduce_factory import IntroduceFactoryRefactoring


class Refactoring(object):

    def local_rename(self, resource, offset, new_name):
        """Returns the changed source_code or ``None`` if nothing has been changed"""
    
    def rename(self, resource, offset, new_name):
        pass
    
    def extract_method(self, resource, start_offset, end_offset,
                       extracted_name):
        pass
    
    def transform_module_to_package(self, resource):
        pass
    
    def undo_last_refactoring(self):
        pass

    def introduce_factory(self, resource, offset, factory_name):
        pass


class PythonRefactoring(Refactoring):

    def __init__(self, pycore):
        self.pycore = pycore
        self.last_changes = ChangeSet()

    def local_rename(self, resource, offset, new_name):
        changes = RenameRefactoring(self.pycore).\
                  local_rename(resource, offset, new_name)
        changes.do()
        self.last_changes = changes
    
    def rename(self, resource, offset, new_name):
        changes = RenameRefactoring(self.pycore).rename(resource, offset, new_name)
        changes.do()
        self.last_changes = changes
    
    def extract_method(self, resource, start_offset, end_offset,
                       extracted_name):
        changes = ExtractMethodRefactoring(self.pycore).\
                  extract_method(resource, start_offset, end_offset,
                                 extracted_name)
        changes.do()
        self.last_changes = changes
    
    def transform_module_to_package(self, resource):
        changes = ChangeSet()
        parent = resource.get_parent()
        name = resource.get_name()[:-3]
        changes.add_change(CreateFolder(parent, name))
        new_path = parent.get_path() + '/%s/__init__.py' % name
        changes.add_change(MoveResource(resource, new_path))
        self.last_changes = changes
        changes.do()
    
    def introduce_factory(self, resource, offset, factory_name):
        factory_introducer = IntroduceFactoryRefactoring(self.pycore, resource,
                                                         offset, factory_name)
        changes = factory_introducer.introduce_factory()
        self.last_changes = changes
        changes.do()
        
    def undo_last_refactoring(self):
        self.last_changes.undo()


class NoRefactoring(Refactoring):
    pass
