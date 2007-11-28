class MultiProjectRefactoring(object):

    def __init__(self, refactoring, projects):
        """Create a multiproject proxy for the main refactoring

        `projects` are other project.

        """
        self.refactoring = refactoring
        self.projects = projects

    def __call__(self, project, *args, **kwds):
        """Create the refactoring"""
        self.project = project
        self.main_refactoring = self.refactoring(project, *args, **kwds)
        self.other_refactorings = [self.refactoring(other, *args, **kwds)
                                   for project in self.projects]
        return self

    def get_all_changes(self, *args, **kwds):
        """Get a project to changes dict"""
        result = []
        for project, refactoring in zip(self.projects,
                                        self.other_refactorings):
            result.append((project, refactoring.get_changes(*args, **kwds)))
        result.append((self.project,
                       self.main_refactoring.get_changes(*args, **kwds)))
        return result

    def __getattr__(self, name):
        return getattr(self.main_refactoring, name)


def perform(project_changes):
    for project, changes in project_changes:
        project.do(changes)
