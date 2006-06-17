import os

import rope.codeassist
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
        self.code_assist = rope.codeassist.PythonCodeAssist(self)
        self.pycore = rope.pycore.PyCore(self)
        self.resources = {}
        self.resources[''] = RootFolder(self)

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
            if not os.path.isfile(filePath):
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

    def get_code_assist(self):
        return self.code_assist

    def get_pycore(self):
        return self.pycore

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
        Project.remove_recursively(self.project._get_resource_path(self.name))

    def is_folder(self):
        """Returns true if the resouse is a folder"""

    def get_project(self):
        """Returns the project this resource belongs to"""
        return self.project

    def add_change_observer(self, observer):
        pass

    def remove_change_observer(self, observer):
        pass

    def _get_real_path(self):
        """Returns the file system path of this resource"""
        return self.project._get_resource_path(self.name)

    def __hash__(self):
        return hash(self.get_path())

    def __eq__(self, resource):
        if type(resource) != type(self):
            return False
        return self.get_path() == resource.get_path()


class File(Resource):
    '''Represents a file in a project'''

    def __init__(self, project, name):
        super(File, self).__init__(project, name)
        self.observers = []
    
    def read(self):
        return open(self.project._get_resource_path(self.name)).read()

    def write(self, contents):
        file = open(self.project._get_resource_path(self.name), 'w')
        file.write(contents)
        file.close()
        for observer in self.observers:
            observer(self)

    def is_folder(self):
        return False

    def add_change_observer(self, observer):
        self.observers.append(observer)

    def remove_change_observer(self, observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def remove(self):
        super(File, self).remove()
        for observer in self.observers:
            observer(self)


class _Folder(Resource):
    """Represents a folder in a project"""

    def __init__(self, project, name):
        super(_Folder, self).__init__(project, name)


    def is_folder(self):
        return True

    def get_children(self):
        '''Returns the children resources of this folder'''
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
        return self.get_child(file_name)

    def create_folder(self, folder_name):
        if self.get_path():
            folder_path = self.get_path() + '/' + folder_name
        else:
            folder_path = folder_name
        self.project._create_folder(folder_path)
        return self.get_child(folder_name)

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



class Folder(_Folder):
    """Represents a non root folder in a project"""

    def __init__(self, project, folderName):
        super(Folder, self).__init__(project, folderName)


class RootFolder(_Folder):
    """Represents the root folder of a project"""

    def __init__(self, project):
        super(RootFolder, self).__init__(project, '')


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


