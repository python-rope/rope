import Tkinter

import rope.ui.core
from rope.ui.menubar import MenuAddress
from rope.ui.extension import SimpleAction


class ConfirmAllEditorsAreSaved(object):
    
    def __init__(self, callback):
        self.callback = callback
    
    def __call__(self, context):
        fileeditor = context.get_active_editor()
        editors = context.get_core().get_editor_manager().editors
        is_modified = False
        for editor in editors:
            if editor.get_editor().is_modified():
                is_modified = True
                break
        if not is_modified:
            return self.callback(context)
        toplevel = Tkinter.Toplevel()
        toplevel.title('Save All')
        frame = Tkinter.Frame(toplevel)
        label = Tkinter.Label(frame, text='All editors should be saved before refactorings.')
        label.grid(row=0, column=0, columnspan=2)
        def ok(event=None):
            context.get_core().save_all_editors()
            toplevel.destroy()
            self.callback(context)
        def cancel(event=None):
            toplevel.destroy()
        ok_button = Tkinter.Button(frame, text='Save All', command=ok)
        cancel_button = Tkinter.Button(frame, text='Cancel', command=cancel)
        ok_button.grid(row=1, column=0)
        toplevel.bind('<Return>', lambda event: ok())
        toplevel.bind('<Escape>', lambda event: cancel())
        toplevel.bind('<Control-g>', lambda event: cancel())
        cancel_button.grid(row=1, column=1)
        frame.grid()
        ok_button.focus_set()


def rename(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        fileeditor.get_editor()._rename_refactoring_dialog()

def transform_module_to_package(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        editor.refactoring.transform_module_to_package(resource)

def local_rename(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor()._local_rename_dialog()

def extract_method(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor()._extract_method_dialog()

def undo_last_refactoring(context):
    if context.get_core().get_open_project():
        context.get_core().get_open_project().get_pycore().\
                get_refactoring().undo_last_refactoring()
    

actions = []
actions.append(SimpleAction('Rename Refactoring', ConfirmAllEditorsAreSaved(rename), 'M-R',
                            MenuAddress(['Refactor', 'Rename'], 'r')))
actions.append(SimpleAction('Transform Module To Package', 
                            ConfirmAllEditorsAreSaved(transform_module_to_package), None,
                            MenuAddress(['Refactor', 'Transform Module To Package'], 't')))
actions.append(SimpleAction('Undo Last Refactoring', 
                            ConfirmAllEditorsAreSaved(undo_last_refactoring), None,
                            MenuAddress(['Refactor', 'Undo Last Refactoring'], 'u')))

actions.append(SimpleAction('Rename Local Variable', ConfirmAllEditorsAreSaved(local_rename), None,
                            MenuAddress(['Refactor', 'Rename Local Variable'], 'e', 1)))
actions.append(SimpleAction('Extract Method', ConfirmAllEditorsAreSaved(extract_method), 'M-M',
                            MenuAddress(['Refactor', 'Extract Method'], 'e', 1)))

core = rope.ui.core.Core.get_core()
for action in actions:
    core.register_action(action)

