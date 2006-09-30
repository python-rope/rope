import Tkinter

import rope.ui.core
from rope.ui.menubar import MenuAddress
from rope.ui.extension import SimpleAction
from rope.ui.uihelpers import TreeViewHandle, TreeView


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

def undo_refactoring(context):
    if context.get_core().get_open_project():
        context.get_core().get_open_project().get_pycore().\
                get_refactoring().undo()
    
def redo_refactoring(context):
    if context.get_core().get_open_project():
        context.get_core().get_open_project().get_pycore().\
                get_refactoring().redo()
    
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

class _ModuleViewHandle(TreeViewHandle):
    
    def __init__(self, core, toplevel, do_select):
        self.core = core
        self.toplevel = toplevel
        self.do_select = do_select

    def entry_to_string(self, resource):
        result = resource.get_name()
        if result == '':
            result = 'project root'
        return result
    
    def get_children(self, resource):
        if resource.is_folder():
            return [child for child in resource.get_children()
                    if (not child.get_name().startswith('.') and
                        not child.get_name().endswith('.pyc'))]
        else:
            return []

    def selected(self, resource):
        self.toplevel.destroy()
        self.do_select(resource)
    
    def canceled(self):
        self.toplevel.destroy()

    def focus_went_out(self):
        pass

def move(context):
    if not context.get_active_editor():
        return
    project = context.get_core().get_open_project()
    toplevel = Tkinter.Toplevel()
    toplevel.title('Move Refactoring')
    frame = Tkinter.Frame(toplevel)
    label = Tkinter.Label(frame, text='Destination Module :')
    label.grid(row=0, column=0)
    new_name_entry = Tkinter.Entry(frame)
    new_name_entry.grid(row=0, column=1)
    def ok(event=None):
        resource = context.get_active_editor().get_file()
        editor = context.get_active_editor().get_editor()
        destination = project.get_resource(new_name_entry.get())
        editor.refactoring.move(resource,
                                editor.get_current_offset(),
                                destination)
        toplevel.destroy()
    def cancel(event=None):
        toplevel.destroy()
    def do_select(folder):
        new_name_entry.delete(0, Tkinter.END)
        new_name_entry.insert(0, folder.get_path())
    def browse():
        toplevel = Tkinter.Toplevel()
        toplevel.title('Choose Destination Module')
        tree_handle = _ModuleViewHandle(core, toplevel, do_select)
        tree_view = TreeView(toplevel, tree_handle, title='Destination Module')
        tree_view.add_entry(context.get_core().project.get_root_folder())
        tree_view.list.focus_set()
        toplevel.grab_set()

    browse_button = Tkinter.Button(frame, text='...', command=browse)
    browse_button.grid(row=0, column=2)
    ok_button = Tkinter.Button(frame, text='Done', command=ok)
    cancel_button = Tkinter.Button(frame, text='Cancel', command=cancel)
    ok_button.grid(row=1, column=0)
    new_name_entry.bind('<Return>', lambda event: ok())
    new_name_entry.bind('<Escape>', lambda event: cancel())
    new_name_entry.bind('<Control-g>', lambda event: cancel())
    cancel_button.grid(row=1, column=1)
    frame.grid()
    new_name_entry.focus_set()

def organize_imports(context):
    if not context.get_active_editor():
        return
    file_editor = context.get_active_editor()
    import_organizer = file_editor.get_editor().refactoring.get_import_organizer()
    if import_organizer:
        import_organizer.organize_imports(file_editor.get_file())

def expand_star_imports(context):
    if not context.get_active_editor():
        return
    file_editor = context.get_active_editor()
    import_organizer = file_editor.get_editor().refactoring.get_import_organizer()
    if import_organizer:
        import_organizer.expand_star_imports(file_editor.get_file())

def transform_froms_to_imports(context):
    if not context.get_active_editor():
        return
    file_editor = context.get_active_editor()
    import_organizer = file_editor.get_editor().refactoring.get_import_organizer()
    if import_organizer:
        import_organizer.transform_froms_to_imports(file_editor.get_file())

def transform_relatives_to_absolute(context):
    if not context.get_active_editor():
        return
    file_editor = context.get_active_editor()
    import_organizer = file_editor.get_editor().refactoring.get_import_organizer()
    if import_organizer:
        import_organizer.transform_relatives_to_absolute(file_editor.get_file())


actions = []
actions.append(SimpleAction('Rename Refactoring', ConfirmAllEditorsAreSaved(rename), 'M-R',
                            MenuAddress(['Refactor', 'Rename'], 'r')))
actions.append(SimpleAction('Extract Method', ConfirmAllEditorsAreSaved(extract_method), 'M-M',
                            MenuAddress(['Refactor', 'Extract Method'], 'e')))
actions.append(SimpleAction('Move Refactoring', ConfirmAllEditorsAreSaved(move), 'M-V',
                            MenuAddress(['Refactor', 'Move'], 'v')))
actions.append(SimpleAction('Rename in File', ConfirmAllEditorsAreSaved(local_rename), None,
                            MenuAddress(['Refactor', 'Rename in File'], 'f')))
actions.append(SimpleAction('Introduce Factory Method', 
                            ConfirmAllEditorsAreSaved(introduce_factory), None,
                            MenuAddress(['Refactor', 'Introduce Factory Method'], 'i', 1)))
actions.append(SimpleAction('Transform Module to Package', 
                            ConfirmAllEditorsAreSaved(transform_module_to_package), None,
                            MenuAddress(['Refactor', 'Transform Module to Package'], 't', 1)))
actions.append(SimpleAction('Organize Imports', 
                            ConfirmAllEditorsAreSaved(organize_imports), 'M-O',
                            MenuAddress(['Refactor', 'Organize Imports'], 'o', 2)))
actions.append(SimpleAction('Expand Star Imports', 
                            ConfirmAllEditorsAreSaved(expand_star_imports), None,
                            MenuAddress(['Refactor', 'Expand Star Imports'], 'x', 2)))
actions.append(SimpleAction('Transform Relatives to Absolute', 
                            ConfirmAllEditorsAreSaved(transform_relatives_to_absolute), None,
                            MenuAddress(['Refactor', 'Transform Relatives to Absolute'], 'a', 2)))
actions.append(SimpleAction('Transform Froms to Imports', 
                            ConfirmAllEditorsAreSaved(transform_froms_to_imports), None,
                            MenuAddress(['Refactor', 'Transform Froms to Imports'], 's', 2)))
actions.append(SimpleAction('Undo Refactoring', 
                            ConfirmAllEditorsAreSaved(undo_refactoring), None,
                            MenuAddress(['Refactor', 'Undo Refactoring'], 'u', 3)))
actions.append(SimpleAction('Undo Last Refactoring', 
                            ConfirmAllEditorsAreSaved(redo_refactoring), None,
                            MenuAddress(['Refactor', 'Redo Refactoring'], 'd', 3)))

core = rope.ui.core.Core.get_core()
for action in actions:
    core.register_action(action)

