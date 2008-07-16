from rope.base import change
from rope.contrib import changestack
from rope.refactor import rename


class FixModuleNames(object):

    def __init__(self, project):
        self.project = project

    def get_changes(self):
        stack = changestack.ChangeStack(self.project, 'Fixing module names')
        try:
            for resource in self.project.pycore.get_python_files():
                modname = resource.name.rsplit('.', 1)[0]
                if not modname.islower():
                    renamer = rename.Rename(self.project, resource)
                    changes = renamer.get_changes(modname.lower())
                    stack.push(changes)
        finally:
            stack.pop_all()
        return stack.merged()
