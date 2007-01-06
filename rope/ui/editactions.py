import Tkinter

import rope.ui.core
from rope.ui.menubar import MenuAddress
from rope.ui.extension import SimpleAction

def set_mark(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().set_mark()

def copy(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().copy_region()

def cut(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().cut_region()

def paste(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().paste()

def undo(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().undo()

def redo(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().redo()

def forward_search(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().start_searching(True)

def backward_search(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().start_searching(False)

def goto_line(context):
    if not context.get_active_editor():
        return
    editor = context.get_active_editor().get_editor()
    toplevel = Tkinter.Toplevel()
    toplevel.title('Goto Line')
    label = Tkinter.Label(toplevel, text='Line Number :')
    line_entry = Tkinter.Entry(toplevel)
    label.grid(row=0, column=0)
    line_entry.grid(row=0, column=1)
    def cancel(event=None):
        toplevel.destroy()
    def ok(event=None):
        editor.goto_line(int(line_entry.get()))
        toplevel.destroy()
    line_entry.bind('<Return>', ok)
    line_entry.bind('<Control-g>', cancel)
    line_entry.bind('<Escape>', cancel)
    toplevel.grid()
    line_entry.focus_set()

def goto_last_edit_location(context):
    context.get_core().get_editor_manager().goto_last_edit_location()


core = rope.ui.core.Core.get_core()
core._add_menu_cascade(MenuAddress(['Edit'], 'e'), ['all', 'none'])
actions = []

actions.append(SimpleAction('Emacs Set Mark', set_mark, 'C-space',
                            MenuAddress(['Edit', 'Emacs Set Mark'], 's'), ['all']))
actions.append(SimpleAction('Emacs Copy', copy, 'M-w',
                            MenuAddress(['Edit', 'Emacs Copy'], 'c'), ['all']))
actions.append(SimpleAction('Emacs Cut', cut, 'C-w',
                            MenuAddress(['Edit', 'Emacs Cut'], 't'), ['all']))
actions.append(SimpleAction('Paste', paste, 'C-y',
                            MenuAddress(['Edit', 'Emacs Paste'], 'p'), ['all']))
actions.append(SimpleAction('Goto Line', goto_line, None,
                            MenuAddress(['Edit', 'Goto Line'], 'g'), ['all']))
actions.append(SimpleAction('Goto Last Edit Location', goto_last_edit_location, 'C-q',
                            MenuAddress(['Edit', 'Goto Last Edit Location'], 'e'), ['all', 'none']))
actions.append(SimpleAction('Undo', undo, 'C-x u',
                            MenuAddress(['Edit', 'Undo'], 'u', 1), ['all']))
actions.append(SimpleAction('Redo', redo, 'C-x r',
                            MenuAddress(['Edit', 'Redo'], 'r', 1), ['all']))
actions.append(SimpleAction('Forward Search', forward_search, 'C-s',
                            MenuAddress(['Edit', 'Forward Search'], 'f', 2), ['all']))
actions.append(SimpleAction('Backward Search', backward_search, 'C-r',
                            MenuAddress(['Edit', 'Backward Search'], 'b', 2), ['all']))

for action in actions:
    core.register_action(action)
