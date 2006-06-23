import rope.indenter
import rope.highlight
import rope.codeassist


class EditingTools(object):

    def create_indenter(self, editor):
        pass

    def create_highlighting(self):
        pass
    
    def create_code_assist(self):
        pass


class PythonEditingTools(EditingTools):

    def __init__(self, project):
        self.project = project

    def create_indenter(self, editor):
        return rope.indenter.PythonCodeIndenter(editor)

    def create_highlighting(self):
        return rope.highlight.PythonHighlighting()
    
    def get_code_assist(self):
        return rope.codeassist.PythonCodeAssist(self.project)


class NormalEditingTools(EditingTools):

    def __init__(self):
        pass

    def create_indenter(self, editor):
        return rope.indenter.NormalIndenter(editor)

    def create_highlighting(self):
        return rope.highlight.NoHighlighting()
    
    def create_code_assist(self):
        return rope.codeassist.NoAssist()

