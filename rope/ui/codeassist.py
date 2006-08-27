import rope.ui.core
from rope.ui.menubar import MenuAddress
from rope.ui.extension import SimpleAction

def do_correct_line_indentation(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().correct_line_indentation()

def do_quick_outline(context):
    if context.get_active_editor:
        context.get_active_editor().get_editor()._show_outline_window()

def do_code_assist(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor()._show_completion_window()

def do_goto_definition(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().goto_definition()

def do_show_doc(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor()._show_doc_window()

def do_run_module(context):
    context.get_core().run_active_editor()

core = rope.ui.core.Core.get_core()
actions = []

actions.append(SimpleAction('Correct Line Indentation', do_correct_line_indentation,
                            'C-i',
                            MenuAddress(['Code', 'Correct Line Indentation'], 'i')))
actions.append(SimpleAction('Quick Outline', do_quick_outline, 'C-o',
                            MenuAddress(['Code', 'Quick Outline'], 'q')))
actions.append(SimpleAction('Code Assist', do_code_assist, 'M-slash',
                            MenuAddress(['Code', 'Code Assist'], 'c')))
actions.append(SimpleAction('Goto Definition', do_goto_definition, 'F3',
                            MenuAddress(['Code', 'Goto Definition'], 'g')))
actions.append(SimpleAction('Show Doc', do_show_doc, 'F2',
                            MenuAddress(['Code', 'Show Doc'], 's')))
actions.append(SimpleAction('Run Module', do_run_module, 'C-F11',
                            MenuAddress(['Code', 'Run Module'], 'm')))

for action in actions:
    core.register_action(action)
