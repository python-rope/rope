import rope.refactor.sourceutils
import ropeide.highlighter
import ropeide.indenter


def get_editingtools_for_context(editing_context, project, prefs):
    if editing_context.name == 'python':
        return PythonEditingTools(project, prefs)
    if editing_context.name == 'rst':
        return ReSTEditingTools()
    return NormalEditingTools()


class EditingTools(object):

    def create_indenter(self, editor):
        pass

    def create_highlighting(self):
        pass


class PythonEditingTools(EditingTools):

    def __init__(self, project, prefs):
        self.project = project
        self.prefs = prefs

    def create_indenter(self, editor):
        indents = rope.refactor.sourceutils.get_indent(self.project.get_pycore())
        return ropeide.indenter.PythonCodeIndenter(editor, indents=indents)

    def create_highlighting(self):
        return ropeide.highlighter.PythonHighlighting()


class ReSTEditingTools(EditingTools):

    def create_indenter(self, editor):
        return ropeide.indenter.NormalIndenter(editor)

    def create_highlighting(self):
        return ropeide.highlighter.ReSTHighlighting()


class NormalEditingTools(EditingTools):

    def create_indenter(self, editor):
        return ropeide.indenter.NormalIndenter(editor)

    def create_highlighting(self):
        return ropeide.highlighter.NoHighlighting()
