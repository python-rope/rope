from rope.base import change, taskhandle
from rope.refactor import patchedast, similarfinder, sourceutils


class Restructure(object):

    def __init__(self, project, pattern, goal, checks={}):
        self.pycore = project.pycore
        self.pattern = pattern
        self.goal = goal
        self.checks = checks
        self.template = similarfinder.CodeTemplate(self.goal)

    def get_changes(self, task_handle=taskhandle.NullTaskHandle()):
        changes = change.ChangeSet('Restructuring <%s> to <%s>' %
                                   (self.pattern, self.goal))
        files = self.pycore.get_python_files()
        job_set = task_handle.create_job_set('Collecting Changes', len(files))
        for resource in files:
            job_set.started_job('Working on <%s>' % resource.path)
            pymodule = self.pycore.resource_to_pyobject(resource)
            finder = similarfinder.CheckingFinder(pymodule, self.checks)
            collector = sourceutils.ChangeCollector(pymodule.source_code)
            for match in finder.get_matches(self.pattern):
                start, end = match.get_region()
                collector.add_change(
                    start, end, self._get_text(pymodule.source_code, match))
            result = collector.get_changed()
            if result is not None:
                changes.add_change(change.ChangeContents(resource, result))
            job_set.finished_job()
        return changes

    def _get_text(self, source, match):
        mapping = {}
        for name in self.template.get_names():
            ast = match.get_ast(name)
            start, end = patchedast.node_region(ast)
            mapping[name] = source[start:end]
        return self.template.substitute(mapping)
