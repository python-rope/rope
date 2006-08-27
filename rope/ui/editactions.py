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

core = rope.ui.core.Core.get_core()
actions = []

actions.append(SimpleAction('Emacs Set Mark', set_mark, '<Control-space>',
                            MenuAddress(['Edit', 'Emacs Set Mark'], 's')))
actions.append(SimpleAction('Emacs Copy', copy, '<Alt-w>',
                            MenuAddress(['Edit', 'Emacs Copy'], 'c')))
actions.append(SimpleAction('Emacs Cut', cut, '<Control-w>',
                            MenuAddress(['Edit', 'Emacs Cut'], 't')))
actions.append(SimpleAction('Paste', paste, '<Control-y>',
                            MenuAddress(['Edit', 'Emacs Paste'], 'p')))
actions.append(SimpleAction('Undo', undo, '<Control-x><u>',
                            MenuAddress(['Edit', 'Undo'], 'u', 1)))
actions.append(SimpleAction('Redo', redo, '<Control-x><r>',
                            MenuAddress(['Edit', 'Redo'], 'r', 1)))
actions.append(SimpleAction('Forward Search', forward_search, '<Control-s>',
                            MenuAddress(['Edit', 'Forward Search'], 'f', 2)))
actions.append(SimpleAction('Backward Search', backward_search, '<Control-r>',
                            MenuAddress(['Edit', 'Backward Search'], 'b', 2)))

for action in actions:
    core.register_action(action)
