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


def get_project(root='.'):
    return project.Project(root)

@interaction('sNew Name: ')
def rename(newname):
    lisp.save_some_buffers()
    filename = lisp.buffer_file_name()
    project = get_project(os.path.dirname(filename))
    resource = libutils.path_to_resource(project, filename)
    renamer = rope.refactor.rename.Rename(project, resource, 1)
    project.do(renamer.get_changes(newname))
    project.close()

def init():
    """Initialize rope mode"""
    #lisp.global_set_key(lisp.kbd('C-c r r'), lisp.rope_rename)
