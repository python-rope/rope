import os
import re

import rope.base.pycore
import rope.base.fscommands
from rope.base.exceptions import RopeException


class Project(object):
    """A Project containing files and folders"""

    def __init__(self, projectRootAddress):
        self.root = projectRootAddress
        if not os.path.exists(self.root):
            os.mkdir(self.root)
        elif not os.path.isdir(self.root):
            raise RopeException('Project root exists and is not a directory')
        self.pycore = rope.base.pycore.PyCore(self)
        self.resources = {}
        self.resources[''] = RootFolder(self)
        self.out_of_project_resources = {}
        self.fscommands = rope.base.fscommands.create_fscommands(self)

    def get_root_folder(self):
        return self.get_resource('')

    def get_root_address(self):
        return self.root

    def get_resource(self, resource_name):
        if resource_name not in self.resources:
            path = self._get_resource_path(resource_name)
            if not os.path.exists(path):
                raise RopeException('Resource %s does not exist' % resource_name)
            elif os.path.isfile(path):
                self.resources[resource_name] = File(self, resource_name)
            elif os.path.isdir(path):
                self.resources[resource_name] = Folder(self, resource_name)
            else:
                raise RopeException('Unknown resource ' + resource_name)
        return self.resources[resource_name]

    def get_files(self):
        return self._get_files_recursively(self.get_root_folder())

    def _create_file(self, file_name):
        file_path = self._get_resource_path(file_name)
        if os.path.exists(file_path):
            if os.path.isfile(file_path):
                raise RopeException('File already exists')
            else:
                raise RopeException('A folder with the same name'
                                    ' as this file already exists')
        try:
            self.fscommands.create_file(file_path)
        except IOError, e:
            raise RopeException(e)

    def _create_folder(self, folder_name):
        folder_path = self._get_resource_path(folder_name)
        if os.path.exists(folder_path):
            if not os.path.isdir(folder_path):
                raise RopeException('A file with the same name as'
                                    ' this folder already exists')
            else:
                raise RopeException('Folder already exists')
        self.fscommands.create_folder(folder_path)

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

    def remove_recursively(self, path):
        self.fscommands.remove(path)


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
            if destination != '':
                return destination + '/' + self.get_name()
            else:
                return self.get_name()
        return destination


class _File(Resource):
    """Represents a file in a project"""

    def __init__(self, project, name):
        super(_File, self).__init__(project, name)
    
    def read(self):
        source_bytes = self._read_file_data()
        return self._file_data_to_unicode(source_bytes)
    
    def _read_file_data(self):
        """Should be implemented in subclasses"""
    
    def _file_data_to_unicode(self, data):
        encoding = self._conclude_file_encoding(data)
        if encoding is not None:
            return unicode(data, encoding)
        return unicode(data)
    
    def _find_line_end(self, source_bytes, start):
        try:
            return source_bytes.index('\n', start)
        except ValueError:
            return len(source_bytes)
    
    def _get_second_line_end(self, source_bytes):
        line1_end = self._find_line_end(source_bytes, 0)
        if line1_end != len(source_bytes):
            return self._find_line_end(source_bytes, line1_end)
        else:
            return line1_end
    
    encoding_pattern = re.compile(r'coding[=:]\s*([-\w.]+)')
    
    def _conclude_file_encoding(self, source_bytes):
        first_two_lines = source_bytes[:self._get_second_line_end(source_bytes)]
        match = _File.encoding_pattern.search(first_two_lines)
        if match is not None:
            return match.group(1)

    def write(self, contents):
        file_ = open(self.project._get_resource_path(self.name), 'w')
        encoding = self._conclude_file_encoding(contents)
        if encoding is not None and isinstance(contents, unicode):
            contents = contents.encode(encoding)
        file_.write(contents)
        file_.close()
        for observer in list(self.observers):
            observer(self)
        self.get_parent()._child_changed(self)

    def is_folder(self):
        return False

    def remove(self):
        self.project.remove_recursively(self.project._get_resource_path(self.name))
        self.project._update_resource_location(self)
        for observer in list(self.observers):
            observer(self)
        self.get_parent()._child_changed(self)

    def move(self, new_location):
        destination = self._get_destination_for_move(new_location)
        self.project.fscommands.move(self.project._get_resource_path(self.name),
                                     self.project._get_resource_path(destination))
        self.project._update_resource_location(self, destination)
        self.get_parent()._child_changed(self)
        self.name = destination
        self.get_parent()._child_changed(self)
        for observer in list(self.observers):
            observer(self)
    

class File(_File):
    """Represents a file in a project"""

    def _read_file_data(self):
        return open(self.project._get_resource_path(self.name)).read()


class OutOfProjectFile(_File):
    """Represents a file outside a project"""

    def __init__(self, project, path):
        super(OutOfProjectFile, self).__init__(project, path)
        self.path = path
        
    def _read_file_data(self):
        return open(self.path).read()

    def _get_real_path(self):
        """Returns the file system path of this resource"""
        return self.path

    def get_parent(self):
        parent = '/'.join(self.path.split('/')[0:-1])
        return self.project.get_out_of_project_resource(parent)


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
        self.project.remove_recursively(self.project._get_resource_path(self.name))
        self.project._update_resource_location(self)
        self.get_parent()._child_changed(self)

    def move(self, new_location):
        destination = self._get_destination_for_move(new_location)
        self.project.fscommands.create_folder(self.project._get_resource_path(destination))
        for child in self.get_children():
            if not (child.is_folder() and child.get_name() == '.svn'):
                child.move(destination + '/' + child.get_name())
        self.project.fscommands.remove(self.project._get_resource_path(self.get_path()))
        self.project._update_resource_location(self, destination)
        self.get_parent()._child_changed(self)
        self.name = destination
        self.get_parent()._child_changed(self)
    
    def _child_changed(self, child):
        if child != self:
            for observer in list(self.observers):
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

    def get_parent(self):
        parent = '/'.join(self.path.split('/')[0:-1])
        return self.project.get_out_of_project_resource(parent)
