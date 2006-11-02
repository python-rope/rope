import Tkinter
import ScrolledText

import rope.refactor.importutils
import rope.ui.core
import rope.refactor.change
from rope.ui.menubar import MenuAddress
from rope.ui.extension import SimpleAction
from rope.ui.uihelpers import TreeViewHandle, TreeView, DescriptionList


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


class PreviewAndCommitChanges(object):
    
    def __init__(self, refactoring, changes):
        self.refactoring = refactoring
        self.changes = changes
    
    def preview(self):
        toplevel = Tkinter.Toplevel()
        toplevel.title('Preview Changes')
        
        def description(change):
            return change.get_description()
        description_list = DescriptionList(toplevel, 'Changes', description)
        for change in self.changes.changes:
            description_list.add_entry(change)
        
        frame = Tkinter.Frame(toplevel)
        def ok(event=None):
            toplevel.destroy()
            self.commit()
        def cancel(event=None):
            toplevel.destroy()
        ok_button = Tkinter.Button(frame, text='OK', command=ok)
        cancel_button = Tkinter.Button(frame, text='Cancel', command=cancel)
        ok_button.grid(row=1, column=0)
        #toplevel.bind('<Return>', lambda event: ok())
        toplevel.bind('<Escape>', lambda event: cancel())
        toplevel.bind('<Control-g>', lambda event: cancel())
        cancel_button.grid(row=1, column=1)
        frame.grid()
    
    def commit(self):
        self.refactoring.add_and_commit_changes(self.changes)


class RefactoringDialog(object):
    
    def __init__(self, refactoring, title):
        self.refactoring = refactoring
        self.title = title
    
    def show(self):
        self.toplevel = Tkinter.Toplevel()
        self.toplevel.title(self.title)
        self.toplevel.bind('<Escape>', lambda event: self._cancel())
        self.toplevel.bind('<Control-g>', lambda event: self._cancel())
        frame = self._get_dialog_frame()
    
        ok_button = Tkinter.Button(self.toplevel, text='Done', command=self._ok)
        preview_button = Tkinter.Button(self.toplevel, text='Preview', command=self._preview)
        cancel_button = Tkinter.Button(self.toplevel, text='Cancel', command=self._cancel)
        ok_button.grid(row=1, column=0)
        preview_button.grid(row=1, column=1)
        cancel_button.grid(row=1, column=2)
        frame.grid(row=0, columnspan=3)
    
    def _ok(self, event=None):
        PreviewAndCommitChanges(self.refactoring, self._get_changes()).commit()
        self.toplevel.destroy()
        
    def _preview(self, event=None):
        PreviewAndCommitChanges(self.refactoring, self._get_changes()).preview()
        self.toplevel.destroy()
    
    def _cancel(self, event=None):
        self.toplevel.destroy()
    

class RenameDialog(RefactoringDialog):
    
    def __init__(self, context, title, is_local=False):
        resource = context.get_active_editor().get_file()
        editor = context.get_active_editor().get_editor()
        super(RenameDialog, self).__init__(_get_refactoring(context), title)
        self.is_local = is_local
        self.renamer = rope.refactor.rename.RenameRefactoring(
            context.get_core().get_open_project().get_pycore(), 
            resource, editor.get_current_offset())
    
    def _get_changes(self):
        new_name = self.new_name_entry.get()
        return self.renamer.get_changes(new_name, in_file=self.is_local)

    def _get_dialog_frame(self):
        frame = Tkinter.Frame(self.toplevel)
        label = Tkinter.Label(frame, text='New Name :')
        label.grid(row=0, column=0)
        self.new_name_entry = Tkinter.Entry(frame)
        self.new_name_entry.insert(0, self.renamer.get_old_name())
        self.new_name_entry.select_range(0, Tkinter.END)
        self.new_name_entry.grid(row=0, column=1, columnspan=2)
        self.new_name_entry.bind('<Return>', lambda event: self._ok())
        self.new_name_entry.focus_set()
        return frame


def rename(context):
    RenameDialog(context, 'Rename Refactoring').show()

def local_rename(context):
    RenameDialog(context, 'Rename Refactoring', True).show()

