from rope.base import exceptions, change, taskhandle
import cPickle as pickle


class History(object):

    def __init__(self, project, maxundos=None):
        self.project = project
        self._undo_list = []
        self._redo_list = []
        if maxundos is None:
            self.max_undos = project.get_prefs().get('max_history_items', 100)
        else:
            self.max_undos = maxundos
        self._load_history()
        self.current_change = None

    def _load_history(self):
        if self.history_file is not None and self.history_file.exists():
            input_file = file(self.history_file.real_path)
            to_change = change.DataToChange(self.history_file.project)
            for data in pickle.load(input_file):
                self._undo_list.append(to_change(data))
            for data in pickle.load(input_file):
                self._redo_list.append(to_change(data))
            input_file.close()

    def _get_history_file(self):
        if self.project.get_prefs().get('save_history', False):
            folder = self.project.ropefolder
            if folder is not None and folder.exists():
                return self.project.get_file(folder.path + '/history.pickle')

    history_file = property(_get_history_file)

    def do(self, changes, task_handle=taskhandle.NullTaskHandle()):
        self.current_change = changes
        try:
            changes.do(change.create_job_set(task_handle, changes))
        finally:
            self.current_change = None
        if self._is_change_interesting(changes):
            self.undo_list.append(changes)
            if len(self.undo_list) > self.max_undos:
                del self.undo_list[0]

    def _is_change_interesting(self, changes):
        for resource in changes.get_changed_resources():
            if not self.project.is_ignored(resource):
                return True
        return False

    def undo(self, change=None, task_handle=taskhandle.NullTaskHandle()):
        if not self._undo_list:
            raise exceptions.HistoryError('Undo list is empty')
        if change is None:
            change = self.undo_list[-1]
        dependencies = self.find_dependencies(change)
        self._move_front(dependencies)
        index = self.undo_list.index(change)
        self._perform_undos(len(self.undo_list) - index, task_handle)

    def _move_front(self, changes):
        for change in changes:
            self.undo_list.remove(change)
            self.undo_list.append(change)

    def find_dependencies(self, change):
        index = self.undo_list.index(change)
        return _FindChangeDependencies(self.undo_list[index:]).\
               find_dependencies()

    def _perform_undos(self, count, task_handle):
        for i in range(count):
            self.current_change = self.undo_list[-1]
            try:
                job_set = change.create_job_set(task_handle,
                                                self.current_change)
                self.current_change.undo(job_set)
            finally:
                self.current_change = None
            self.redo_list.append(self.undo_list.pop())

    def redo(self, task_handle=taskhandle.NullTaskHandle()):
        if not self.redo_list:
            raise exceptions.HistoryError('Redo list is empty')
        self.current_change = self.redo_list[-1]
        try:
            job_set = change.create_job_set(task_handle, self.current_change)
            self.current_change.do(job_set=job_set)
        finally:
            self.current_change = None
        self.undo_list.append(self.redo_list.pop())

    def contents_before_current_change(self, file):
        if self.current_change is None:
            return None
        result = self._search_for_change_contents([self.current_change], file)
        if result is not None:
            return result
        if file.exists() and not file.is_folder():
            return file.read()
        else:
            return None

    def _search_for_change_contents(self, change_list, file):
        for change_ in reversed(change_list):
            if isinstance(change_, change.ChangeSet):
                result = self._search_for_change_contents(change_.changes,
                                                          file)
                if result is not None:
                    return result
            if isinstance(change_, change.ChangeContents) and \
               change_.resource == file:
                return change_.old_contents

    def sync(self):
        if self.history_file is not None:
            output_file = file(self.history_file.real_path, 'w')
            to_data = change.ChangeToData()
            pickle.dump([to_data(change_) for change_ in self.undo_list],
                        output_file)
            pickle.dump([to_data(change_) for change_ in self.redo_list],
                        output_file)
            output_file.close()

    def get_file_undo_list(self, resource):
        result = []
        for change in self.undo_list:
            if resource in change.get_changed_resources():
                result.append(change)
        return result

    def __str__(self):
        return 'History holds %s changes in memory' % \
               (len(self.undo_list) + len(self.redo_list))

    undo_list = property(lambda self: self._undo_list)
    redo_list = property(lambda self: self._redo_list)


class _FindChangeDependencies(object):

    def __init__(self, change_list):
        self.change = change_list[0]
        self.change_list = change_list
        self.changed_resources = set(self.change.get_changed_resources())

    def find_dependencies(self):
        result = [self.change]
        for change in self.change_list[1:]:
            if self._depends_on(change, result):
                result.append(change)
                self.changed_resources.update(change.get_changed_resources())
        return result

    def _depends_on(self, changes, result):
        for resource in changes.get_changed_resources():
            if resource is None:
                continue
            if resource in self.changed_resources:
                return True
            for changed in self.changed_resources:
                if resource.is_folder() and resource.contains(changed):
                    return True
                if changed.is_folder() and changed.contains(resource):
                    return True
        return False
