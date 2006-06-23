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

    def save(self):
        self.file.write(self.editor.get_text())
        self.editor.undo_separator()

    def get_editor(self):
        return self.editor

    def get_file(self):
        return self.file

