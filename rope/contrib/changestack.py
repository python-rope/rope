from rope.base import change


class ChangeStack(object):

    def __init__(self, project, description='merged changes'):
        self.project = project
        self.description = description
        self.stack = []

    def push_change(self, changes):
        self.stack.append(changes)
        self.project.do(changes)

    def pop_all(self):
        for i in range(len(self.stack)):
            self.project.history.undo()

    def merged_changes(self):
        result = change.ChangeSet(self.description)
        for changes in self.stack:
            for c in self._basic_changes(changes):
                result.add_change(c)
        return result

    def _basic_changes(self, changes):
        if isinstance(changes, change.ChangeSet):
            for child in changes.changes:
                for atom in self._basic_changes(child):
                    yield atom
        else:
            yield changes
