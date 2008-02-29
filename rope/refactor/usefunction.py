from rope.base import (change, taskhandle, evaluate,
                       exceptions, pyobjects, pynames, ast)
from rope.refactor import restructure, sourceutils, similarfinder, importutils


class UseFunction(object):
    """Try to use a function wherever possible"""

    def __init__(self, project, resource, offset):
        self.project = project
        self.offset = offset
        this_pymodule = project.pycore.resource_to_pyobject(resource)
        pyname = evaluate.get_pyname_at(this_pymodule, offset)
        if pyname is None:
            raise exceptions.RefactoringError('Unresolvable name selected')
        self.pyfunction = pyname.get_object()
        if not isinstance(self.pyfunction, pyobjects.PyFunction) or \
           not isinstance(self.pyfunction.parent, pyobjects.PyModule):
            raise exceptions.RefactoringError(
                'Use function works for global functions, only.')
        self.resource = self.pyfunction.get_module().get_resource()
        self._check_returns()

    def _check_returns(self):
        class CountReturns(object):
            returns = 0
            yields = 0
            def __call__(self, node):
                if isinstance(node, ast.Return):
                    self.returns += 1
                if isinstance(node, ast.Yield):
                    self.yields += 1
        counter = CountReturns()
        node = self.pyfunction.get_ast()
        ast.call_for_nodes(node, counter, recursive=True)
        if counter.yields:
            raise exceptions.RefactoringError('Use function should not '
                                              'be used on generators.')
        if counter.returns > 1:
            raise exceptions.RefactoringError(
                'usefunction: Function has more than '
                'one return statement.')
        if counter.returns == 1 and not isinstance(node.body[-1], ast.Return):
            raise exceptions.RefactoringError(
                'usefunction: return should be the last statement.')

    def get_changes(self, resources=None,
                    task_handle=taskhandle.NullTaskHandle()):
        if resources is None:
            resources = self.project.pycore.get_python_files()
        changes = change.ChangeSet('Using function <%s>' %
                                   self.pyfunction.get_name())
        if self.resource in resources:
            newresources = list(resources)
            newresources.remove(self.resource)
        for c in self._restructure(newresources, task_handle).changes:
            changes.add_change(c)
        if self.resource in resources:
            for c in self._restructure([self.resource], task_handle,
                                       others=False).changes:
                changes.add_change(c)
        return changes

    def get_function_name(self):
        return self.pyfunction.get_name()

    def _restructure(self, resources, task_handle, others=True):
        body = self._get_body()
        pattern = self._make_pattern()
        goal = self._make_goal(import_=others)
        imports = None
        if others:
            imports = ['import %s' % self._module_name()]

        body_region = sourceutils.get_body_region(self.pyfunction)
        args_value = {'skip': (self.resource, body_region)}
        args = {'': args_value}

        restructuring = restructure.Restructure(
            self.project, pattern, goal, args=args, imports=imports)
        return restructuring.get_changes(resources=resources,
                                         task_handle=task_handle)

    def _find_temps(self):
        return find_temps(self.project, self._get_body())

    def _module_name(self):
        return importutils.get_module_name(self.project.pycore,
                                           self.resource)

    def _make_pattern(self):
        params = self.pyfunction.get_param_names()
        body = self._get_body()
        body = restructure.replace(body, 'return', 'pass')
        wildcards = list(params)
        wildcards.extend(self._find_temps())
        if self._does_return():
            if self._is_expression():
                replacement = '${%s}' % self._rope_returned
            else:
                replacement = '%s = ${%s}' % (self._rope_result,
                                              self._rope_returned)
            body = restructure.replace(
                body, 'return ${%s}' % self._rope_returned,
                replacement)
            wildcards.append(self._rope_result)
        return similarfinder.make_pattern(body, wildcards)

    def _get_body(self):
        return sourceutils.get_body(self.pyfunction)

    def _make_goal(self, import_=False):
        params = self.pyfunction.get_param_names()
        function_name = self.pyfunction.get_name()
        if import_:
            function_name = self._module_name() + '.' + function_name
        goal = '%s(%s)' % (function_name,
                           ', ' .join(('${%s}' % p) for p in params))
        if self._does_return() and not self._is_expression():
            goal = '${%s} = %s' % (self._rope_result, goal)
        return goal

    def _does_return(self):
        body = self._get_body()
        removed_return = restructure.replace(body, 'return ${result}', '')
        return removed_return != body

    def _is_expression(self):
        return len(self.pyfunction.get_ast().body) == 1

    _rope_result = '_rope__result'
    _rope_returned = '_rope__returned'


def find_temps(project, code):
    code = 'def f():\n' + sourceutils.indent_lines(code, 4)
    pymodule = project.pycore.get_string_module(code)
    result = []
    function_scope = pymodule.get_scope().get_scopes()[0]
    for name, pyname in function_scope.get_names().items():
        if isinstance(pyname, pynames.AssignedName):
            result.append(name)
    return result
