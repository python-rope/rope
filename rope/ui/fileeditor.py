import Tkinter

import rope.base.exceptions
from rope.ui import editingcontexts

class FileEditor(object):

    def __init__(self, project, file_, editor_factory, readonly=False):
        self.file = file_
        self.project = project
        editingcontext = None
        if self.file.get_name().endswith('.py'):
            editingcontext = editingcontexts.python
        elif self.file.get_name().endswith('.txt'):
            editingcontext = editingcontexts.rest
        else:
            editingcontext = editingcontexts.others
        self.editor = editor_factory.create(editingcontext)
        self.editor.set_text(self.file.read())
        self.modification_observers = []
        self.editor.add_modification_observer(self._editor_was_modified)
        self.file.get_parent().add_change_observer(self._editor_was_modified)
        self.file.add_change_observer(self._file_was_modified)
        self.saving = False
        self.readonly = readonly
        #if readonly:
        #    self.editor.getWidget()['state'] = Tkinter.DISABLED
    
    def _editor_was_modified(self, *args):
        for observer in list(self.modification_observers):
            observer(self)
    
    def _file_was_modified(self, file_):
        if not self.saving:
            self.editor.set_text(file_.read())
            self.editor.saving_editor()
    
    def add_modification_observer(self, observer):
        self.modification_observers.append(observer)

    def save(self):
        if self.readonly:
            raise rope.base.exceptions.RopeUIException(
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
        self.file.remove_change_observer(self._file_was_modified)

