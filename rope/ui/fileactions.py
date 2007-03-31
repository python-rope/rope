import re

import Tkinter

import rope.base.project
import rope.ui.actionhelpers
import rope.ui.core
from rope.ui import uihelpers
from rope.ui.actionhelpers import ConfirmEditorsAreSaved
from rope.ui.extension import SimpleAction
from rope.ui.menubar import MenuAddress
from rope.ui.uihelpers import (TreeViewHandle, TreeView, find_item_dialog,
                               SearchableList, SearchableListHandle)


def open_project(context):
    context.get_core()._open_project_dialog()

def close_project(context):
    context.get_core()._close_project_dialog()

class _FolderViewHandle(TreeViewHandle):

    def __init__(self, core, toplevel, do_select):
        self.core = core
        self.toplevel = toplevel
        self.do_select = do_select

    def entry_to_string(self, resource):
        result = resource.name
        if result == '':
            result = 'project root'
        return result

    def get_children(self, resource):
        if resource.is_folder():
            return [child for child in resource.get_children()
                    if not child.name.startswith('.') and
                    child.is_folder()]
        else:
            return []

    def selected(self, resource):
        self.toplevel.destroy()
        self.do_select(resource)

    def canceled(self):
        self.toplevel.destroy()

    def focus_went_out(self):
        pass


def _create_resource_dialog(core, creation_callback,
                            resource_name='File', parent_name='Parent Folder'):
    """Ask user about the parent folder and the name of the resource to be created

    creation_callback is a function accepting the parent and the name

    """
    if not rope.ui.actionhelpers.check_project(core):
        return
    toplevel = Tkinter.Toplevel()
    toplevel.title('New ' + resource_name)
    create_dialog = Tkinter.Frame(toplevel)
    parent_label = Tkinter.Label(create_dialog, text=parent_name)
    parent_entry = Tkinter.Entry(create_dialog)
    def do_select(folder):
        parent_entry.delete(0, Tkinter.END)
        parent_entry.insert(0, folder.path)
    def show_directory_view():
        toplevel = Tkinter.Toplevel()
        toplevel.title('Select ' + parent_name)
        tree_handle = _FolderViewHandle(core, toplevel, do_select)
        tree_view = TreeView(toplevel, tree_handle, title='Resources')
        tree_view.add_entry(core.project.root)
        toplevel.grab_set()

    parent_browse = Tkinter.Button(create_dialog, text='...', command=show_directory_view)
    resource_label = Tkinter.Label(create_dialog, text=('New ' + resource_name))
    resource_entry = Tkinter.Entry(create_dialog)

    def do_create_resource():
        parent_folder = core.project.get_resource(parent_entry.get())
        creation_callback(parent_folder, resource_entry.get())
        toplevel.destroy()
    def cancel():
        toplevel.destroy()
    parent_entry.bind('<Return>', lambda event: do_create_resource())
    parent_entry.bind('<Escape>', lambda event: cancel())
    parent_entry.bind('<Control-g>', lambda event: cancel())
    resource_entry.bind('<Return>', lambda event: do_create_resource())
    resource_entry.bind('<Escape>', lambda event: cancel())
    resource_entry.bind('<Control-g>', lambda event: cancel())
    parent_label.grid(row=0, column=0, sticky=Tkinter.W)
    parent_entry.grid(row=0, column=1)
    parent_browse.grid(row=0, column=2)
    resource_label.grid(row=1, column=0, sticky=Tkinter.W)
    resource_entry.grid(row=1, column=1)
    create_dialog.grid()
    resource_entry.focus_set()
    toplevel.grab_set()
    core.root.wait_window(toplevel)

def create_file(context):
    def do_create_file(parent_folder, file_name):
        new_file = parent_folder.create_file(file_name)
        context.get_core().editor_manager.get_resource_editor(new_file)
    _create_resource_dialog(context.get_core(), do_create_file, 'File', 'Parent Folder')

def create_folder(context):
    def do_create_folder(parent_folder, folder_name):
        new_file = parent_folder.create_folder(folder_name)
    _create_resource_dialog(context.get_core(), do_create_folder, 'Folder', 'Parent Folder')

def create_module(context):
    def do_create_module(source_folder, module_name):
        new_module = context.get_core().project.get_pycore().\
                     create_module(source_folder, module_name)
        context.get_core().editor_manager.get_resource_editor(new_module)
    _create_resource_dialog(context.get_core(), do_create_module, 'Module', 'Source Folder')

