import rope.base.exceptions
import rope.ui.uihelpers
from rope.base.project import ResourceObserver, FilteredResourceObserver
from rope.ui import editingcontexts


class FileEditor(object):

    def __init__(self, project, file_, editor_factory, readonly=False):
        self.file = file_
        self.project = project
        editingcontext = None
        if self.file.name.endswith('.py'):
            editingcontext = editingcontexts.python
        elif self.file.name.endswith('.txt'):
            editingcontext = editingcontexts.rest
        else:
            editingcontext = editingcontexts.others
        self.editor = editor_factory.create(editingcontext)
        self.editor.set_text(self.file.read())
        self.modification_observers = []
        self.change_observers = []
        self.editor.add_modification_observer(self._editor_was_modified)
        self._register_observers()
        self.saving = False
        self.readonly = readonly
        #if readonly:
        #    self.editor.getWidget()['state'] = Tkinter.DISABLED

    def _register_observers(self):
        self.observer = FilteredResourceObserver(
            ResourceObserver(self._file_was_modified, self._file_was_removed),
            [self.file])
        if self.project is not None:
            self.project.add_observer(self.observer)

    def _remove_observers(self):
        if self.project is not None:
            self.project.remove_observer(self.observer)

    def _editor_was_modified(self):
        for observer in list(self.modification_observers):
            observer(self)

    def _file_was_removed(self, file, new_file=None):
        self._remove_observers()
        # XXX: file was removed while we were editing it.  What to do?
        if new_file is None:
            return
        self.file = new_file
        self._register_observers()
        self._editor_was_modified()

    def _file_was_modified(self, file_):
        if not self.saving:
            self.editor.set_text(file_.read())
            self.editor.saving_editor()

    def add_modification_observer(self, observer):
        self.modification_observers.append(observer)

    def add_change_observer(self, observer):
        self.editor.add_change_observer(lambda index: observer(self.file, index))

    def save(self):
        if self.readonly:
            raise rope.ui.uihelpers.RopeUIError(
                'File is opened in readonly mode!')
        self.saving = True
        try:
            self.file.write(self.editor.get_text())
            self.editor.saving_editor()
        finally:
            self.saving = False

    def get_editor(self):
        return self.editor

    def get_file(self):
        return self.file

    def close(self):
        self._remove_observers()

