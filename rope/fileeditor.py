import rope.highlight
import rope.indenter

class FileEditor(object):
    def __init__(self, project, file, editor):
        self.file = file
        self.editor = editor
        self.project = project
        if self.file.get_name().endswith('.py'):
            self.editor.set_highlighting(rope.highlight.PythonHighlighting(self.editor))
            self.editor.set_indenter(rope.indenter.PythonCodeIndenter(self.editor))
            self.editor.set_code_assist(self.project.get_code_assist())
        self.editor.set_text(self.file.read())

    def save(self):
        self.file.write(self.editor.get_text())
        self.editor.undo_separator()

    def get_editor(self):
        return self.editor

    def get_file(self):
        return self.file
