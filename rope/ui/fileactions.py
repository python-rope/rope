import rope.ui.core
from rope.ui.menubar import MenuAddress
from rope.ui.extension import SimpleAction

def open_project(context):
    context.get_core()._open_project_dialog()

def close_project(context):
    context.get_core()._close_project_dialog()

def create_file(context):
    context.get_core()._create_new_file_dialog()

def create_folder(context):
    context.get_core()._create_new_folder_dialog()

def create_module(context):
    context.get_core()._create_new_module_dialog()

def create_package(context):
    context.get_core()._create_new_package_dialog()

def find_file(context):
    context.get_core()._find_file_dialog()

def project_tree(context):
    context.get_core()._show_resource_tree()

def open_file(context):
    context.get_core()._open_file_dialog()

def change_editor(context):
    context.get_core()._change_editor_dialog()

def save_editor(context):
    context.get_core().save_active_editor()

def save_all(context):
    context.get_core().save_all_editors()

def close_editor(context):
    context.get_core().close_active_editor()

def exit_rope(context):
    context.get_core()._close_project_and_exit()

core = rope.ui.core.Core.get_core()
actions = []

actions.append(SimpleAction('Open Project', open_project, '<Control-x><Control-p>',
                            MenuAddress(['File', 'Open Project...'], 'o')))
actions.append(SimpleAction('Close Project', close_project, None,
                            MenuAddress(['File', 'Close Project'], 'l')))

actions.append(SimpleAction('Create File', create_file, None,
                            MenuAddress(['File', 'New File...'], 'n', 1)))
actions.append(SimpleAction('Create Folder', create_folder, None,
                            MenuAddress(['File', 'New Folder...'], 'e', 1)))
actions.append(SimpleAction('Create Module', create_module, None,
                            MenuAddress(['File', 'New Module...'], 'm', 1)))
actions.append(SimpleAction('Create Package', create_package, None,
                            MenuAddress(['File', 'New Package...'], 'p', 1)))

actions.append(SimpleAction('Find File', find_file, '<Control-x><Control-f>',
                            MenuAddress(['File', 'Find File...'], 'f', 2)))
actions.append(SimpleAction('Project Tree', project_tree, '<Alt-Q><r>',
                            MenuAddress(['File', 'Project Tree'], 't', 2)))
actions.append(SimpleAction('Open File', open_file, None,
                            MenuAddress(['File', 'Open File...'], None, 2)))

actions.append(SimpleAction('Change Editor', change_editor, '<Control-x><b>',
                            MenuAddress(['File', 'Change Editor...'], 'c', 3)))
actions.append(SimpleAction('Save Editor', save_editor, '<Control-x><Control-s>',
                            MenuAddress(['File', 'Save Editor'], 's', 3)))
actions.append(SimpleAction('Save All Editors', save_all, '<Control-x><s>',
                            MenuAddress(['File', 'Save All'], 'a', 3)))
actions.append(SimpleAction('Close Editor', close_editor, '<Control-x><k>',
                            MenuAddress(['File', 'Close Editor'], 'c', 3)))

actions.append(SimpleAction('Exit', exit_rope, '<Control-x><Control-c>',
                            MenuAddress(['File', 'Exit'], 'x', 4)))

for action in actions:
    core.register_action(action)
