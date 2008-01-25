from rope.base import exceptions, pynames, resourceobserver
from rope.refactor import importutils


class AutoImport(object):

    def __init__(self, project, observe=False):
        self.project = project
        self.names = project.data_files.read_data('globalnames')
        if self.names is None:
            self.names = {}
        project.data_files.add_write_hook(self.write)
        # XXX: handle moved and removed
        observer = resourceobserver.ResourceObserver(
            changed=self._changed, moved=self._moved)
        if observe:
            project.add_observer(observer)

    def write(self):
        self.project.data_files.write_data('globalnames', self.names)

    def import_assist(self, starting):
        # XXX: breaking if gave up! use generators
        result = []
        for module in self.names:
            for global_name in self.names[module]:
                if global_name.startswith(starting):
                    result.append((global_name, module))
        return result

    def get_modules(self, name):
        result = []
        for module in self.names:
            if name in self.names[module]:
                result.append(module)
        return result

    def update_resource(self, resource):
        try:
            pymodule = self.project.pycore.resource_to_pyobject(resource)
            modname = self._module_name(resource)
            self._add_names(pymodule, modname)
        except exceptions.ModuleSyntaxError:
            pass

    def _module_name(self, resource):
        return importutils.get_module_name(self.project.pycore, resource)

    def _add_names(self, pymodule, modname):
        # XXX: exclude imported names
        globals = []
        for name, pyname in pymodule._get_structural_attributes().items():
            if isinstance(pyname, (pynames.AssignedName, pynames.DefinedName)):
                globals.append(name)
        self.names[modname] = globals

    def update_module(self, modname):
        try:
            pymodule = self.project.pycore.get_module(modname)
            self._add_names(pymodule, modname)
        except exceptions.ModuleNotFoundError:
            pass

    def _changed(self, resource):
        if not resource.is_folder():
            self.update_resource(resource)

    def _moved(self, resource, newresource):
        if not resource.is_folder():
            modname = self._module_name(resource)
            if modname in self.names:
                del self.names[modname]
            self.update_resource(newresource)
