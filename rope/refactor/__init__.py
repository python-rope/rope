import rope.importutils

from rope.refactor.change import (ChangeSet, ChangeFileContents,
                                  MoveResource, CreateFolder)
from rope.refactor.rename import RenameRefactoring
from rope.refactor.extract import ExtractMethodRefactoring
from rope.refactor.introduce_factory import IntroduceFactoryRefactoring
from rope.refactor.move import MoveRefactoring


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

    def introduce_factory(self, resource, offset, factory_name, global_factory):
        pass

    def move(self, resource, offset, dest_resource):
        pass
    
    def get_import_organizer(self):
        pass


class ImportOrganizer(object):
    
    def __init__(self, refactoring):
        self.refactoring = refactoring
        self.pycore = refactoring.pycore
        self.import_tools = rope.importutils.ImportTools(self.pycore)
    
    def _perform_command_on_module_with_imports(self, resource, method):
        pymodule = self.pycore.resource_to_pyobject(resource)
        module_with_imports = self.import_tools.get_module_with_imports(pymodule)
        method(module_with_imports)
        changes = ChangeSet()
        result = module_with_imports.get_changed_source()
        if result is not None:
            changes.add_change(ChangeFileContents(resource, result))
        self.refactoring._add_and_commit_changes(changes)
    
    def remove_unused_imports(self, resource):
        self._perform_command_on_module_with_imports(
            resource, rope.importutils.ModuleWithImports.remove_unused_imports)

    def expand_star_imports(self, resource):
        self._perform_command_on_module_with_imports(
            resource, rope.importutils.ModuleWithImports.expand_stars)

    def remove_duplicate_imports(self, resource):
        self._perform_command_on_module_with_imports(
            resource, rope.importutils.ModuleWithImports.remove_duplicates)


class PythonRefactoring(Refactoring):

    def __init__(self, pycore):
        self.pycore = pycore
        self.last_changes = ChangeSet()

    def local_rename(self, resource, offset, new_name):
        changes = RenameRefactoring(self.pycore).\
                  local_rename(resource, offset, new_name)
        self._add_and_commit_changes(changes)
    
    def rename(self, resource, offset, new_name):
        changes = RenameRefactoring(self.pycore).rename(resource, offset, new_name)
        self._add_and_commit_changes(changes)
    
    def extract_method(self, resource, start_offset, end_offset,
                       extracted_name):
        changes = ExtractMethodRefactoring(self.pycore).\
                  extract_method(resource, start_offset, end_offset,
                                 extracted_name)
        self._add_and_commit_changes(changes)
    
    def transform_module_to_package(self, resource):
        changes = ChangeSet()
        parent = resource.get_parent()
        name = resource.get_name()[:-3]
        changes.add_change(CreateFolder(parent, name))
        new_path = parent.get_path() + '/%s/__init__.py' % name
        changes.add_change(MoveResource(resource, new_path))
        self._add_and_commit_changes(changes)
    
    def introduce_factory(self, resource, offset, factory_name, global_factory=False):
        factory_introducer = IntroduceFactoryRefactoring(self.pycore, resource,
                                                         offset, factory_name, global_factory)
        changes = factory_introducer.introduce_factory()
        self._add_and_commit_changes(changes)
    
    def move(self, resource, offset, dest_resource):
        changes = MoveRefactoring(self.pycore, resource,
                                  offset, dest_resource).move()
        self._add_and_commit_changes(changes)
    
    def _add_and_commit_changes(self, changes):
        self.last_changes = changes
        changes.do()
        
    def undo_last_refactoring(self):
        self.last_changes.undo()

    def get_import_organizer(self):
        return ImportOrganizer(self)


class NoRefactoring(Refactoring):
    pass
