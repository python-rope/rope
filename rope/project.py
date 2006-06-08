import os
import sys
import subprocess

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
        self.code_assist = rope.codeassist.CodeAssist(self)
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

    def _is_package(self, folder):
        init_dot_py = folder.get_path() + '/__init__.py'
        try:
            init_dot_py_file = self.get_resource(init_dot_py)
            if not init_dot_py_file.is_folder():
                return True
        except RopeException:
            pass
        return False

    def _find_source_folders(self, folder):
        for resource in folder.get_folders():
            if self._is_package(resource):
                return [folder]
        result = []
        for resource in folder.get_files():
            if resource.get_name().endswith('.py'):
                result.append(folder)
        for resource in folder.get_folders():
            result.extend(self._find_source_folders(resource))
        return result

    def get_source_folders(self):
        return self._find_source_folders(self.get_root_folder())

    def create_module(self, src_folder, new_module):
        packages = new_module.split('.')
        parent = src_folder
        for package in packages[:-1]:
            parent = parent.get_child(package)
        return parent.create_file(packages[-1] + '.py')

    def create_package(self, src_folder, new_package):
        packages = new_package.split('.')
        parent = src_folder
        for package in packages[:-1]:
            parent = parent.get_child(package)
        created_package = parent.create_folder(packages[-1])
        created_package.create_file('__init__.py')
        return created_package

    def find_module(self, module_name):
        source_folders = self.get_source_folders()
        packages = module_name.split('.')
        result = []
        for src in source_folders:
            module = src
            found = True
            for pkg in packages[:-1]:
                if  module.is_folder() and module.has_child(pkg):
                    module = module.get_child(pkg)
                else:
                    found = False
                    break

            if module.is_folder() and module.has_child(packages[-1]) and\
               module.get_child(packages[-1]).is_folder():
                module = module.get_child(packages[-1])
            elif module.is_folder() and module.has_child(packages[-1] + '.py') and\
               not module.get_child(packages[-1] + '.py').is_folder():
                module = module.get_child(packages[-1] + '.py')
            else:
                found = False
            if found:
                result.append(module)
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

    def remove(self):
        """Removes resource from the project"""

    def get_name(self):
        """Returns the name of this resource"""
    
    def get_path(self):
        """Returns the path of this resource relative to the project root
        
        The path is the list of parent directories separated by '/' followed
        by the resource name.
        """

    def is_folder(self):
        """Returns true if the resouse is a folder"""

    def get_project(self):
        """Returns the project this resource belongs to"""

    def add_change_observer(self, observer):
        pass

    def _get_real_path(self):
        """Returns the file system path of this resource"""

    def __hash__(self):
        return hash(self.get_path())

    def __eq__(self, resource):
        if type(resource) != type(self):
            return False
        return self.get_path() == resource.get_path()


class File(Resource):
    '''Represents a file in a project'''

    def __init__(self, project, fileName):
        self.project = project
        self.fileName = fileName
        self.observers = []
    
    def read(self):
        return open(self.project._get_resource_path(self.fileName)).read()

    def write(self, contents):
        file = open(self.project._get_resource_path(self.fileName), 'w')
        file.write(contents)
        file.close()
        for observer in self.observers:
            observer(self)

    def remove(self):
        Project.remove_recursively(self.project._get_resource_path(self.fileName))

    def get_name(self):
        return self.fileName.split('/')[-1]

    def get_path(self):
        return self.fileName

    def is_folder(self):
        return False

    def add_change_observer(self, observer):
        self.observers.append(observer)

    def _get_real_path(self):
        return self.project._get_resource_path(self.fileName)

    def get_project(self):
        return self.project


class _Folder(Resource):
    """Represents a folder in a project"""

    def __init__(self, project, folderName):
        self.project = project
        self.folderName = folderName

    def _get_real_path(self):
        return self.project._get_resource_path(self.folderName)
    
    def remove(self):
        Project.remove_recursively(self.project._get_resource_path(self.folderName))

    def get_name(self):
        return self.folderName.split('/')[-1]

    def get_path(self):
        return self.folderName

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

    def get_project(self):
        return self.project

    def _get_real_path(self):
        return self.project._get_resource_path(self.folderName)


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


class PythonFileRunner(object):
    """A class for running python project files"""

    def __init__(self, file, stdin=None, stdout=None):
        self.file = file
        file_path = self.file._get_real_path()
        env = {}
        env.update(os.environ)
        source_folders = []
        for folder in file.get_project().get_source_folders():
            source_folders.append(os.path.abspath(folder._get_real_path()))
        env['PYTHONPATH'] = env.get('PYTHONPATH', '') + os.pathsep + \
                            os.pathsep.join(source_folders)
        self.process = subprocess.Popen(executable=sys.executable,
                                        args=(sys.executable, self.file.get_name()),
                                        cwd=os.path.split(file_path)[0], stdin=stdin,
                                        stdout=stdout, stderr=stdout, env=env)

    def wait_process(self):
        """Wait for the process to finish"""
        self.process.wait()

    def kill_process(self):
        """Stop the process. This does not work on windows."""
        os.kill(self.process.pid, 9)
