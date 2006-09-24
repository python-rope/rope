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
    if not context.get_active_editor():
        return
    toplevel = Tkinter.Toplevel()
    toplevel.title('Rename Refactoring')
    frame = Tkinter.Frame(toplevel)
    label = Tkinter.Label(frame, text='New Name :')
    label.grid(row=0, column=0)
    new_name_entry = Tkinter.Entry(frame)
    new_name_entry.grid(row=0, column=1)
    def ok(event=None):
        resource = context.get_active_editor().get_file()
        editor = context.get_active_editor().get_editor()
        editor.refactoring.rename(resource,
                                  editor.get_current_offset(),
                                  new_name_entry.get())
        toplevel.destroy()
    def cancel(event=None):
        toplevel.destroy()

    ok_button = Tkinter.Button(frame, text='Done', command=ok)
    cancel_button = Tkinter.Button(frame, text='Cancel', command=cancel)
    ok_button.grid(row=1, column=0)
    new_name_entry.bind('<Return>', lambda event: ok())
    new_name_entry.bind('<Escape>', lambda event: cancel())
    new_name_entry.bind('<Control-g>', lambda event: cancel())
    cancel_button.grid(row=1, column=1)
    frame.grid()
    new_name_entry.focus_set()

def transform_module_to_package(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        editor.refactoring.transform_module_to_package(resource)

def local_rename(context):
    toplevel = Tkinter.Toplevel()
    toplevel.title('Rename Variable In File')
    frame = Tkinter.Frame(toplevel)
    label = Tkinter.Label(frame, text='New Name :')
    label.grid(row=0, column=0)
    new_name_entry = Tkinter.Entry(frame)
    new_name_entry.grid(row=0, column=1)
    def ok(event=None):
        resource = context.get_active_editor().get_file()
        editor = context.get_active_editor().get_editor()
        editor.refactoring.local_rename(resource,
                                        editor.get_current_offset(),
                                        new_name_entry.get())
        toplevel.destroy()
    def cancel(event=None):
        toplevel.destroy()

    ok_button = Tkinter.Button(frame, text='Done', command=ok)
    cancel_button = Tkinter.Button(frame, text='Cancel', command=cancel)
    ok_button.grid(row=1, column=0)
    new_name_entry.bind('<Return>', lambda event: ok())
    new_name_entry.bind('<Escape>', lambda event: cancel())
    new_name_entry.bind('<Control-g>', lambda event: cancel())
    cancel_button.grid(row=1, column=1)
    frame.grid()
    new_name_entry.focus_set()

def extract_method(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor()._extract_method_dialog()

def undo_last_refactoring(context):
    if context.get_core().get_open_project():
        context.get_core().get_open_project().get_pycore().\
                get_refactoring().undo_last_refactoring()
    
def introduce_factory(context):
    if not context.get_active_editor():
        return
    toplevel = Tkinter.Toplevel()
    toplevel.title('Introduce Factory Method Refactoring')
    frame = Tkinter.Frame(toplevel)
    label = Tkinter.Label(frame, text='Factory Method Name :')
    new_name_entry = Tkinter.Entry(frame)
        
    global_factory_val = Tkinter.BooleanVar(False)
    static_factory_button = Tkinter.Radiobutton(frame, variable=global_factory_val,
                                                value=False, text='Use static method')
    global_factory_button = Tkinter.Radiobutton(frame, variable=global_factory_val,
                                                value=True, text='Use global function')
    
    def ok(event=None):
        resource = context.get_active_editor().get_file()
        editor = context.get_active_editor().get_editor()
        editor.refactoring.introduce_factory(resource, editor.get_current_offset(),
                                             new_name_entry.get(),
                                             global_factory=global_factory_val.get())
        toplevel.destroy()
    def cancel(event=None):
        toplevel.destroy()

    ok_button = Tkinter.Button(frame, text='Done', command=ok)
    cancel_button = Tkinter.Button(frame, text='Cancel', command=cancel)
    new_name_entry.bind('<Return>', lambda event: ok())
    new_name_entry.bind('<Escape>', lambda event: cancel())
    new_name_entry.bind('<Control-g>', lambda event: cancel())
        
    label.grid(row=0, column=0)
    new_name_entry.grid(row=0, column=1)
    static_factory_button.grid(row=1, column=0)
    global_factory_button.grid(row=1, column=1)
    ok_button.grid(row=2, column=0)
    cancel_button.grid(row=2, column=1)
    frame.grid()
    new_name_entry.focus_set()

    
actions = []
actions.append(SimpleAction('Rename Refactoring', ConfirmAllEditorsAreSaved(rename), 'M-R',
                            MenuAddress(['Refactor', 'Rename'], 'r')))
actions.append(SimpleAction('Extract Method', ConfirmAllEditorsAreSaved(extract_method), 'M-M',
                            MenuAddress(['Refactor', 'Extract Method'], 'e')))
actions.append(SimpleAction('Rename in File', ConfirmAllEditorsAreSaved(local_rename), None,
                            MenuAddress(['Refactor', 'Rename in File'], 'f')))
actions.append(SimpleAction('Transform Module to Package', 
                            ConfirmAllEditorsAreSaved(transform_module_to_package), None,
                            MenuAddress(['Refactor', 'Transform Module to Package'], 't', 1)))
actions.append(SimpleAction('Introduce Factory Method', 
                            ConfirmAllEditorsAreSaved(introduce_factory), None,
                            MenuAddress(['Refactor', 'Introduce Factory Method'], 'i', 1)))
actions.append(SimpleAction('Undo Last Refactoring', 
                            ConfirmAllEditorsAreSaved(undo_last_refactoring), None,
                            MenuAddress(['Refactor', 'Undo Last Refactoring'], 'u', 2)))

core = rope.ui.core.Core.get_core()
for action in actions:
    core.register_action(action)

