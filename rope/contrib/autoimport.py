from rope.base import exceptions, pynames, resourceobserver
from rope.refactor import importutils


class AutoImport(object):
    """A class for finding the module that provides a name

    This class maintains a cache of global names in python modules.
    Note that this cache is not accurate and might be out of date.

    """

    def __init__(self, project, observe=False):
        """Construct an AutoImport object

        If `observe` is `True`, listen for project changes and update
        the cache.

        """
        self.project = project
        self.names = project.data_files.read_data('globalnames')
        if self.names is None:
            self.names = {}
        project.data_files.add_write_hook(self._write)
        # XXX: using a filtered observer
        observer = resourceobserver.ResourceObserver(
            changed=self._changed, moved=self._moved, removed=self._removed)
        if observe:
            project.add_observer(observer)

    def import_assist(self, starting):
        """Return a list of ``(name, module)`` tuples

        This function tries to find modules that have a global name
        that starts with `starting`.

        """
        # XXX: breaking if gave up! use generators
        result = []
        for module in self.names:
            for global_name in self.names[module]:
                if global_name.startswith(starting):
                    result.append((global_name, module))
        return result

    def get_modules(self, name):
        """Return the list of modules that have global `name`"""
        result = []
        for module in self.names:
            if name in self.names[module]:
                result.append(module)
        return result

    def update_resource(self, resource):
        """Update the cache for global names in `resource`"""
        try:
            pymodule = self.project.pycore.resource_to_pyobject(resource)
            modname = self._module_name(resource)
            self._add_names(pymodule, modname)
        except exceptions.ModuleSyntaxError:
            pass

    def update_module(self, modname):
        """Update the cache for global names in `modname` module

        `modname` is the name of a module.
        """
        try:
            pymodule = self.project.pycore.get_module(modname)
            self._add_names(pymodule, modname)
        except exceptions.ModuleNotFoundError:
            pass

    def _module_name(self, resource):
        return importutils.get_module_name(self.project.pycore, resource)

    def _add_names(self, pymodule, modname):
        globals = []
        for name, pyname in pymodule._get_structural_attributes().items():
            if isinstance(pyname, (pynames.AssignedName, pynames.DefinedName)):
                globals.append(name)
        self.names[modname] = globals

    def _write(self):
        self.project.data_files.write_data('globalnames', self.names)

    def _changed(self, resource):
        if not resource.is_folder():
            self.update_resource(resource)

    def _moved(self, resource, newresource):
        if not resource.is_folder():
            modname = self._module_name(resource)
            if modname in self.names:
                del self.names[modname]
            self.update_resource(newresource)

    def _removed(self, resource):
        if not resource.is_folder():
            modname = self._module_name(resource)
            if modname in self.names:
                del self.names[modname]
