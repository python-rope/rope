import Tkinter

import rope.ui.core
from rope.ui.menubar import MenuAddress
from rope.ui.extension import SimpleAction
from rope.ui.uihelpers import TreeView, TreeViewHandle


def do_correct_line_indentation(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().correct_line_indentation()

class _OutlineViewHandle(TreeViewHandle):
    
    def __init__(self, editor, toplevel):
        self.editor = editor
        self.toplevel = toplevel

    def entry_to_string(self, outline_node):
        return outline_node.get_name()

    def canceled(self):
        self.toplevel.destroy()

    def selected(self, selected):
        self.editor.goto_line(selected.get_line_number())
        self.toplevel.destroy()

    def focus_went_out(self):
        self.canceled()

    def get_children(self, outline_node):
        return outline_node.get_children()


def do_quick_outline(context):
    if not context.get_active_editor():
        return
    editor = context.get_active_editor().get_editor()
    toplevel = Tkinter.Toplevel()
    toplevel.title('Quick Outline')
    tree_view = TreeView(toplevel, _OutlineViewHandle(editor, toplevel),
                         title='Quick Outline')
    for node in editor.outline.get_root_nodes(editor.get_text()):
        tree_view.add_entry(node)
    tree_view.list.focus_set()
    toplevel.grab_set()

def do_code_assist(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor()._show_completion_window()

def do_goto_definition(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().goto_definition()

def do_show_doc(context):
    if not context.get_active_editor():
        return
    editor = context.get_active_editor().get_editor()
    doc = editor.code_assist.get_doc(editor.get_text(),
                                     editor.get_current_offset(),
                                     context.get_active_editor().get_file())
    if doc is not None:
        toplevel = Tkinter.Toplevel()
        toplevel.title('Show Doc')
        doc_text = Tkinter.Label(toplevel, text='\n%s\n' % doc, justify=Tkinter.LEFT, 
                                 relief=Tkinter.GROOVE, width=80)
        doc_text.grid(sticky=Tkinter.W+Tkinter.N)
        def close(event=None):
            toplevel.destroy()
        toplevel.bind('<Escape>', close)
        toplevel.bind('<Control-g>', close)
        toplevel.bind('<FocusOut>', close)
        toplevel.grab_set()
        toplevel.focus_set()

def do_run_module(context):
    if context.get_active_editor():
        context.get_core().get_open_project().get_pycore().\
                run_module(context.get_active_editor().get_file())

# Registering code assist actions
core = rope.ui.core.Core.get_core()
actions = []

actions.append(SimpleAction('Code Assist', do_code_assist, 'M-slash',
                            MenuAddress(['Code', 'Code Assist'], 'c')))
actions.append(SimpleAction('Goto Definition', do_goto_definition, 'F3',
                            MenuAddress(['Code', 'Goto Definition'], 'g')))
actions.append(SimpleAction('Show Doc', do_show_doc, 'F2',
                            MenuAddress(['Code', 'Show Doc'], 's')))

actions.append(SimpleAction('Correct Line Indentation',
                            do_correct_line_indentation, 'C-i',
                            MenuAddress(['Code', 'Correct Line Indentation'], 'i', 1)))
actions.append(SimpleAction('Quick Outline', do_quick_outline, 'C-o',
                            MenuAddress(['Code', 'Quick Outline'], 'q', 2)))
actions.append(SimpleAction('Run Module', do_run_module, 'M-X p',
                            MenuAddress(['Code', 'Run Module'], 'm', 2)))

for action in actions:
    core.register_action(action)
