import difflib
import os
import time
import datetime

from rope.base.exceptions import RopeError
from rope.base.fscommands import FileSystemCommands


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

    def __init__(self, description, timestamp=None):
        self.changes = []
        self.description = description
        self.time = timestamp

    def do(self):
        try:
            done = []
            for change in self.changes:
                change.do()
                done.append(change)
            self.time = time.time()
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
        result = str(self) + ':\n\n\n' + \
                 '\n------\n'.join(
            [(str(change) + ':\n\n' + change.get_description())
             for change in self.changes])
        return result

    def __str__(self):
        if self.time is not None:
            date = datetime.datetime.fromtimestamp(self.time)
            if date.date() == datetime.date.today():
                string_date = 'today'
            elif date.date() == (datetime.date.today() - datetime.timedelta(1)):
                string_date = 'yesterday'
            else:
                string_date = date.strftime('%a %d %b %Y')
            string_time = date.strftime('%H:%M:%S')
            string_time = '%s %s ' % (string_date, string_time)
            return self.description + ' - ' + string_time
        return self.description

    def get_changed_resources(self):
        result = set()
        for change in self.changes:
            result.update(change.get_changed_resources())
        return result


class ChangeContents(Change):

    def __init__(self, resource, new_content, old_content=None):
        self.resource = resource
        self.new_content = new_content
        self.old_content = old_content
        if self.old_content is None:
            if self.resource.exists():
                self.old_content = self.resource.read()
        self.operations = self.resource.project.operations

    def do(self):
        if self.old_content is None:
            self.old_content = self.resource.read()
        self.operations.write_file(self.resource, self.new_content)

    def undo(self):
        self.operations.write_file(self.resource, self.old_content)

    def __str__(self):
        return 'Change <%s>' % self.resource.path

    def get_description(self):
        differ = difflib.Differ()
        result = list(differ.compare(self.old_content.splitlines(True),
                                     self.new_content.splitlines(True)))
        return ''.join(result)

    def get_changed_resources(self):
        return [self.resource]


class MoveResource(Change):

    def __init__(self, resource, new_location, exact=False):
        self.project = resource.project
        self.operations = resource.project.operations
        self.old_resource = resource
        if not exact:
            new_location = _get_destination_for_move(resource, new_location)
        if resource.is_folder():
            self.new_resource = self.project.get_folder(new_location)
        else:
            self.new_resource = self.project.get_file(new_location)

    def do(self):
        self.operations.move(self.old_resource, self.new_resource.path)

    def undo(self):
        self.operations.move(self.new_resource, self.old_resource.path)

    def __str__(self):
        return 'Move <%s>' % self.old_location

    def get_description(self):
        return 'Move <%s> to <%s>' % (self.old_resource.path,
                                      self.new_resource.path)

    def get_changed_resources(self):
        return [self.old_resource, self.new_resource]


class CreateResource(Change):

    def __init__(self, resource):
        self.resource = resource
        self.operations = self.resource.project.operations

    def do(self):
        self.operations.create(self.resource)

    def undo(self):
        self.operations.remove(self.resource)

    def __str__(self):
        return 'Create Resource <%s>' % (self.resource.path)

    def get_changed_resources(self):
        return [self.resource]

    def _get_child_path(self, parent, name):
        if parent.path == '':
            return name
        else:
            return parent.path + '/' + name


class CreateFolder(CreateResource):

    def __init__(self, parent, name):
        resource = parent.project.get_folder(self._get_child_path(parent, name))
        super(CreateFolder, self).__init__(resource)


class CreateFile(CreateResource):

    def __init__(self, parent, name):
        resource = parent.project.get_file(self._get_child_path(parent, name))
        super(CreateFile, self).__init__(resource)


class RemoveResource(Change):

    def __init__(self, resource):
        self.resource = resource
        self.operations = resource.project.operations

    def do(self):
        self.operations.remove(self.resource)

    # TODO: Undoing remove operations
    def undo(self):
        raise NotImplementedError(
            'Undoing `RemoveResource` is not implemented yet.')

    def __str__(self):
        return 'Remove <%s>' % (self.resource.path)

    def get_changed_resources(self):
        return [self.resource]


class _ResourceOperations(object):

    def __init__(self, project, fscommands):
        self.project = project
        self.fscommands = fscommands
        self.direct_commands = FileSystemCommands()

    def _get_fscommands(self, resource):
        if self.project.is_ignored(resource):
            return self.direct_commands
        return self.fscommands

    def write_file(self, resource, contents):
        self.project.file_access.write(resource.real_path, contents)
        for observer in list(self.project.observers):
            observer.resource_changed(resource)

    def move(self, resource, new_location):
        destination = _get_destination_for_move(resource, new_location)
        fscommands = self._get_fscommands(resource)
        fscommands.move(resource.real_path,
                        self.project._get_resource_path(destination))
        new_resource = self.project.get_resource(destination)
        for observer in list(self.project.observers):
            observer.resource_removed(resource, new_resource)

    def create(self, resource):
        if resource.is_folder():
            self._create_folder(resource.path)
        else:
            self._create_file(resource.path)
        for observer in list(self.project.observers):
            observer.resource_changed(resource)

    def remove(self, resource):
        fscommands = self._get_fscommands(resource)
        fscommands.remove(resource.real_path)
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
            fscommands = self._get_fscommands(self.project.get_file(file_name))
            fscommands.create_file(file_path)
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
        fscommands = self._get_fscommands(self.project.get_folder(folder_name))
        fscommands.create_folder(folder_path)


def _get_destination_for_move(resource, destination):
    dest_path = resource.project._get_resource_path(destination)
    if os.path.isdir(dest_path):
        if destination != '':
            return destination + '/' + resource.name
        else:
            return resource.name
    return destination


class ChangeToData(object):

    def convertChangeSet(self, change):
        description = change.description
        changes = []
        for child in change.changes:
            changes.append(self(child))
        return (description, changes, change.time)

    def convertChangeContents(self, change):
        return (change.resource.path, change.new_content, change.old_content)

    def convertMoveResource(self, change):
        return (change.old_resource.path, change.new_resource.path)

    def convertCreateResource(self, change):
        return (change.resource.path, change.resource.is_folder())

    def convertRemoveResource(self, change):
        return (change.resource.path, change.resource.is_folder())

    def __call__(self, change):
        change_type = type(change)
        if change_type in (CreateFolder, CreateFile):
            change_type = CreateResource
        method = getattr(self, 'convert' + change_type.__name__)
        return (change_type.__name__, method(change))


class DataToChange(object):

    def __init__(self, project):
        self.project = project

    def makeChangeSet(self, description, changes, time=None):
        result = ChangeSet(description, time)
        for child in changes:
            result.add_change(self(child))
        return result

    def makeChangeContents(self, path, new_content, old_content):
        resource = self.project.get_file(path)
        return ChangeContents(resource, new_content, old_content)

    def makeMoveResource(self, old_path, new_path):
        resource = self.project.get_file(old_path)
        return MoveResource(resource, new_path, exact=True)

    def makeCreateResource(self, path, is_folder):
        if is_folder:
            resource = self.project.get_folder(path)
        else:
            resource = self.project.get_file(path)
        return CreateResource(resource)

    def makeRemoveResource(self, path, is_folder):
        if is_folder:
            resource = self.project.get_folder(path)
        else:
            resource = self.project.get_file(path)
        return RemoveResource(resource)

    def __call__(self, data):
        method = getattr(self, 'make' + data[0])
        return method(*data[1])
