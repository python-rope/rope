import Tkinter

import rope.ui.core
from rope.ui.actionhelpers import ConfirmAllEditorsAreSaved
from rope.ui.extension import SimpleAction
from rope.ui.menubar import MenuAddress


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

def undo_editing(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().undo()

def redo_editing(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().redo()

def _confirm_action(title, message, action):
    toplevel = Tkinter.Toplevel()
    toplevel.title(title)
    frame = Tkinter.Frame(toplevel)
    label = Tkinter.Label(frame, text=message)
    label.grid(row=0, column=0, columnspan=2)
    def ok(event=None):
        action()
        toplevel.destroy()
    def cancel(event=None):
        toplevel.destroy()
    ok_button = Tkinter.Button(frame, text='OK', command=ok)
    cancel_button = Tkinter.Button(frame, text='Cancel', command=cancel)
    ok_button.grid(row=1, column=0)
    toplevel.bind('<Return>', lambda event: ok())
    toplevel.bind('<Escape>', lambda event: cancel())
    toplevel.bind('<Control-g>', lambda event: cancel())
    cancel_button.grid(row=1, column=1)
    frame.grid()
    ok_button.focus_set()


def undo_project(context):
    if context.project:
        history = context.project.history
        if not history.undo_list:
            return
        def undo():
            history.undo()
        _confirm_action(
            'Undoing Project Change',
            'Undoing <%s>\n\n' % history.undo_list[-1].get_description() +
            'Undo project might change many files. Proceed?', undo)

def redo_project(context):
    if context.project:
        history = context.project.history
        if not history.redo_list:
            return
        def redo():
            history.redo()
        _confirm_action(
            'Redoing Project Change',
            'Redoing <%s>\n\n' % history.redo_list[-1].get_description() +
            'Redo project might change many files. Proceed?', redo)

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

actions.append(SimpleAction('Undo', undo_editing, 'C-x u',
                            MenuAddress(['Edit', 'Undo Editing'], 'u', 1), ['all']))
actions.append(SimpleAction('Redo', redo_editing, 'C-x r',
                            MenuAddress(['Edit', 'Redo Editing'], 'r', 1), ['all']))
actions.append(
    SimpleAction('Undo Project',
                 ConfirmAllEditorsAreSaved(undo_project), 'C-x U',
                 MenuAddress(['Edit', 'Undo Last Project Change'], 'd', 2),
                 ['all', 'none']))
actions.append(
    SimpleAction('Redo Project',
                 ConfirmAllEditorsAreSaved(redo_project), 'C-x R',
                 MenuAddress(['Edit', 'Redo Last Project Change'], 'o', 2),
                 ['all', 'none']))

actions.append(SimpleAction('Forward Search', forward_search, 'C-s',
                            MenuAddress(['Edit', 'Forward Search'], 'f', 3), ['all']))
actions.append(SimpleAction('Backward Search', backward_search, 'C-r',
                            MenuAddress(['Edit', 'Backward Search'], 'b', 3), ['all']))

for action in actions:
    core.register_action(action)