def transform_module_to_package(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        _get_refactoring(context).transform_module_to_package(resource)

class ExtractDialog(RefactoringDialog):
    
    def __init__(self, context, do_extract, kind):
        editor = context.get_active_editor().get_editor()
        super(ExtractDialog, self).__init__(_get_refactoring(context),
                                            'Extract ' + kind)
        self.do_extract = do_extract
        self.kind = kind
    
    def _get_changes(self):
        return self.do_extract(self.new_name_entry.get())
    
    def _get_dialog_frame(self):
        frame = Tkinter.Frame(self.toplevel)
        label = Tkinter.Label(frame, text='New %s Name :' % self.kind)
        label.grid(row=0, column=0)
        self.new_name_entry = Tkinter.Entry(frame)
        self.new_name_entry.grid(row=0, column=1)

        self.new_name_entry.bind('<Return>', lambda event: self._ok())
        self.new_name_entry.focus_set()
        return frame


def extract_method(context):
    def do_extract(new_name):
        editor = context.get_active_editor().get_editor()
        resource = context.get_active_editor().get_file()
        start_offset, end_offset = editor.get_region_offset()
        return rope.refactor.extract.ExtractMethodRefactoring(
            context.get_core().get_open_project().get_pycore(),
            resource, start_offset, end_offset).get_changes(new_name)
    ExtractDialog(context, do_extract, 'Method').show()

def extract_variable(context):
    def do_extract(new_name):
        editor = context.get_active_editor().get_editor()
        resource = context.get_active_editor().get_file()
        start_offset, end_offset = editor.get_region_offset()
        return rope.refactor.extract.ExtractVariableRefactoring(
            context.get_core().get_open_project().get_pycore(),
            resource, start_offset, end_offset).get_changes(new_name)
    ExtractDialog(context, do_extract, 'Variable').show()


class IntroduceFactoryDialog(RefactoringDialog):
    
    def __init__(self, context):
        resource = context.get_active_editor().get_file()
        editor = context.get_active_editor().get_editor()
        super(IntroduceFactoryDialog, self).__init__(
            _get_refactoring(context), 'Introduce Factory Method Refactoring')
        self.introducer = rope.refactor.introduce_factory.IntroduceFactoryRefactoring(
            context.get_core().get_open_project().get_pycore(), 
            resource, editor.get_current_offset())
    
    def _get_changes(self):
        return self.introducer.get_changes(
            self.new_name_entry.get(), global_factory=self.global_factory_val.get())
    
    def _get_dialog_frame(self):
        frame = Tkinter.Frame(self.toplevel)
        label = Tkinter.Label(frame, text='Factory Method Name :')
        self.new_name_entry = Tkinter.Entry(frame)
        
        self.global_factory_val = Tkinter.BooleanVar(False)
        static_factory_button = Tkinter.Radiobutton(frame, variable=self.global_factory_val,
                                                    value=False, text='Use static method')
        global_factory_button = Tkinter.Radiobutton(frame, variable=self.global_factory_val,
                                                    value=True, text='Use global function')
        self.new_name_entry.bind('<Return>', lambda event: self._ok())
        
        label.grid(row=0, column=0)
        self.new_name_entry.grid(row=0, column=1)
        static_factory_button.grid(row=1, column=0)
        global_factory_button.grid(row=1, column=1)
        self.new_name_entry.focus_set()
        return frame


def introduce_factory(context):
    IntroduceFactoryDialog(context).show()

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
    if context.project:
        def undo():
            context.project.get_pycore().get_refactoring().undo()
        _confirm_action('Undoing Refactoring',
                        'Undo refactoring might change many files. Proceed?',
                        undo)
def redo_refactoring(context):
    if context.project:
        def redo():
            context.project.get_pycore().get_refactoring().redo()
        _confirm_action('Redoing Refactoring',
                        'Redo refactoring might change many files. Proceed?',
                        redo)
    

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


class MoveDialog(RefactoringDialog):
    
    def __init__(self, context):
        resource = context.get_active_editor().get_file()
        editor = context.get_active_editor().get_editor()
        self.project = context.get_core().get_open_project()
        super(MoveDialog, self).__init__(_get_refactoring(context), 'Move Refactoring')
        self.mover = rope.refactor.move.MoveRefactoring(
            context.get_core().get_open_project().get_pycore(), 
            resource, editor.get_current_offset())
    
    def _get_changes(self):
        destination = self.project.get_pycore().find_module(self.new_name_entry.get())
        return self.mover.get_changes(destination)
    
    def _get_dialog_frame(self):
        frame = Tkinter.Frame(self.toplevel)
        label = Tkinter.Label(frame, text='Destination Module :')
        label.grid(row=0, column=0)
        self.new_name_entry = Tkinter.Entry(frame)
        self.new_name_entry.grid(row=0, column=1)
        def do_select(resource):
            name = rope.refactor.importutils.ImportTools.get_module_name(
                self.project.get_pycore(), resource)
            self.new_name_entry.delete(0, Tkinter.END)
            self.new_name_entry.insert(0, name)
        def browse():
            toplevel = Tkinter.Toplevel()
            toplevel.title('Choose Destination Module')
            tree_handle = _ModuleViewHandle(self.project, toplevel, do_select)
            tree_view = TreeView(toplevel, tree_handle, title='Destination Module')
            for folder in self.project.get_pycore().get_source_folders():
                tree_view.add_entry(folder)
            tree_view.list.focus_set()
            toplevel.grab_set()

        browse_button = Tkinter.Button(frame, text='...', command=browse)
        browse_button.grid(row=0, column=2)
        self.new_name_entry.bind('<Return>', lambda event: self._ok())
        self.new_name_entry.bind('<Escape>', lambda event: self._cancel())
        self.new_name_entry.bind('<Control-g>', lambda event: self._cancel())
        frame.grid()
        self.new_name_entry.focus_set()
        return frame

def move(context):
    MoveDialog(context).show()

def organize_imports(context):
    if not context.get_active_editor():
        return
    file_editor = context.get_active_editor()
    import_organizer = _get_refactoring(context).get_import_organizer()
    if import_organizer:
        import_organizer.organize_imports(file_editor.get_file())

def expand_star_imports(context):
    if not context.get_active_editor():
        return
    file_editor = context.get_active_editor()
    import_organizer = _get_refactoring(context).get_import_organizer()
    if import_organizer:
        import_organizer.expand_star_imports(file_editor.get_file())

def transform_froms_to_imports(context):
    if not context.get_active_editor():
        return
    file_editor = context.get_active_editor()
    import_organizer = _get_refactoring(context).get_import_organizer()
    if import_organizer:
        import_organizer.transform_froms_to_imports(file_editor.get_file())

def transform_relatives_to_absolute(context):
    if not context.get_active_editor():
        return
    file_editor = context.get_active_editor()
    import_organizer = _get_refactoring(context).get_import_organizer()
    if import_organizer:
        import_organizer.transform_relatives_to_absolute(file_editor.get_file())

def inline(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        _get_refactoring(context).inline_local_variable(resource, editor.get_current_offset())
    
def encapsulate_field(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        _get_refactoring(context).encapsulate_field(
            resource, editor.get_current_offset())
    
def convert_local_to_field(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        _get_refactoring(context).convert_local_variable_to_field(
            resource, editor.get_current_offset())

def _get_refactoring(context):
    return context.project.get_pycore().get_refactoring()


actions = []
actions.append(SimpleAction('Rename Refactoring', ConfirmAllEditorsAreSaved(rename), 'M-R',
                            MenuAddress(['Refactor', 'Rename'], 'n'), ['python']))
actions.append(SimpleAction('Extract Method', ConfirmAllEditorsAreSaved(extract_method), 'M-M',
                            MenuAddress(['Refactor', 'Extract Method'], 'x'), ['python']))
actions.append(SimpleAction('Move Refactoring', ConfirmAllEditorsAreSaved(move), 'M-V',
                            MenuAddress(['Refactor', 'Move'], 'm'), ['python']))
actions.append(SimpleAction('Inline Local Variable', ConfirmAllEditorsAreSaved(inline), 'M-I',
                            MenuAddress(['Refactor', 'Inline Local Variable'], 'i'), ['python']))
actions.append(SimpleAction('Extract Local Variable', ConfirmAllEditorsAreSaved(extract_variable), None,
                            MenuAddress(['Refactor', 'Extract Local Variable'], 'l'), ['python']))
actions.append(SimpleAction('Rename in File', ConfirmAllEditorsAreSaved(local_rename), None,
                            MenuAddress(['Refactor', 'Rename in File'], 'e'), ['python']))
actions.append(SimpleAction('Introduce Factory Method', 
                            ConfirmAllEditorsAreSaved(introduce_factory), None,
                            MenuAddress(['Refactor', 'Introduce Factory Method'], 'f', 1),
                            ['python']))
actions.append(SimpleAction('Encapsulate Field', 
                            ConfirmAllEditorsAreSaved(encapsulate_field), None,
                            MenuAddress(['Refactor', 'Encapsulate Field'], 's', 1),
                            ['python']))
actions.append(SimpleAction('Convert Local Variable to Field', 
                            ConfirmAllEditorsAreSaved(convert_local_to_field), None,
                            MenuAddress(['Refactor', 'Convert Local Variable to Field'], 'b', 1),
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
                            MenuAddress(['Refactor', 'Expand Star Imports'], 'p', 2),
                            ['python']))
actions.append(SimpleAction('Transform Relatives to Absolute', 
                            ConfirmAllEditorsAreSaved(transform_relatives_to_absolute), None,
                            MenuAddress(['Refactor', 'Transform Relatives to Absolute'], 'a', 2),
                            ['python']))
actions.append(SimpleAction('Transform Froms to Imports', 
                            ConfirmAllEditorsAreSaved(transform_froms_to_imports), None,
                            MenuAddress(['Refactor', 'Transform Froms to Imports'], 'r', 2),
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

