"""rope refactor package

This package contains modules that perform python refactorings.
Refactoring classes perform refactorings in 4 steps:

1. Collect some data for performing the refactoring and use them
   to construct a refactoring class.  Like::

     renamer = Rename(project, resource, offset)

2. Some refactorings give you useful information about the
   refactoring after their construction.  Like::

     print(renamer.get_old_name())

3. Give the refactoring class more information about how to
   perform the refactoring and get the changes this refactoring is
   going to make.  This is done by calling `get_changes` method of the
   refactoring class.  Like::

     changes = renamer.get_changes(new_name)

4. You can commit the changes.  Like::

     project.do(changes)

These steps are like the steps IDEs usually do for performing a
refactoring.  These are the things an IDE does in each step:

1. Construct a refactoring object by giving it information like
   resource, offset and ... .  Some of the refactoring problems (like
   performing rename refactoring on language keywords) can be reported
   here.
2. Print some information about the refactoring and ask the user
   about the information that are necessary for completing the
   refactoring (like new name).
3. Call the `get_changes` by passing it information asked from
   the user (if necessary) and get and preview the changes returned by
   it.
4. perform the refactoring.

From ``0.5m5`` release the `get_changes()` method of some time-
consuming refactorings take an optional `rope.base.taskhandle.
TaskHandle` parameter.  You can use this object for stopping or
monitoring the progress of refactorings.

"""
import rope.refactor.importutils
from rope.base import exceptions
from rope.base.change import ChangeSet, ChangeContents, MoveResource, CreateFolder
from rope.refactor.importutils import module_imports


class ModuleToPackage(object):

    def __init__(self, project, resource):
        self.project = project
        self.pycore = project.pycore
        self.resource = resource

    def get_changes(self):
        changes = ChangeSet('Transform <%s> module to package' %
                            self.resource.path)
        new_content = self._transform_relatives_to_absolute(self.resource)
        if new_content is not None:
            changes.add_change(ChangeContents(self.resource, new_content))
        parent = self.resource.parent
        name = self.resource.name[:-3]
        changes.add_change(CreateFolder(parent, name))
        parent_path = parent.path + '/'
        if not parent.path:
            parent_path = ''
        new_path = parent_path + '%s/__init__.py' % name
        changes.add_change(MoveResource(self.resource, new_path))
        return changes

    def _transform_relatives_to_absolute(self, resource):
        pymodule = self.pycore.resource_to_pyobject(resource)
        import_tools = rope.refactor.importutils.ImportTools(self.pycore)
        return import_tools.relatives_to_absolutes(pymodule)


class ImportOrganizer(object):

    def __init__(self, project):
        self.project = project
        self.pycore = project.pycore
        self.import_tools = rope.refactor.importutils.ImportTools(self.pycore)

    def _perform_command_on_import_tools(self, method, resource):
        pymodule = self.pycore.resource_to_pyobject(resource)
        before_performing = pymodule.source_code
        result = method(pymodule)
        if result is not None and result != before_performing:
            changes = ChangeSet(method.__name__.replace('_', ' ') +
                                ' in <%s>' % resource.path)
            changes.add_change(ChangeContents(resource, result))
            return changes

    def organize_imports(self, resource):
        return self._perform_command_on_import_tools(
            self.import_tools.organize_imports, resource)

    def expand_star_imports(self, resource):
        return self._perform_command_on_import_tools(
            self.import_tools.expand_stars, resource)

    def froms_to_imports(self, resource):
        return self._perform_command_on_import_tools(
            self.import_tools.froms_to_imports, resource)

    def relatives_to_absolutes(self, resource):
        return self._perform_command_on_import_tools(
            self.import_tools.relatives_to_absolutes, resource)

    def handle_long_imports(self, resource):
        return self._perform_command_on_import_tools(
            self.import_tools.handle_long_imports, resource)
