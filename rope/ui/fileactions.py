import Tkinter
import tkMessageBox
import re

import rope.base.project
import rope.ui.core
from rope.ui.extension import SimpleAction
from rope.ui.menubar import MenuAddress
from rope.ui.uihelpers import TreeViewHandle, TreeView, find_item_dialog


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

def _check_if_project_is_open(core):
    if core.project is rope.base.project.get_no_project():
        tkMessageBox.showerror(parent=core.root, title='No Open Project',
                               message='No project is open')
        return False
    return True

def _create_resource_dialog(core, creation_callback,
                            resource_name='File', parent_name='Parent Folder'):
    """Ask user about the parent folder and the name of the resource to be created

    creation_callback is a function accepting the parent and the name

    """
    if not _check_if_project_is_open(core):
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
        tree_view.list.focus_set()
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
    if not _check_if_project_is_open(context.core):
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
    if not _check_if_project_is_open(core):
        return
    toplevel = Tkinter.Toplevel()
    toplevel.title('Resources')
    tree_handle = _ResourceViewHandle(core, toplevel)
    tree_view = TreeView(toplevel, tree_handle, title='Resources',
                         height=25, width=45)
    for child in tree_handle.get_children(core.project.root):
        tree_view.add_entry(child)

def project_tree(context):
    _show_resource_view(context.get_core())

def validate_project(context):
    context.project.validate(context.project.root)

def change_editor(context):
    context.get_core()._change_editor_dialog()

def save_editor(context):
    context.get_core().save_active_editor()

def save_all(context):
    context.get_core().save_all_editors()

def close_editor(context):
    context.get_core()._close_active_editor_dialog()

def exit_rope(context):
    context.get_core()._close_project_and_exit()

core = rope.ui.core.Core.get_core()
core._add_menu_cascade(MenuAddress(['File'], 'i'), ['all', 'none'])
actions = []

actions.append(SimpleAction('open_project', open_project, 'C-x C-p',
                            MenuAddress(['File', 'Open Project...'], 'o')))
actions.append(SimpleAction('close_project', close_project, 'C-x p k',
                            MenuAddress(['File', 'Close Project'], 'l')))

actions.append(SimpleAction('create_file', create_file, 'C-x n f',
                            MenuAddress(['File', 'New File...'], 'n', 1)))
actions.append(SimpleAction('create_folder', create_folder, 'C-x n d',
                            MenuAddress(['File', 'New Folder...'], 'e', 1)))
actions.append(SimpleAction('create_module', create_module, 'C-x n m',
                            MenuAddress(['File', 'New Module...'], 'm', 1)))
actions.append(SimpleAction('create_package', create_package, 'C-x n p',
                            MenuAddress(['File', 'New Package...'], 'p', 1)))

actions.append(SimpleAction('find_file', find_file, 'C-x C-f',
                            MenuAddress(['File', 'Find File...'], 'f', 2)))
actions.append(SimpleAction('project_tree', project_tree, 'C-x p t',
                            MenuAddress(['File', 'Project Tree'], 't', 2)))
actions.append(SimpleAction('validate_project', validate_project, 'C-x p v',
                            MenuAddress(['File', 'Validate Project Files'], 'v', 2)))

actions.append(SimpleAction('change_buffer', change_editor, 'C-x b',
                            MenuAddress(['File', 'Change Editor...'], 'c', 3)))
actions.append(SimpleAction('save_buffer', save_editor, 'C-x C-s',
                            MenuAddress(['File', 'Save Editor'], 's', 3)))
actions.append(SimpleAction('save_all_buffers', save_all, 'C-x s',
                            MenuAddress(['File', 'Save All'], 'a', 3)))
actions.append(SimpleAction('close_buffer', close_editor, 'C-x k',
                            MenuAddress(['File', 'Close Editor'], 'd', 3)))

actions.append(SimpleAction('exit', exit_rope, 'C-x C-c',
                            MenuAddress(['File', 'Exit'], 'x', 4)))

for action in actions:
    core.register_action(action)
