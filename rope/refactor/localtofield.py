from rope.base import evaluate, exceptions, pynames, worder
from rope.refactor.rename import Rename


class LocalToField:
    """Convert a method local to a field, rejecting invalid selections at construction."""

    def __init__(self, project, resource, offset):
        self.project = project
        self.resource = resource
        self.offset = offset
        self._get_method_scope()

    def get_changes(self):
        name = worder.get_name_at(self.resource, self.offset)
        function_scope = self._get_method_scope()
        # Not checking redefinition
        # self._check_redefinition(name, function_scope)

        new_name = self._get_field_name(function_scope.pyobject, name)
        changes = Rename(self.project, self.resource, self.offset).get_changes(
            new_name, resources=[self.resource]
        )
        return changes

    def _check_redefinition(self, name, function_scope):
        class_scope = function_scope.parent
        if name in class_scope.pyobject:
            raise exceptions.RefactoringError("The field %s already exists" % name)

    def _get_field_name(self, pyfunction, name):
        self_name = pyfunction.get_param_names()[0]
        new_name = self_name + "." + name
        return new_name

    def _get_method_scope(self):
        pymodule = self.project.get_pymodule(self.resource)
        pyname = evaluate.eval_location(pymodule, self.offset)
        if isinstance(pyname, pynames.AssignedName):
            definition_module, lineno = pyname.get_definition_location()
            scope = definition_module.get_scope().get_inner_scope_for_line(lineno)
            if (
                scope.get_kind() == "Function"
                and scope.parent is not None
                and scope.parent.get_kind() == "Class"
                and pyname in scope.get_names().values()
            ):
                return scope
        raise exceptions.RefactoringError(
            "Convert local variable to field should be performed on "
            "a local variable of a method."
        )
