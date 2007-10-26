import os

from Pymacs import lisp

import rope.refactor.rename
from rope.base import project, libutils


class interaction(object):

    def __init__(self, mode=''):
        self.mode = mode

    def __call__(self, func):
        func.interaction = self.mode
        return func

class RopeInterface(object):

    def __init__(self):
        self.project = None

    def init(self):
        """Initialize rope mode"""
        #lisp.global_set_key(lisp.kbd('C-c r r'), lisp.rope_rename)

    @interaction('DProject Root Folder: ')
    def set_project(self, root):
        if self.project is not None:
            self.close_project()
        self.project = project.Project(root)

    @interaction()
    def close_project(self):
        self.project.close()

    @interaction('sNew Name: ')
    def rename(self, newname):
        lisp.save_some_buffers()
        filename = lisp.buffer_file_name()
        resource = libutils.path_to_resource(self.project, filename)
        renamer = rope.refactor.rename.Rename(self.project, resource, 1)
        self.project.do(renamer.get_changes(newname))


interface = RopeInterface()
init = interface.init

set_project = interface.set_project
close_project = interface.close_project
rename = interface.rename