def create_package(context):
    def do_create_package(source_folder, package_name):
        new_package = context.get_core().project.get_pycore().\
                      create_package(source_folder,
                                     package_name)
        context.get_core().editor_manager.get_resource_editor(new_package.get_child('__init__.py'))
    _create_resource_dialog(context.get_core(), do_create_package, 'Package', 'Source Folder')


class _NormalSelector(object):

    def __init__(self, pattern):
        self.pattern = pattern

    def can_select(self, input_str):
        return input_str.startswith(self.pattern)


class _RESelector(object):

    def __init__(self, pattern):
        self.pattern = re.compile((pattern + '*').replace('?', '.').
                                  replace('*', '.*'))

    def can_select(self, input_str):
        return self.pattern.match(input_str)


class FindFileHandle(object):

    def __init__(self, context):
        self.core = context.core
        self.project = context.project
        self.last_keyword = None
        self.last_result = None

    def find_matches(self, starting):
        """Returns the Files in the project whose names starts with starting"""
        files = []
        if self.last_keyword is not None and starting.startswith(self.last_keyword):
            files = self.last_result
        else:
            files = self.project.get_files()
            files.sort(cmp=self._compare_files)
        result = []
        selector = self._create_selector(starting)
        for file_ in files:
            if selector.can_select(file_.name):
                result.append(file_)
            elif file_.name == '__init__.py' and \
                 selector.can_select(file_.parent.name):
                result.append(file_)
        self.last_keyword = starting
        self.last_result = result
        return result

    def _create_selector(self, pattern):
        if '?' in pattern or '*' in pattern:
            return _RESelector(pattern)
        else:
            return _NormalSelector(pattern)

    def selected(self, resource):
        self.core.open_file(resource.path)

    def to_string(self, resource):
        return resource.path

    def to_name(self, resource):
        return resource.name

    def _is_init_dot_py(self, file):
        return file.name == '__init__.py'

    def _compare_files(self, file1, file2):
        if self._is_init_dot_py(file1) or self._is_init_dot_py(file2):
            if self._is_init_dot_py(file1) and not self._is_init_dot_py(file2):
                return 1
            if not self._is_init_dot_py(file1) and self._is_init_dot_py(file2):
                return -1
            return cmp(file1.path, file2.path)
        if file1.name != file2.name:
            return cmp(file1.name, file2.name)
        return cmp(file1.path, file2.path)


def find_file(context):
    if not rope.ui.actionhelpers.check_project(context.core):
        return
    find_item_dialog(FindFileHandle(context), title='Find Project File',
                     matches='Matching Files')

class _ResourceViewHandle(TreeViewHandle):

    def __init__(self, core, toplevel):
        self.core = core
        self.toplevel = toplevel

    def entry_to_string(self, resource):
        return resource.name

    def get_children(self, resource):
        if resource.is_folder():
            result = [child for child in resource.get_children()
                      if not child.name.startswith('.') and
                      not child.name.endswith('.pyc')]
            result.sort(self._compare_files)
            return result
        else:
            return []

    def _compare_files(self, file1, file2):
        return cmp((not file1.is_folder(), file1.name),
                   (not file2.is_folder(), file2.name))

    def selected(self, resource):
        if not resource.is_folder():
            self.core.editor_manager.get_resource_editor(resource)
        else:
            return True

    def canceled(self):
        self.toplevel.destroy()

    def focus_went_out(self):
        pass


def _show_resource_view(core):
    if not rope.ui.actionhelpers.check_project(core):
        return
    toplevel = Tkinter.Toplevel()
    toplevel.title('Resources')
    tree_handle = _ResourceViewHandle(core, toplevel)
    tree_view = TreeView(toplevel, tree_handle, title='Resources',
                         height=25, width=45)
    for child in tree_handle.get_children(core.project.root):
        tree_view.add_entry(child)

class ChangeBufferHandle(SearchableListHandle):

    def __init__(self, toplevel, context):
        self.toplevel = toplevel
        self.context = context

    def selected(self, editor):
        self.toplevel.destroy()
        self.context.core.activate_editor(editor)

    def entry_to_string(self, editor):
        return editor.get_file().name

    def matches(self, editor, text):
        return editor.get_file().name.startswith(text)

    def canceled(self):
        self.toplevel.destroy()

