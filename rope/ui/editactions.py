import Tkinter
import os.path

import rope.ui.core
import rope.base.project
from rope.ui.actionhelpers import ConfirmEditorsAreSaved
from rope.ui.extension import SimpleAction
from rope.ui.menubar import MenuAddress
from rope.ui import uihelpers, fill


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


class Yank(object):

    _yank_count = 0

    def __call__(self, context):
        last_command = context.core.last_action
        if last_command is None or last_command.get_name() not in ['paste', 'yank']:
            return
        if last_command.get_name() == 'paste':
            self._yank_count = 1
        if last_command.get_name() == 'yank':
            self._yank_count += 1
        if context.get_active_editor():
            context.get_active_editor().get_editor().yank(self._yank_count)


class FillParagraph(object):

    def __init__(self):
        self.fill = fill.Fill()

    def __call__(self, context):
        text = context.editor.get_text()
        offset = context.editor.get_current_offset()
        start, end, filled = self.fill.fill_paragraph(text, offset)
        start_index = context.editor.get_index(start)
        end_index = context.editor.get_index(end)
        context.editor.delete(start_index, end_index)
        context.editor.insert(start_index, filled)
        context.editor.set_insert(context.editor.get_index(offset))


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
            'Undoing <%s>\n\n' % str(history.undo_list[-1]) +
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
            'Redoing <%s>\n\n' % str(history.redo_list[-1]) +
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


def show_history(context):
    if not context.project:
        return
    toplevel = Tkinter.Toplevel()
    toplevel.title('File History')
    frame = Tkinter.Frame(toplevel)
    list_frame = Tkinter.Frame(frame)
    enhanced_list = uihelpers.DescriptionList(
        list_frame, 'Undo History', lambda change: change.get_description())
    for change in reversed(context.project.history.undo_list):
        enhanced_list.add_entry(change)
    list_frame.grid(row=0, column=0, columnspan=2)
    def undo(event=None):
        change = enhanced_list.get_selected()
        if change is None:
            return
        def undo():
            context.project.history.undo(change)
        _confirm_action(
            'Undoing Project Change',
            'Undoing <%s>\n\n' % str(change) +
            'Undo project might change many files. Proceed?', undo)
        toplevel.destroy()
    def cancel(event=None):
        toplevel.destroy()
    undo_button = Tkinter.Button(frame, text='Undo', command=undo)
    cancel_button = Tkinter.Button(frame, text='Cancel', command=cancel)
    undo_button.grid(row=1, column=0)
    toplevel.bind('<Return>', lambda event: undo())
    toplevel.bind('<Escape>', lambda event: cancel())
    toplevel.bind('<Control-g>', lambda event: cancel())
    toplevel.bind('<Alt-u>', lambda event: undo())
    cancel_button.grid(row=1, column=1)
    frame.grid()
    undo_button.focus_set()

def swap_mark_and_insert(context):
    context.editor.swap_mark_and_insert()


def edit_dot_rope(context):
    resource = rope.base.project.get_no_project().get_resource(
        os.path.expanduser('~%s.rope' % os.path.sep))
    editor_manager = context.get_core().get_editor_manager()
    editor_manager.get_resource_editor(resource, mode='python')

def repeat_last_action(context):
    if context.get_active_editor():
        context.core.repeat_last_action()


class FindCommandHandle(uihelpers.FindItemHandle):

    def __init__(self, core):
        self.core = core

    def find_matches(self, starting):
        return [action for action in self.core.get_available_actions()
                if action.get_name().startswith(starting)]

    def selected(self, action):
        self.core.perform_action(action)

    def to_string(self, action):
        return action.get_name()


def execute_command(context):
    uihelpers.find_item_dialog(
        FindCommandHandle(context.core), 'Execute Command',
        'Matched Commands', height=10, width=25)


core = rope.ui.core.Core.get_core()
core._add_menu_cascade(MenuAddress(['Edit'], 'e'), ['all', 'none'])
actions = []

actions.append(SimpleAction('set_mark', set_mark, 'C-space',
                            MenuAddress(['Edit', 'Set Mark'], 's'), ['all']))
actions.append(SimpleAction('copy', copy, 'M-w',
                            MenuAddress(['Edit', 'Copy'], 'c'), ['all']))
actions.append(SimpleAction('cut', cut, 'C-w',
                            MenuAddress(['Edit', 'Cut'], 't'), ['all']))
actions.append(SimpleAction('paste', paste, 'C-y',
                            MenuAddress(['Edit', 'Paste'], 'p'), ['all']))
actions.append(SimpleAction('yank', Yank(), 'M-y',
                            MenuAddress(['Edit', 'Yank'], 'y'), ['all']))
actions.append(SimpleAction('goto_line', goto_line, 'C-x g',
                            MenuAddress(['Edit', 'Goto Line'], 'g'), ['all']))
actions.append(SimpleAction('goto_last_edit_location', goto_last_edit_location, 'C-x C-q',
                            MenuAddress(['Edit', 'Goto Last Edit Location'], 'e'), ['all', 'none']))
actions.append(SimpleAction('swap_mark_and_insert', swap_mark_and_insert, 'C-x C-x',
                            None, ['all']))
actions.append(SimpleAction('fill_paragraph', FillParagraph(), 'M-q',
                            None, ['rest', 'other']))

actions.append(SimpleAction('undo', undo_editing, 'C-x u',
                            MenuAddress(['Edit', 'Undo Editing'], 'u', 1), ['all']))
actions.append(SimpleAction('redo', redo_editing, 'C-x r',
                            MenuAddress(['Edit', 'Redo Editing'], 'r', 1), ['all']))
actions.append(SimpleAction('repeat_last_action', repeat_last_action, 'C-x z',
                            MenuAddress(['Edit', 'Repeat Last Action'], 'l', 1), ['all']))
actions.append(
    SimpleAction('undo_project',
                 ConfirmEditorsAreSaved(undo_project), 'C-x p u',
                 MenuAddress(['Edit', 'Undo Last Project Change'], 'd', 2),
                 ['all', 'none']))
actions.append(
    SimpleAction('redo_project',
                 ConfirmEditorsAreSaved(redo_project), 'C-x p r',
                 MenuAddress(['Edit', 'Redo Last Project Change'], 'o', 2),
                 ['all', 'none']))
actions.append(
    SimpleAction('project_history',
                 ConfirmEditorsAreSaved(show_history), 'C-x p h',
                 MenuAddress(['Edit', 'Project History'], 'h', 2),
                 ['all', 'none']))

actions.append(SimpleAction('search_forward', forward_search, 'C-s',
                            MenuAddress(['Edit', 'Forward Search'], 'f', 3), ['all']))
actions.append(SimpleAction('search_backward', backward_search, 'C-r',
                            MenuAddress(['Edit', 'Backward Search'], 'b', 3), ['all']))

actions.append(SimpleAction('execute_command', execute_command, 'M-x',
                            MenuAddress(['Edit', 'Execute Command'], 'x', 4), ['all', 'none']))
actions.append(SimpleAction('edit_dot_rope', edit_dot_rope, 'C-x c',
                            MenuAddress(['Edit', 'Edit ~/.rope'], '.', 4), ['all', 'none']))


for action in actions:
    core.register_action(action)
