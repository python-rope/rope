import rope.highlight
import rope.indenter

class FileEditor(object):
    def __init__(self, file, editor):
        self.file = file
        self.editor = editor
        if self.file.get_name().endswith('.py'):
            self.editor.set_highlighting(rope.highlight.PythonHighlighting(self.editor))
            self.editor.set_indenter(rope.indenter.PythonCodeIndenter(self.editor))
        self.editor.set_text(self.file.read())

    def save(self):
        self.file.write(self.editor.get_text())

    def get_editor(self):
        return self.editor

    def get_file(self):
        return self.file
