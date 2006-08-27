import rope.ui.core
from rope.ui.menubar import MenuAddress
from rope.ui.extension import SimpleAction

def do_rename(context):
    if context.get_active_editor():
                context.get_active_editor().get_editor()._rename_refactoring_dialog()

def do_local_rename(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor()._local_rename_dialog()

def do_extract_method(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor()._extract_method_dialog()

def do_undo_last_refactoring(context):
    if context.get_core().get_open_project():
        context.get_core().get_open_project().get_refactoring().undo_last_refactoring()
    

actions = []
actions.append(SimpleAction('Rename Refactoring', do_rename, '<Alt-R>',
                            MenuAddress(['Refactor', 'Rename'], 'r')))
actions.append(SimpleAction('Undo Last Refactoring', do_undo_last_refactoring, None,
                            MenuAddress(['Refactor', 'Undo Last Refactoring'], 'u')))

actions.append(SimpleAction('Rename Local Variable', do_local_rename, None,
                            MenuAddress(['Refactor', 'Rename Local Variable'], 'e', 1)))
actions.append(SimpleAction('Extract Method', do_extract_method, '<Alt-M>',
                            MenuAddress(['Refactor', 'Extract Method'], 'e', 1)))

core = rope.ui.core.Core.get_core()
for action in actions:
    core.register_action(action)

