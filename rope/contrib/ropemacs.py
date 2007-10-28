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

    @interaction('DRope Project Root Folder: ')
    def set_project(self, root):
        if self.project is not None:
            self.close_project()
        self.project = project.Project(root)

    @interaction()
    def close_project(self):
        self.project.close()

    @interaction('sNew Name: ')
    def rename(self, newname):
        self._check_project()
        lisp.save_some_buffers()
        filename = lisp.buffer_file_name()
        resource = libutils.path_to_resource(self.project, filename)
        offset = lisp.point_min() + lisp.point()
        renamer = rope.refactor.rename.Rename(self.project, resource, 1)
        changes = renamer.get_changes(newname)
        self.project.do(changes)
        self._reload_buffers(changes.get_changed_resources())

    @interaction()
    def hey(self):
        pass

    def _check_project(self):
        if self.project is None:
            lisp.call_interactively(lisp.rope_set_project)

    def _reload_buffers(self, changed_resources):
        for resource in changed_resources:
            buffer = lisp.find_buffer_visiting(resource.real_path)
            if buffer:
                lisp.set_buffer(buffer)
                lisp.revert_buffer(None, 1)


interface = RopeInterface()
init = interface.init

set_project = interface.set_project
close_project = interface.close_project
rename = interface.rename