def change_editor(context):
    if not rope.ui.actionhelpers.check_project(core):
        return
    toplevel = Tkinter.Toplevel()
    toplevel.title('Change Buffer')
    buffer_list = SearchableList(toplevel, ChangeBufferHandle(toplevel, context),
                                 verb='Change', name='Buffer', width=28, height=9)
    editor_list = context.core.editor_manager.get_editor_list()
    for editor in editor_list:
        buffer_list.add_entry(editor)


def project_tree(context):
    _show_resource_view(context.get_core())

def validate_project(context):
    context.project.validate(context.project.root)

def sync_project(context):
    context.project.sync()

def save_editor(context):
    context.get_core().save_active_editor()

def save_all(context):
    context.get_core().save_all_editors()

def close_editor(context):
    context.get_core()._close_active_editor_dialog()

def edit_project_config(context):
    if not rope.ui.actionhelpers.check_project(context.core):
        return
    resource = context.project.ropefolder
    if resource is not None:
        config = resource.get_child('config.py')
        editor_manager = context.get_core().get_editor_manager()
        editor_manager.get_resource_editor(config)

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

def exit_rope(context):
    context.get_core()._close_project_and_exit()

core = rope.ui.core.Core.get_core()
core.add_menu_cascade(MenuAddress(['File'], 'f'), ['all', 'none'])
actions = []

actions.append(SimpleAction('open_project', open_project, 'C-x C-p',
                            MenuAddress(['File', 'Open Project...'], 'o')))
actions.append(SimpleAction('close_project', close_project, 'C-x p k',
                            MenuAddress(['File', 'Close Project'], 'l')))

actions.append(SimpleAction('find_file', find_file, 'C-x C-f',
                            MenuAddress(['File', 'Find File...'], 'f', 1)))
core.add_menu_cascade(MenuAddress(['File', 'New'], 'n', 1), ['all', 'none'])
actions.append(SimpleAction('create_file', create_file, 'C-x n f',
                            MenuAddress(['File', 'New', 'New File...'], 'f')))
actions.append(SimpleAction('create_folder', create_folder, 'C-x n d',
                            MenuAddress(['File', 'New', 'New Directory...'], 'd')))
actions.append(SimpleAction('create_module', create_module, 'C-x n m',
                            MenuAddress(['File', 'New', 'New Module...'], 'm')))
actions.append(SimpleAction('create_package', create_package, 'C-x n p',
                            MenuAddress(['File', 'New', 'New Package...'], 'p')))

actions.append(SimpleAction('change_buffer', change_editor, 'C-x b',
                            MenuAddress(['File', 'Change Editor...'], 'c', 2)))
actions.append(SimpleAction('save_buffer', save_editor, 'C-x C-s',
                            MenuAddress(['File', 'Save Editor'], 's', 2)))
actions.append(SimpleAction('save_all_buffers', save_all, 'C-x s',
                            MenuAddress(['File', 'Save All'], 'a', 2)))
actions.append(SimpleAction('close_buffer', close_editor, 'C-x k',
                            MenuAddress(['File', 'Close Editor'], 'd', 2)))

actions.append(
    SimpleAction('undo_project',
                 ConfirmEditorsAreSaved(undo_project), 'C-x p u',
                 MenuAddress(['File', 'Undo Last Project Change'], 'u', 3),
                 ['all', 'none']))
actions.append(
    SimpleAction('redo_project',
                 ConfirmEditorsAreSaved(redo_project), 'C-x p r',
                 MenuAddress(['File', 'Redo Last Project Change'], 'r', 3),
                 ['all', 'none']))
actions.append(
    SimpleAction('project_history',
                 ConfirmEditorsAreSaved(show_history), 'C-x p h',
                 MenuAddress(['File', 'Project History'], 'h', 3),
                 ['all', 'none']))

actions.append(SimpleAction('project_tree', project_tree, 'C-x p t',
                            MenuAddress(['File', 'Project Tree'], 't', 4)))
actions.append(
    SimpleAction('edit_project_config', edit_project_config, 'C-x p c',
                 MenuAddress(['File', 'Edit Project config.py'], None, 4),
                 ['all', 'none']))
actions.append(SimpleAction('validate_project', validate_project, 'C-x p v',
                            MenuAddress(['File', 'Validate Project Files'], 'v', 4)))
actions.append(SimpleAction('sync_project', sync_project, 'C-x p s',
                            MenuAddress(['File', 'Sync Project To Disk'], None, 4)))

actions.append(SimpleAction('exit', exit_rope, 'C-x C-c',
                            MenuAddress(['File', 'Exit'], 'x', 5)))

for action in actions:
    core.register_action(action)
