from rope.base import resources, project


class MultiProjectRefactoring(object):

    def __init__(self, refactoring, projects, addpath=True):
        """Create a multiproject proxy for the main refactoring

        `projects` are other project.

        """
        self.refactoring = refactoring
        self.projects = projects
        self.addpath = addpath

    def __call__(self, project, *args, **kwds):
        """Create the refactoring"""
        return _MultiRefactoring(self.refactoring, self.projects, self.addpath,
                                 project, *args, **kwds)


class _MultiRefactoring(object):

    def __init__(self, refactoring, other_projects, addpath,
                 project, *args, **kwds):
        self.refactoring = refactoring
        self.projects = other_projects
        self.project = project
        for other_project in self.projects:
            other_project.get_prefs().add('python_path', self.project.address)
        self.main_refactoring = self.refactoring(project, *args, **kwds)
        args, kwds = self._change_project_resources_for_args(args, kwds)
        self.other_refactorings = [self.refactoring(other, *args, **kwds)
                                   for other in self.projects]

    def get_all_changes(self, *args, **kwds):
        """Get a project to changes dict"""
        result = []
        result.append((self.project,
                       self.main_refactoring.get_changes(*args, **kwds)))
        args, kwds = self._change_project_resources_for_args(args, kwds)
        for project, refactoring in zip(self.projects,
                                        self.other_refactorings):
            result.append((project, refactoring.get_changes(*args, **kwds)))
        return result

    def __getattr__(self, name):
        return getattr(self.main_refactoring, name)

    def _change_project_resources_for_args(self, args, kwds):
        newargs = [self._change_project_resource(arg) for arg in args]
        newkwds = dict((name, self._change_project_resource(value))
                       for name, value in kwds.items())
        return newargs, newkwds
        
    def _change_project_resource(self, obj):
        if isinstance(obj, resources.Resource) and \
           obj.project == self.project:
            return project.get_no_project().get_resource(obj.real_path)
        return obj


def perform(project_changes):
    for project, changes in project_changes:
        project.do(changes)
