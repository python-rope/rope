import rope.ui.indenter
import rope.ui.highlighter
import rope.codeassist
import rope.outline
import rope.refactor


class EditingTools(object):

    def create_indenter(self, editor):
        pass

    def create_highlighting(self):
        pass
    
    def create_code_assist(self):
        pass

    def create_outline(self):
        pass

    def create_refactoring(self):
        pass
    
    def get_editing_context(self):
        pass


class PythonEditingTools(EditingTools):

    def __init__(self, project):
        self.project = project

    def create_indenter(self, editor):
        return rope.ui.indenter.PythonCodeIndenter(editor)

    def create_highlighting(self):
        return rope.ui.highlighter.PythonHighlighting()
    
    def create_code_assist(self):
        return rope.codeassist.PythonCodeAssist(self.project)

    def create_outline(self):
        return rope.outline.PythonOutline(self.project)

    def create_refactoring(self):
        return self.project.get_pycore().get_refactoring()

    def get_editing_context(self):
        return 'python'


class NormalEditingTools(EditingTools):

    def __init__(self):
        pass

    def create_indenter(self, editor):
        return rope.ui.indenter.NormalIndenter(editor)

    def create_highlighting(self):
        return rope.ui.highlighter.NoHighlighting()
    
    def create_code_assist(self):
        return rope.codeassist.NoAssist()

    def create_outline(self):
        return rope.outline.NoOutline()

    def create_refactoring(self):
        return rope.refactor.NoRefactoring()

    def get_editing_context(self):
        return 'others'


class ReSTEditingTools(EditingTools):

    def __init__(self):
        pass

    def create_indenter(self, editor):
        return rope.ui.indenter.NormalIndenter(editor)

    def create_highlighting(self):
        return rope.ui.highlighter.ReSTHighlighting()
    
    def create_code_assist(self):
        return rope.codeassist.NoAssist()

    def create_outline(self):
        return rope.outline.NoOutline()

    def create_refactoring(self):
        return rope.refactor.NoRefactoring()

    def get_editing_context(self):
        return 'rest'
