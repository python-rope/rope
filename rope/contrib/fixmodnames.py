"""Fix the name of modules"""
from rope.base import change, taskhandle
from rope.contrib import changestack
from rope.refactor import rename


class FixModuleNames(object):

    def __init__(self, project):
        self.project = project

    def get_changes(self, fixer=str.lower,
                    task_handle=taskhandle.NullTaskHandle()):
        """Fix module names

        `fixer` is a function that takes and returns a `str`.  Given
        the name of a module, it should return the fixed name.

        """
        stack = changestack.ChangeStack(self.project, 'Fixing module names')
        try:
            while True:
                for resource in self.project.pycore.get_python_files():
                    modname = resource.name.rsplit('.', 1)[0]
                    if modname == '__init__':
                        modname = resource.parent.name
                    if modname != fixer(modname):
                        renamer = rename.Rename(self.project, resource)
                        changes = renamer.get_changes(modname.lower(),
                                                      task_handle=handle)
                        stack.push(changes)
                        break
                else:
                    break
        finally:
            stack.pop_all()
        return stack.merged()
