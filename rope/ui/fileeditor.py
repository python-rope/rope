import rope.ui.editingtools

class FileEditor(object):

    def __init__(self, project, file_, editor_factory):
        self.file = file_
        self.project = project
        editing_tools = None
        if self.file.get_name().endswith('.py'):
            editing_tools = rope.ui.editingtools.PythonEditingTools(project)
        elif self.file.get_name().endswith('.txt'):
            editing_tools = rope.ui.editingtools.ReSTEditingTools()
        else:
            editing_tools = rope.ui.editingtools.NormalEditingTools()
        self.editor = editor_factory.create(editing_tools)
        self.editor.set_text(self.file.read())
        self.modification_observers = []
        self.editor.add_modification_observer(self._editor_was_modified)
        self.file.add_change_observer(self._file_was_modified)
        self.saving = False
    
    def _editor_was_modified(self):
        for observer in list(self.modification_observers):
            observer(self)
    
    def _file_was_modified(self, file_):
        if not self.saving:
            self.editor.set_text(file_.read())
            self.editor.saving_editor()
    
    def add_modification_observer(self, observer):
        self.modification_observers.append(observer)

    def save(self):
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

