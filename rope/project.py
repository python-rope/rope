import os
import shutil

import rope.pycore
from rope.exceptions import RopeException


class Project(object):
    """A Project containing files and folders"""

    def __init__(self, projectRootAddress):
        self.root = projectRootAddress
        if not os.path.exists(self.root):
            os.mkdir(self.root)
        elif not os.path.isdir(self.root):
            raise RopeException('Project root exists and is not a directory')
        self.pycore = rope.pycore.PyCore(self)
        self.resources = {}
        self.resources[''] = RootFolder(self)
        self.out_of_project_resources = {}

    def get_root_folder(self):
        return self.get_resource('')

    def get_root_address(self):
        return self.root

    def get_resource(self, resourceName):
        if resourceName not in self.resources:
            path = self._get_resource_path(resourceName)
            if not os.path.exists(path):
                raise RopeException('Resource %s does not exist' % resourceName)
            elif os.path.isfile(path):
                self.resources[resourceName] = File(self, resourceName)
            elif os.path.isdir(path):
                self.resources[resourceName] = Folder(self, resourceName)
            else:
                raise RopeException('Unknown resource ' + resourceName)
        return self.resources[resourceName]

    def get_files(self):
        return self._get_files_recursively(self.get_root_folder())

    def _create_file(self, fileName):
        filePath = self._get_resource_path(fileName)
        if os.path.exists(filePath):
            if os.path.isfile(filePath):
                raise RopeException('File already exists')
            else:
                raise RopeException('A folder with the same name as this file already exists')
        try:
            newFile = open(filePath, 'w')
        except IOError, e:
            raise RopeException(e)
        newFile.close()

    def _create_folder(self, folderName):
        folderPath = self._get_resource_path(folderName)
        if os.path.exists(folderPath):
            if not os.path.isdir(folderPath):
                raise RopeException('A file with the same name as this folder already exists')
            else:
                raise RopeException('Folder already exists')
        os.mkdir(folderPath)

    def _get_resource_path(self, name):
        return os.path.join(self.root, *name.split('/'))

    def _get_files_recursively(self, folder):
        result = []
        for file in folder.get_files():
            if not file.get_name().endswith('.pyc'):
                result.append(file)
        for folder in folder.get_folders():
            if not folder.get_name().startswith('.'):
                result.extend(self._get_files_recursively(folder))
        return result

    def get_pycore(self):
        return self.pycore

    def get_out_of_project_resource(self, path):
        path = os.path.abspath(path)
        if path not in self.out_of_project_resources:
            if not os.path.exists(path):
                raise RopeException('Resource %s does not exist' % path)
            elif os.path.isfile(path):
                self.out_of_project_resources[path] = OutOfProjectFile(self, path)
            elif os.path.isdir(path):
                self.out_of_project_resources[path] = OutOfProjectFolder(self, path)
            else:
                raise RopeException('Unknown resource ' + path)
        return self.out_of_project_resources[path]
    
    def _update_resource_location(self, resource, new_location=None):
        del self.resources[resource.get_path()]
        if new_location is not None:
            self.resources[new_location] = resource

    @staticmethod
    def remove_recursively(file):
        for root, dirs, files in os.walk(file, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        if os.path.isdir(file):
            os.rmdir(file)
        else:
            os.remove(file)


class Resource(object):
    """Represents files and folders in a project"""

    def __init__(self, project, name):
        self.project = project
        self.name = name
        self.observers = []

    def get_path(self):
        """Returns the path of this resource relative to the project root
        
        The path is the list of parent directories separated by '/' followed
        by the resource name.
        """
        return self.name

    def get_name(self):
        """Returns the name of this resource"""
        return self.name.split('/')[-1]
    
    def remove(self):
        """Removes resource from the project"""
    
    def move(self, new_location):
        """Moves resource to new_lcation"""

    def is_folder(self):
        """Returns true if the resource is a folder"""

    def get_project(self):
        """Returns the project this resource belongs to"""
        return self.project

    def add_change_observer(self, observer):
        self.observers.append(observer)

    def remove_change_observer(self, observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def get_parent(self):
        parent = '/'.join(self.name.split('/')[0:-1])
        return self.project.get_resource(parent)

    def _get_real_path(self):
        """Returns the file system path of this resource"""
        return self.project._get_resource_path(self.name)
    
    def _get_destination_for_move(self, destination):
        dest_path = self.project._get_resource_path(destination)
        if os.path.isdir(dest_path):
            return destination + '/' + self.get_name()
        return destination


class _File(Resource):
    """Represents a file in a project"""

    def __init__(self, project, name):
        super(_File, self).__init__(project, name)
    
    def read(self):
        return open(self.project._get_resource_path(self.name)).read()

    def write(self, contents):
        file = open(self.project._get_resource_path(self.name), 'w')
        file.write(contents)
        file.close()
        for observer in self.observers:
            observer(self)
        self.get_parent()._child_changed(self)

    def is_folder(self):
        return False

    def remove(self):
        Project.remove_recursively(self.project._get_resource_path(self.name))
        self.project._update_resource_location(self)
        for observer in self.observers:
            observer(self)
        self.get_parent()._child_changed(self)

    def move(self, new_location):
        destination = self._get_destination_for_move(new_location)
        shutil.move(self.project._get_resource_path(self.name),
                    self.project._get_resource_path(destination))
        self.project._update_resource_location(self, destination)
        self.get_parent()._child_changed(self)
        self.name = destination
        self.get_parent()._child_changed(self)


class File(_File):
    """Represents a file in a project"""


class OutOfProjectFile(_File):
    """Represents a file outside a project"""

    def __init__(self, project, path):
        super(OutOfProjectFile, self).__init__(project, path)
        self.path = path
        
    def read(self):
        return open(self.path).read()

    def _get_real_path(self):
        """Returns the file system path of this resource"""
        return self.path


class _Folder(Resource):
    """Represents a folder in a project"""

    def __init__(self, project, name):
        super(_Folder, self).__init__(project, name)


    def is_folder(self):
        return True

    def get_children(self):
        """Returns the children resources of this folder"""
        path = self._get_real_path()
        result = []
        content = os.listdir(path)
        for name in content:
            if self.get_path() != '':
                resource_name = self.get_path() + '/' + name
            else:
                resource_name = name
            result.append(self.project.get_resource(resource_name))
        return result

    def create_file(self, file_name):
        if self.get_path():
            file_path = self.get_path() + '/' + file_name
        else:
            file_path = file_name
        self.project._create_file(file_path)
        child = self.get_child(file_name)
        self._child_changed(child)
        return child

    def create_folder(self, folder_name):
        if self.get_path():
            folder_path = self.get_path() + '/' + folder_name
        else:
            folder_path = folder_name
        self.project._create_folder(folder_path)
        child = self.get_child(folder_name)
        self._child_changed(child)
        return child

    def get_child(self, name):
        if self.get_path():
            child_path = self.get_path() + '/' + name
        else:
            child_path = name
        return self.project.get_resource(child_path)
    
    def has_child(self, name):
        try:
            self.get_child(name)
            return True
        except RopeException:
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

    def remove(self):
        for child in self.get_children():
            child.remove()
        Project.remove_recursively(self.project._get_resource_path(self.name))
        self.project._update_resource_location(self)
        self.get_parent()._child_changed(self)

    def move(self, new_location):
        destination = self._get_destination_for_move(new_location)
        os.makedirs(self.project._get_resource_path(destination))
        for child in self.get_children():
            child.move(destination + '/' + child.get_name())
        shutil.rmtree(self.project._get_resource_path(self.get_path()))
        self.project._update_resource_location(self, destination)
        self.get_parent()._child_changed(self)
        self.name = destination
        self.get_parent()._child_changed(self)
    
    def _child_changed(self, child):
        if child != self:
            for observer in self.observers:
                observer(self)


class Folder(_Folder):
    """Represents a non root folder in a project"""

    def __init__(self, project, folderName):
        super(Folder, self).__init__(project, folderName)


class RootFolder(_Folder):
    """Represents the root folder of a project"""

    def __init__(self, project):
        super(RootFolder, self).__init__(project, '')


class OutOfProjectFolder(_Folder):
    """Represents a folder outside the project"""

    def __init__(self, project, path):
        super(OutOfProjectFolder, self).__init__(project, path)
        self.path = path
    
    def get_children(self):
        result = []
        content = os.listdir(self.path)
        for name in content:
            resource_path = os.path.join(self.path, name)
            result.append(self.project.get_out_of_project_resource(resource_path))
        return result

    def get_child(self, name):
        child_path = os.path.join(self.path, name)
        return self.project.get_out_of_project_resource(child_path)
    
    def _get_real_path(self):
        """Returns the file system path of this resource"""
        return self.path


class FileFinder(object):

    def __init__(self, project):
        self.project = project
        self.last_keyword = None
        self.last_result = None

    def find_files_starting_with(self, starting):
        """Returns the Files in the project whose names starts with starting"""
        files = []
        if self.last_keyword is not None and starting.startswith(self.last_keyword):
            files = self.last_result
        else:
            files = self.project.get_files()
        result = []
        for file in files:
            if file.get_name().startswith(starting):
                result.append(file)
        self.last_keyword = starting
        self.last_result = result
        return result

