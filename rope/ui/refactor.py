import Tkinter

import rope.importutils
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


def _rename_dialog(do_rename, title):
    toplevel = Tkinter.Toplevel()
    toplevel.title(title)
    frame = Tkinter.Frame(toplevel)
    label = Tkinter.Label(frame, text='New Name :')
    label.grid(row=0, column=0)
    new_name_entry = Tkinter.Entry(frame)
    new_name_entry.grid(row=0, column=1)
    def ok(event=None):
        do_rename(new_name_entry.get())
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

def rename(context):
    def do_rename(new_name):
        resource = context.get_active_editor().get_file()
        editor = context.get_active_editor().get_editor()
        editor.refactoring.rename(resource,
                                  editor.get_current_offset(),
                                  new_name)
    _rename_dialog(do_rename, 'Rename Refactoring')

def transform_module_to_package(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        editor.refactoring.transform_module_to_package(resource)

def local_rename(context):
    def do_rename(new_name):
        resource = context.get_active_editor().get_file()
        editor = context.get_active_editor().get_editor()
        editor.refactoring.local_rename(resource,
                                        editor.get_current_offset(),
                                        new_name)
    _rename_dialog(do_rename, 'Rename Variable In File')

def _extract_dialog(do_extract, kind):
    toplevel = Tkinter.Toplevel()
    toplevel.title('Extract ' + kind)
    frame = Tkinter.Frame(toplevel)
    label = Tkinter.Label(frame, text='New %s Name :' % kind)
    label.grid(row=0, column=0)
    new_name_entry = Tkinter.Entry(frame)
    new_name_entry.grid(row=0, column=1)
    def ok(event=None):
        do_extract(new_name_entry.get())
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
    def do_extract(new_name):
        editor = context.get_active_editor().get_editor()
        resource = context.get_active_editor().get_file()
        (start_offset, end_offset) = editor.get_region_offset()
        editor.refactoring.extract_method(resource,
                                          start_offset, end_offset,
                                          new_name)
    _extract_dialog(do_extract, 'Method')

def extract_variable(context):
    def do_extract(new_name):
        editor = context.get_active_editor().get_editor()
        resource = context.get_active_editor().get_file()
        (start_offset, end_offset) = editor.get_region_offset()
        editor.refactoring.extract_variable(resource,
                                            start_offset, end_offset,
                                            new_name)
    _extract_dialog(do_extract, 'Variable')

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

def undo_refactoring(context):
    if context.get_core().get_open_project():
        def undo():
            context.get_core().get_open_project().get_pycore().\
                    get_refactoring().undo()
        _confirm_action('Undoing Refactoring',
                        'Undo refactoring might change many files. Proceed?',
                        undo)
def redo_refactoring(context):
    if context.get_core().get_open_project():
        def redo():
            context.get_core().get_open_project().get_pycore().\
                    get_refactoring().redo()
        _confirm_action('Redoing Refactoring',
                        'Redo refactoring might change many files. Proceed?',
                        redo)
    
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
    
    def __init__(self, project, toplevel, do_select):
        self.project = project
        self.toplevel = toplevel
        self.do_select = do_select

    def entry_to_string(self, resource):
        if resource.is_folder():
            result = resource.get_name()
            if result == '':
                result = 'project root'
            return result
        else:
            return resource.get_name()[:-3]
    
    def get_children(self, resource):
        if resource.is_folder():
            return [child for child in resource.get_children()
                    if not child.get_name().startswith('.') and 
                    (child.is_folder() or child.get_name().endswith('.py'))]
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
        destination = project.get_pycore().find_module(new_name_entry.get())
        editor.refactoring.move(resource,
                                editor.get_current_offset(),
                                destination)
        toplevel.destroy()
    def cancel(event=None):
        toplevel.destroy()
    def do_select(resource):
        name = rope.importutils.ImportTools.get_module_name(project.get_pycore(), resource)
        new_name_entry.delete(0, Tkinter.END)
        new_name_entry.insert(0, name)
    def browse():
        toplevel = Tkinter.Toplevel()
        toplevel.title('Choose Destination Module')
        tree_handle = _ModuleViewHandle(core.get_open_project(), toplevel, do_select)
        tree_view = TreeView(toplevel, tree_handle, title='Destination Module')
        for folder in project.get_pycore().get_source_folders():
            tree_view.add_entry(folder)
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

def inline(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        editor.refactoring.inline_local_variable(resource, editor.get_current_offset())
    
def encapsulate_field(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        editor.refactoring.encapsulate_field(resource, editor.get_current_offset())
    
def convert_local_to_field(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        editor.refactoring.convert_local_variable_to_field(
            resource, editor.get_current_offset())


actions = []
actions.append(SimpleAction('Rename Refactoring', ConfirmAllEditorsAreSaved(rename), 'M-R',
                            MenuAddress(['Refactor', 'Rename'], 'r'), ['python']))
actions.append(SimpleAction('Extract Method', ConfirmAllEditorsAreSaved(extract_method), 'M-M',
                            MenuAddress(['Refactor', 'Extract Method'], 'e'), ['python']))
actions.append(SimpleAction('Move Refactoring', ConfirmAllEditorsAreSaved(move), 'M-V',
                            MenuAddress(['Refactor', 'Move'], 'v'), ['python']))
actions.append(SimpleAction('Inline Local Variable', ConfirmAllEditorsAreSaved(inline), 'M-I',
                            MenuAddress(['Refactor', 'Inline Local Variable'], 'i'), ['python']))
actions.append(SimpleAction('Extract Local Variable', ConfirmAllEditorsAreSaved(extract_variable), None,
                            MenuAddress(['Refactor', 'Extract Local Variable'], 'l'), ['python']))
actions.append(SimpleAction('Rename in File', ConfirmAllEditorsAreSaved(local_rename), None,
                            MenuAddress(['Refactor', 'Rename in File'], 'f'), ['python']))
actions.append(SimpleAction('Introduce Factory Method', 
                            ConfirmAllEditorsAreSaved(introduce_factory), None,
                            MenuAddress(['Refactor', 'Introduce Factory Method'], 'c', 1),
                            ['python']))
actions.append(SimpleAction('Encapsulate Field', 
                            ConfirmAllEditorsAreSaved(encapsulate_field), None,
                            MenuAddress(['Refactor', 'Encapsulate Field'], 'n', 1),
                            ['python']))
actions.append(SimpleAction('Convert Local Variable to Field', 
                            ConfirmAllEditorsAreSaved(convert_local_to_field), None,
                            MenuAddress(['Refactor', 'Convert Local Variable to Field'], None, 1),
                            ['python']))
actions.append(SimpleAction('Transform Module to Package', 
                            ConfirmAllEditorsAreSaved(transform_module_to_package), None,
                            MenuAddress(['Refactor', 'Transform Module to Package'], 't', 1), 
                            ['python']))
actions.append(SimpleAction('Organize Imports', 
                            ConfirmAllEditorsAreSaved(organize_imports), 'C-O',
                            MenuAddress(['Refactor', 'Organize Imports'], 'o', 2), ['python']))
actions.append(SimpleAction('Expand Star Imports', 
                            ConfirmAllEditorsAreSaved(expand_star_imports), None,
                            MenuAddress(['Refactor', 'Expand Star Imports'], 'x', 2),
                            ['python']))
actions.append(SimpleAction('Transform Relatives to Absolute', 
                            ConfirmAllEditorsAreSaved(transform_relatives_to_absolute), None,
                            MenuAddress(['Refactor', 'Transform Relatives to Absolute'], 'a', 2),
                            ['python']))
actions.append(SimpleAction('Transform Froms to Imports', 
                            ConfirmAllEditorsAreSaved(transform_froms_to_imports), None,
                            MenuAddress(['Refactor', 'Transform Froms to Imports'], 's', 2),
                            ['python']))
actions.append(SimpleAction('Undo Refactoring', 
                            ConfirmAllEditorsAreSaved(undo_refactoring), None,
                            MenuAddress(['Refactor', 'Undo Refactoring'], 'u', 3), ['python']))
actions.append(SimpleAction('Undo Last Refactoring', 
                            ConfirmAllEditorsAreSaved(redo_refactoring), None,
                            MenuAddress(['Refactor', 'Redo Refactoring'], 'd', 3), ['python']))

core = rope.ui.core.Core.get_core()
core._add_menu_cascade(MenuAddress(['Refactor'], 't'), ['python'])
for action in actions:
    core.register_action(action)

