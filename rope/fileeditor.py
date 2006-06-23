import rope.highlight
import rope.indenter
import rope.editingtools

class FileEditor(object):

    def __init__(self, project, file, editor):
        self.file = file
        self.editor = editor
        self.project = project
        if self.file.get_name().endswith('.py'):
            self.editor.set_editing_tools(rope.editingtools.PythonEditingTools(project))
        self.editor.set_text(self.file.read())

    def save(self):
        self.file.write(self.editor.get_text())
        self.editor.undo_separator()

    def get_editor(self):
        return self.editor

    def get_file(self):
        return self.file

