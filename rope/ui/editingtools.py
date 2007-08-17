import rope.ide.codeassist
import rope.refactor.sourceutils
import rope.ui.highlighter
import rope.ui.indenter


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
        self._code_assist = None
        self._outline = None

    def create_indenter(self, editor):
        indents = rope.refactor.sourceutils.get_indent(self.project.get_pycore())
        return rope.ui.indenter.PythonCodeIndenter(editor, indents=indents)

    def create_highlighting(self):
        return rope.ui.highlighter.PythonHighlighting()

    def _get_code_assist(self):
        if self._code_assist is None:
            self._code_assist = rope.ide.codeassist.PythonCodeAssist(self.project)
            for name, template in self.prefs.get('templates', []):
                self._code_assist.add_template(name, template)
        return self._code_assist

    codeassist = property(_get_code_assist)


class ReSTEditingTools(EditingTools):

    def create_indenter(self, editor):
        return rope.ui.indenter.NormalIndenter(editor)

    def create_highlighting(self):
        return rope.ui.highlighter.ReSTHighlighting()


class NormalEditingTools(EditingTools):

    def create_indenter(self, editor):
        return rope.ui.indenter.NormalIndenter(editor)

    def create_highlighting(self):
        return rope.ui.highlighter.NoHighlighting()

