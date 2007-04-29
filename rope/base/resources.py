import os

import rope.base.change
from rope.base.exceptions import RopeError


class Resource(object):
    """Represents files and folders in a project"""

    def __init__(self, project, path):
        self.project = project
        self._path = path

    def move(self, new_location):
        """Move resource to `new_location`"""
        self._perform_change(rope.base.change.MoveResource(self, new_location),
                             'Moving <%s> to <%s>' % (self.path, new_location))

    def remove(self):
        """Remove resource from the project"""
        self._perform_change(rope.base.change.RemoveResource(self),
                             'Removing <%s>' % self.path)

    def is_folder(self):
        """Return true if the resource is a folder"""

    def create(self):
        """Create this resource"""

    def exists(self):
        return os.path.exists(self.real_path)

    def _get_parent(self):
        parent = '/'.join(self.path.split('/')[0:-1])
        return self.project.get_resource(parent)

    def _get_path(self):
        """Return the path of this resource relative to the project root

        The path is the list of parent directories separated by '/' followed
        by the resource name.
        """
        return self._path

    def _get_name(self):
        """Return the name of this resource"""
        return self.path.split('/')[-1]

    def _get_real_path(self):
        """Return the file system path of this resource"""
        return self.project._get_resource_path(self.path)

    def _get_destination_for_move(self, destination):
        dest_path = self.project._get_resource_path(destination)
        if os.path.isdir(dest_path):
            if destination != '':
                return destination + '/' + self.name
            else:
                return self.name
        return destination

    parent = property(_get_parent)
    name = property(_get_name)
    path = property(_get_path)
    real_path = property(_get_real_path)

    def __eq__(self, obj):
        return self.__class__ == obj.__class__ and self.path == obj.path

    def __hash__(self):
        return hash(self.path)

    def _perform_change(self, change_, description):
        changes = rope.base.change.ChangeSet(description)
        changes.add_change(change_)
        self.project.do(changes)


class File(Resource):
    """Represents a file"""

    def __init__(self, project, name):
        super(File, self).__init__(project, name)

    def read(self):
        return self.project.file_access.read(self.real_path)

    def write(self, contents):
        try:
            if contents == self.read():
                return
        except IOError:
            pass
        self._perform_change(rope.base.change.ChangeContents(self, contents),
                             'Writing file <%s>' % self.path)

    def is_folder(self):
        return False

    def create(self):
        self.parent.create_file(self.name)


class Folder(Resource):
    """Represents a folder"""

    def __init__(self, project, name):
        super(Folder, self).__init__(project, name)

    def is_folder(self):
        return True

    def get_children(self):
        """Return the children of this folder"""
        path = self.real_path
        result = []
        content = os.listdir(path)
        for name in content:
            child = self.get_child(name)
            if not self.project.is_ignored(child):
                result.append(self.get_child(name))
        return result

    def create_file(self, file_name):
        self._perform_change(
            rope.base.change.CreateFile(self, file_name),
            'Creating file <%s>' % self._get_child_path(file_name))
        return self.get_child(file_name)

    def create_folder(self, folder_name):
        self._perform_change(
            rope.base.change.CreateFolder(self, folder_name),
            'Creating folder <%s>' % self._get_child_path(folder_name))
        return self.get_child(folder_name)

    def _get_child_path(self, name):
        if self.path:
            return self.path + '/' + name
        else:
            return name

    def get_child(self, name):
        if self.path:
            child_path = self.path + '/' + name
        else:
            child_path = name
        return self.project.get_resource(child_path)

    def has_child(self, name):
        try:
            self.get_child(name)
            return True
        except RopeError:
            return False

    def get_files(self):
        result = []
        for resource in self.get_children():
            if not resource.is_folder():
                result.append(resource)
        return result

    def get_folders(self):
        result = []
        for resource in self.get_children():
            if resource.is_folder():
                result.append(resource)
        return result

    def contains(self, resource):
        if self == resource:
            return False
        return self.path == '' or resource.path.startswith(self.path + '/')

    def create(self):
        self.parent.create_folder(self.name)
