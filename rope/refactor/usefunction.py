from rope.base import change, taskhandle, evaluate
from rope.refactor import restructure, sourceutils, similarfinder


class UseFunction(object):

    def __init__(self, project, resource, offset):
        self.project = project
        self.resource = resource
        self.offset = offset
        this_pymodule = project.pycore.resource_to_pyobject(resource)
        pyname = evaluate.get_pyname_at(this_pymodule, offset)
        self.pyfunction = pyname.get_object()

    def get_changes(self, task_handle=taskhandle.NullTaskHandle()):
        body = sourceutils.get_body(self.pyfunction)
        params = self.pyfunction.get_param_names()
        pattern = self._make_pattern(params)
        goal = self._make_goal(params)

        defining_resource = self.pyfunction.get_module().get_resource()
        body_region = sourceutils.get_body_region(self.pyfunction)
        args_value = {'skip': (defining_resource, body_region)}
        args = {'': args_value}

        restructuring = restructure.Restructure(
            self.project, pattern, goal, args=args)
        return restructuring.get_changes(task_handle=task_handle)

    def _make_pattern(self, params):
        body = sourceutils.get_body(self.pyfunction)
        body = restructure.replace(body, 'return', 'pass')
        if self._does_return():
            if self._is_expression():
                replacement = '${%s}' % self._rope_returned
            else:
                replacement = '%s = ${%s}' % (self._rope_result,
                                              self._rope_returned)
            body = restructure.replace(
                body, 'return ${%s}' % self._rope_returned,
                replacement)
            params = list(params) + [self._rope_result]
        return similarfinder.make_pattern(body, params)

    def _make_goal(self, params):
        goal = '%s(%s)' % (self.pyfunction.get_name(),
                           ', ' .join(('${%s}' % p) for p in params))
        if self._does_return() and not self._is_expression():
            goal = '${%s} = %s' % (self._rope_result, goal)
        return goal

    def _does_return(self):
        body = sourceutils.get_body(self.pyfunction)
        removed_return = restructure.replace(body, 'return ${result}', '')
        return removed_return != body

    def _is_expression(self):
        return len(self.pyfunction.get_ast().body) == 1

    _rope_result = '_rope__result'
    _rope_returned = '_rope__returned'
