from rope.base import exceptions


class History(object):

    def __init__(self, maxundos=1000):
        self._undo_list = []
        self._redo_list = []
        self.max_undo_count = maxundos

    def do(self, changes):
        self._undo_list.append(changes)
        if len(self._undo_list) > self.max_undo_count:
            del self._undo_list[0]
        changes.do()

    def undo(self):
        if not self._undo_list:
            raise exceptions.HistoryError('Undo list is empty')
        change = self._undo_list.pop()
        self._redo_list.append(change)
        change.undo()

    def redo(self):
        if not self._redo_list:
            raise exceptions.HistoryError('Redo list is empty')
        change = self._redo_list.pop()
        self._undo_list.append(change)
        change.do()

    undo_list = property(lambda self: self._undo_list)
    redo_list = property(lambda self: self._redo_list)
