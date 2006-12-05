import os
import re

import rope.base.pycore
import rope.base.fscommands
from rope.base.exceptions import RopeException


class _Project(object):
    
    def __init__(self, fscommands):
        self.fscommands = fscommands
        self.robservers = {}
        self.observers = set()
    
    def add_observer(self, observer):
        self.observers.add(observer)
    
    def remove_observer(self, observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def get_resource(self, resource_name):
        path = self._get_resource_path(resource_name)
        if not os.path.exists(path):
            raise RopeException('Resource %s does not exist' % resource_name)
        elif os.path.isfile(path):
            return File(self, resource_name)
        elif os.path.isdir(path):
            return Folder(self, resource_name)
        else:
            raise RopeException('Unknown resource ' + resource_name)

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
        pass

    def remove_recursively(self, path):
        self.fscommands.remove(path)


class Project(_Project):
    """A Project containing files and folders"""

    def __init__(self, project_root):
        self.root = project_root
        if not os.path.exists(self.root):
            os.mkdir(self.root)
        elif not os.path.isdir(self.root):
            raise RopeException('Project root exists and is not a directory')
        fscommands = rope.base.fscommands.create_fscommands(self.root)
        super(Project, self).__init__(fscommands)
        self.pycore = rope.base.pycore.PyCore(self)
        self.no_project = NoProject()

    def get_root_folder(self):
        return self.get_resource('')

    def get_root_address(self):
        return self.root

    def get_files(self):
        return self._get_files_recursively(self.get_root_folder())

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
        return self.no_project.get_resource(path)
    

class NoProject(_Project):
    """A null object for holding out of project files"""
    
    def __init__(self):
        fscommands = rope.base.fscommands.FileSystemCommands()
        super(NoProject, self).__init__(fscommands)
    
    def _get_resource_path(self, name):
        return os.path.abspath(name)
    
    def get_resource(self, name):
        return super(NoProject, self).get_resource(os.path.abspath(name))


class Resource(object):
    """Represents files and folders in a project"""

    def __init__(self, project, name):
        self.project = project
        self.name = name
        
    def _get_observers(self):
        return self.project.observers
    
    observers = property(_get_observers)

    def get_path(self):
        """Return the path of this resource relative to the project root
        
        The path is the list of parent directories separated by '/' followed
        by the resource name.
        """
        return self.name

    def get_name(self):
        """Return the name of this resource"""
        return self.name.split('/')[-1]
    
    def move(self, new_location):
        """Move resource to new_lcation"""
        destination = self._get_destination_for_move(new_location)
        self.project.fscommands.move(self._get_real_path(),
                                     self.project._get_resource_path(destination))
        new_resource = self.project.get_resource(destination)
        for observer in list(self.observers):
            observer.resource_removed(self, new_resource)
    
    def remove(self):
        """Remove resource from the project"""
        self.project.remove_recursively(self._get_real_path())
        for observer in list(self.observers):
            observer.resource_removed(self)
    
    def is_folder(self):
        """Return true if the resource is a folder"""
    
    def exists(self):
        os.path.exists(self._get_real_path())

    def get_parent(self):
        parent = '/'.join(self.name.split('/')[0:-1])
        return self.project.get_resource(parent)

    def _get_real_path(self):
        """Return the file system path of this resource"""
        return self.project._get_resource_path(self.name)
    
    def _get_destination_for_move(self, destination):
        dest_path = self.project._get_resource_path(destination)
        if os.path.isdir(dest_path):
            if destination != '':
                return destination + '/' + self.get_name()
            else:
                return self.get_name()
        return destination
    
    def __eq__(self, obj):
        return self.__class__ == obj.__class__ and self.name == obj.name
    
    def __hash__(self):
        return hash(self.name)


class File(Resource):
    """Represents a file"""

    def __init__(self, project, name):
        super(File, self).__init__(project, name)
    
    def read(self):
        source_bytes = open(self._get_real_path()).read()
        return self._file_data_to_unicode(source_bytes)
    
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
        match = File.encoding_pattern.search(first_two_lines)
        if match is not None:
            return match.group(1)

    def write(self, contents):
        file_ = open(self._get_real_path(), 'w')
        encoding = self._conclude_file_encoding(contents)
        if encoding is not None and isinstance(contents, unicode):
            contents = contents.encode(encoding)
        file_.write(contents)
        file_.close()
        for observer in list(self.observers):
            observer.resource_changed(self)

    def is_folder(self):
        return False


class Folder(Resource):
    """Represents a folder"""

    def __init__(self, project, name):
        super(Folder, self).__init__(project, name)

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
        for observer in list(self.observers):
            observer.resource_changed(child)
        return child

    def create_folder(self, folder_name):
        if self.get_path():
            folder_path = self.get_path() + '/' + folder_name
        else:
            folder_path = folder_name
        self.project._create_folder(folder_path)
        child = self.get_child(folder_name)
        for observer in list(self.observers):
            observer.resource_changed(child)
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
    
    def contains(self, resource):
        return self != resource and resource.get_path().startswith(self.get_path())

    def _child_changed(self, child):
        if child != self:
            for observer in list(self.observers):
                observer.resource_changed(self)


class ResourceObserver(object):
    """Provides the interface observing resources
    
    `ResourceObserver` s can be registered using `Resource.add_observer`.
    """
    
    def __init__(self, changed, removed):
        self.changed = changed
        self.removed = removed
    
    def resource_changed(self, resource):
        """It is called when the resource changes"""
        self.changed(resource)
    
    def resource_removed(self, resource, new_resource=None):
        """It is called when a resource no longer exists
        
        `new_resource` is the destination if we know it, otherwise it
        is None.
        """
        self.removed(resource, new_resource)


class FilteredResourceObserver(object):
    
    def __init__(self, resources_getter, resource_observer):
        self._resources_getter = resources_getter
        self.observer = resource_observer
    
    def _get_resources(self):
        return self._resources_getter()
    
    resources = property(_get_resources)
    
    def resource_changed(self, changed):
        if changed in self.resources:
            self.observer.resource_changed(changed)
        self._parents_changed(changed)
    
    def resource_removed(self, resource, new_resource=None):
        if resource in self.resources:
            self.observer.resource_removed(resource, new_resource)
        if resource.is_folder():
            for file in self.resources:
                if resource.contains(file):
                    new_file = self._calculate_new_resource(resource, new_resource, file)
                    self.observer.resource_removed(file, new_file)
        self._parents_changed(resource)
        if new_resource is not None:
            self._parents_changed(new_resource)
    
    def _parents_changed(self, child):
        for resource in self.resources:
            if resource.is_folder() and child.get_parent() == resource:
                self.observer.resource_changed(resource)

    def _calculate_new_resource(self, main, new_main, resource):
        if new_main is None:
            return None
        diff = resource.get_path()[:len(main.get_path())]
        return new_main.get_path() + diff
