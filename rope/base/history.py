from rope.refactor import change


class History(object):

    def __init__(self):
        self._undo_list = []
        self._redo_list = []

    def do(self, changes):
        self._undo_list.append(changes)
        changes.do()

    def undo(self):
        change = self._undo_list.pop()
        self._redo_list.append(change)
        change.undo()

    def redo(self):
        change = self._redo_list.pop()
        self._undo_list.append(change)
        change.do()
