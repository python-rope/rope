import rope.highlight
import rope.indenter
import rope.editingtools

class FileEditor(object):

    def __init__(self, project, file, editor_factory):
        self.file = file
        self.project = project
        editing_tools = None
        if self.file.get_name().endswith('.py'):
            editing_tools = rope.editingtools.PythonEditingTools(project)
        else:
            editing_tools = rope.editingtools.NormalEditingTools()
        self.editor = editor_factory.create(editing_tools)
        self.editor.set_text(self.file.read())
        self.modification_observers = []
        self.editor.add_modification_observer(self._editor_was_modified)
    
    def _editor_was_modified(self):
        for observer in self.modification_observers:
            observer(self)
    
    def add_modification_observer(self, observer):
        self.modification_observers.append(observer)

    def save(self):
        self.file.write(self.editor.get_text())
        self.editor.saving_editor()

    def get_editor(self):
        return self.editor

    def get_file(self):
        return self.file

