"""Project file system commands.

This modules implements file system operations used by rope.
Different version control systems can supported by implementing the
interface provided by `FileSystemCommands` class.

"""

import os
import shutil

try:
    import pysvn
except ImportError:
    pass


def create_fscommands(root):
    if 'pysvn' in globals() and '.svn' in os.listdir(root):
        return SubversionCommands()
    return FileSystemCommands()


class FileSystemCommands(object):
    
    def create_file(self, path):
        open(path, 'w').close()
    
    def create_folder(self, path):
        os.mkdir(path)
    
    def move(self, path, new_location):
        shutil.move(path, new_location)
    
    def remove(self, path):
        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)


class SubversionCommands(object):
    
    def __init__(self):
        self.normal_actions = FileSystemCommands()
        self.client = pysvn.Client()
    
    def create_file(self, path):
        self.normal_actions.create_file(path)
        self.client.add(path, force=True)
    
    def create_folder(self, path):
        self.normal_actions.create_folder(path)
        self.client.add(path, force=True)
    
    def move(self, path, new_location):
        self.client.move(path, new_location, force=True)
    
    def remove(self, path):
        self.client.remove(path, force=True)
