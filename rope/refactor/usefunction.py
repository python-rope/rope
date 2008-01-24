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
        pattern = similarfinder.make_pattern(body, params)
        goal = '%s(%s)' % (self.pyfunction.get_name(),
                           ', ' .join(('${%s}' % p) for p in params))
        restructuring = restructure.Restructure(self.project, pattern, goal)
        return restructuring.get_changes(task_handle=task_handle)
