from rope.ui import editingtools

class EditingContext(object):
    
    def __init__(self, name, core):
        self.core = core
        self.name = name
    
    def _get_editing_tools(self):
        project = self.core.get_open_project()
        return editingtools.get_editingtools_for_context(self, project)
    
    editingtools = property(_get_editing_tools)

contexts = {}

def init_contexts(core):
    for name in ['python', 'rest', 'others', 'none']:
        if name not in contexts:
            context = EditingContext(name, core)
            globals()[name] = context
            contexts[name] = context
