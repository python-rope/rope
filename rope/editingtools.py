import rope.indenter
import rope.highlight
import rope.codeassist
import rope.outline


class EditingTools(object):

    def create_indenter(self, editor):
        pass

    def create_highlighting(self):
        pass
    
    def create_code_assist(self):
        pass

    def create_outline(self):
        pass


class PythonEditingTools(EditingTools):

    def __init__(self, project):
        self.project = project

    def create_indenter(self, editor):
        return rope.indenter.PythonCodeIndenter(editor)

    def create_highlighting(self):
        return rope.highlight.PythonHighlighting()
    
    def create_code_assist(self):
        return rope.codeassist.PythonCodeAssist(self.project)

    def create_outline(self):
        return rope.outline.PythonOutline(self.project)


class NormalEditingTools(EditingTools):

    def __init__(self):
        pass

    def create_indenter(self, editor):
        return rope.indenter.NormalIndenter(editor)

    def create_highlighting(self):
        return rope.highlight.NoHighlighting()
    
    def create_code_assist(self):
        return rope.codeassist.NoAssist()

    def create_outline(self):
        return rope.outline.NoOutline()


