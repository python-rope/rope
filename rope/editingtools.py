import rope.indenter
import rope.highlight
import rope.codeassist


class EditingTools(object):

    def get_indenter(self):
        pass

    def get_highlighting(self):
        pass
    
    def get_code_assist(self):
        pass


class PythonEditingTools(EditingTools):

    def __init__(self, project, editor):
        self.project = project
        self.editor = editor
        self.indenter = rope.indenter.PythonCodeIndenter(self.editor)
        self.highlighting = rope.highlight.PythonHighlighting(self.editor)
        self.codeassist = rope.codeassist.PythonCodeAssist(self.project)

    def get_indenter(self):
        return self.indenter

    def get_highlighting(self):
        return self.highlighting
    
    def get_code_assist(self):
        return self.codeassist


class NormalEditingTools(EditingTools):

    def __init__(self, editor):
        self.editor = editor
        self.indenter = rope.indenter.NormalIndenter(self.editor)
        self.highlighting = rope.highlight.NoHighlighting()
        self.codeassist = rope.codeassist.NoAssist()

    def get_indenter(self):
        return self.indenter

    def get_highlighting(self):
        return self.highlighting
    
    def get_code_assist(self):
        return self.codeassist

