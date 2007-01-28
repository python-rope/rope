import difflib
import os

from rope.base.exceptions import RopeError


class Change(object):

    def do(self, resource_operations):
        pass

    def undo(self, resource_operations):
        pass

    def get_description(self):
        return str(self)

    def get_changed_resources(self):
        return []


class ChangeSet(Change):

    def __init__(self, description):
        self.changes = []
        self.description = description

    def do(self):
        try:
            done = []
            for change in self.changes:
                change.do()
                done.append(change)
        except Exception:
            for change in done:
                change.undo()
            raise

    def undo(self):
        try:
            done = []
            for change in reversed(self.changes):
                change.undo()
                done.append(change)
        except Exception:
            for change in done:
                change.do()
            raise

    def add_change(self, change):
        self.changes.append(change)

    def get_description(self):
        result = self.description + ':\n\n\n' + \
                 '\n------\n'.join(
            [(str(change) + ':\n\n' + change.get_description())
             for change in self.changes])
        return result

    def __str__(self):
        return self.description

    def get_changed_resources(self):
        result = set()
        for change in self.changes:
            result.update(change.get_changed_resources())
        return result


class ChangeContents(Change):

    def __init__(self, resource, new_content):
        self.resource = resource
        self.new_content = new_content
        self.old_content = None
        self.operations = self.resource.project.operations

    def do(self):
        self.old_content = self.resource.read()
        self.operations.write_file(self.resource, self.new_content)

    def undo(self):
        self.operations.write_file(self.resource, self.old_content)

    def __str__(self):
        return 'Change <%s>' % self.resource.path

    def get_description(self):
        differ = difflib.Differ()
        result = list(differ.compare(self.resource.read().splitlines(True),
                                     self.new_content.splitlines(True)))
        return ''.join(result)

    def get_changed_resources(self):
        return [self.resource]


class MoveResource(Change):

    def __init__(self, resource, new_location):
        self.project = resource.project
        self.new_location = _get_destination_for_move(resource, new_location)
        self.old_location = resource.path
        self.operations = resource.project.operations
        self.old_resource = resource
        self.new_resource = None

    def do(self):
        self.operations.move(self.old_resource, self.new_location)
        self.new_resource = self.project.get_resource(self.new_location)

    def undo(self):
        self.operations.move(self.new_resource, self.old_location)

    def __str__(self):
        return 'Move <%s>' % self.old_location

    def get_description(self):
        return 'Move <%s> to <%s>' % (self.old_location, self.new_location)

    def get_changed_resources(self):
        return [self.old_resource, self.new_resource]


class _CreateResource(Change):

    def __init__(self, parent, name):
        self.parent = parent
        self.name = name
        self.new_resource = None
        self.operations = self.parent.project.operations

    def undo(self):
        self.operations.remove(self.new_resource)

    def __str__(self):
        return 'Create <%s>' % (self.parent.path + '/' + self.name)

    def get_changed_resources(self):
        return [self.new_resource]


class CreateFolder(_CreateResource):

    def do(self):
        self.new_resource = self.operations.create_folder(self.parent,
                                                          self.name)


class CreateFile(_CreateResource):

    def do(self):
        self.new_resource = self.operations.create_file(self.parent,
                                                        self.name)


class RemoveResource(Change):

    def __init__(self, resource):
        self.resource = resource
        self.operations = resource.project.operations

    def do(self):
        self.operations.remove(self.resource)

    # TODO: Undoing remove operations
    def undo(self):
        pass

    def __str__(self):
        return 'Remove <%s>' % (self.resource.path)

    def get_changed_resources(self):
        return [self.resource]


class _ResourceOperations(object):

    def __init__(self, project, fscommands):
        self.project = project
        self.fscommands = fscommands

    def write_file(self, resource, contents):
        self.project.file_access.write(resource.real_path, contents)
        for observer in list(self.project.observers):
            observer.resource_changed(resource)

    def move(self, resource, new_location):
        destination = _get_destination_for_move(resource, new_location)
        self.fscommands.move(resource.real_path,
                             self.project._get_resource_path(destination))
        new_resource = self.project.get_resource(destination)
        for observer in list(self.project.observers):
            observer.resource_removed(resource, new_resource)

    def create_file(self, folder, file_name):
        if folder.path:
            file_path = folder.path + '/' + file_name
        else:
            file_path = file_name
        self._create_file(file_path)
        child = folder.get_child(file_name)
        for observer in list(self.project.observers):
            observer.resource_changed(child)
        return child

    def create_folder(self, folder, folder_name):
        if folder.path:
            folder_path = folder.path + '/' + folder_name
        else:
            folder_path = folder_name
        self._create_folder(folder_path)
        child = folder.get_child(folder_name)
        for observer in list(self.project.observers):
            observer.resource_changed(child)
        return child

    def remove(self, resource):
        self.fscommands.remove(resource.real_path)
        for observer in list(self.project.observers):
            observer.resource_removed(resource)

    def _create_file(self, file_name):
        file_path = self.project._get_resource_path(file_name)
        if os.path.exists(file_path):
            if os.path.isfile(file_path):
                raise RopeError('File already exists')
            else:
                raise RopeError('A folder with the same name'
                                    ' as this file already exists')
        try:
            self.fscommands.create_file(file_path)
        except IOError, e:
            raise RopeError(e)

    def _create_folder(self, folder_name):
        folder_path = self.project._get_resource_path(folder_name)
        if os.path.exists(folder_path):
            if not os.path.isdir(folder_path):
                raise RopeError('A file with the same name as'
                                    ' this folder already exists')
            else:
                raise RopeError('Folder already exists')
        self.fscommands.create_folder(folder_path)


def _get_destination_for_move(resource, destination):
    dest_path = resource.project._get_resource_path(destination)
    if os.path.isdir(dest_path):
        if destination != '':
            return destination + '/' + resource.name
        else:
            return resource.name
    return destination

