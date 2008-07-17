from rope.base import ast, evaluate


def find_errors(project, resource):
    pymodule = project.pycore.resource_to_pyobject(resource)
    finder = _BadAccessFinder(pymodule)
    ast.walk(pymodule.get_ast(), finder)
    return finder.errors


class _BadAccessFinder(object):

    def __init__(self, pymodule):
        self.pymodule = pymodule
        self.scope = pymodule.get_scope()
        self.errors = []

    def _Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Param)):
            return
        scope = self.scope.get_inner_scope_for_line(node.lineno)
        pyname = scope.lookup(node.id)
        if pyname is None:
            self._add_error(node, 'Unresolved variable')
        elif self._is_defined_after(scope, pyname, node.lineno):
            self._add_error(node, 'Defined later')

    def _add_error(self, node, msg):
        error = Error(node.lineno, msg + ' %s' % node.id)
        self.errors.append(error)

    def _is_defined_after(self, scope, pyname, lineno):
        location = pyname.get_definition_location()
        if location is not None and location[1] is not None:
            if location[0] == self.pymodule and \
               lineno <= location[1] <= scope.get_end():
                return True


class Error(object):

    def __init__(self, lineno, error):
        self.lineno = lineno
        self.error = error

    def __str__(self):
        return '%s: %s' % (self.lineno, self.error)
