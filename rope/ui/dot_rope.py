# The default ~/.rope file for *rope*.
#
# You can edit this file to change some of rope's preferences.  If
# you like you can edit this file using rope itself.
# (``edit_dot_rope`` in execute command or ``Edit ~/.rope`` in
# ``Edit`` menu.)
#
# Note: Since this file is not inside a project you cannot perform
#   refactorings on it.
#
import rope.ui.core


core = rope.ui.core.get_core()

# Changing editor font
#core.set('font', ('Courier', 14))


# Hiding menu bar
#core.set('show_menu_bar', False)

# Hiding buffer list
#core.set('show_buffer_list', False)

# Hiding status bar
#core.set('show_status_bar', False)


# If you don't like emacs keybinding, change this to False
i_like_emacs = True
if not i_like_emacs:
    core.rebind_action('open_project', 'C-P')
    core.rebind_action('close_project', None)
    core.rebind_action('create_file', None)
    core.rebind_action('create_folder', None)
    core.rebind_action('create_module', None)
    core.rebind_action('create_package', None)
    core.rebind_action('project_tree', 'M-Q r')
    core.rebind_action('validate_project', 'F5')
    core.rebind_action('find_file', 'C-R')
    core.rebind_action('change_buffer', 'C-E')
    core.rebind_action('save_buffer', 'C-s')
    core.rebind_action('save_all_buffers', 'C-S')
    core.rebind_action('close_buffer', 'C-w')
    core.rebind_action('exit', 'C-W')

    core.rebind_action('set_mark', None)
    core.rebind_action('copy', 'C-c')
    core.rebind_action('cut', 'C-x')
    core.rebind_action('paste', 'C-v')
    core.rebind_action('goto_line', 'C-l')
    core.rebind_action('goto_last_edit_location', 'C-q')
    core.rebind_action('swap_mark_and_insert', None)
    core.rebind_action('undo', 'C-z')
    core.rebind_action('redo', 'C-y')
    core.rebind_action('undo_project', 'C-Z')
    core.rebind_action('redo_project', 'C-Y')
    core.rebind_action('project_history', None)
    core.rebind_action('search_forward', 'C-f')
    core.rebind_action('search_backward', 'C-F')
    core.rebind_action('edit_dot_rope', None)
    core.rebind_action('execute_command', None)

    core.rebind_action('code_assist', 'C-space')
    core.rebind_action('goto_definition', 'F3')
    core.rebind_action('show_doc', 'F2')
    core.rebind_action('quick_outline', 'C-o')
    core.rebind_action('find_occurrences', 'C-G')
    core.rebind_action('format_code', 'C-F')
    core.rebind_action('comment_line', 'C-3')
    core.rebind_action('comment_region', None)
    core.rebind_action('run_module', 'M-X p')
    core.rebind_action('run_unit_tests', 'M-X t')

    core.rebind_action('rename', 'M-R')
    core.rebind_action('move', 'M-V')
    core.rebind_action('extract_method', 'M-M')
    core.rebind_action('inline', 'M-I')
    core.rebind_action('extract_local_variable', 'M-L')
    core.rebind_action('rename_in_file', None)
    core.rebind_action('change_signature', 'M-C')
    core.rebind_action('introduce_factory', None)
    core.rebind_action('encapsulate_field', None)
    core.rebind_action('introduce_parameter', None)
    core.rebind_action('method_object', None)
    core.rebind_action('module_to_package', None)
    core.rebind_action('rename_current_module', None)
    core.rebind_action('move_current_module', None)
    core.rebind_action('organize_imports', 'C-O')
    core.rebind_action('expand_star_imports', None)
    core.rebind_action('relative_to_absolute', None)
    core.rebind_action('from_to_import', None)
    core.rebind_action('handle_long_imports', None)

    core.rebind_action('readme', None)
    core.rebind_action('features', None)
    core.rebind_action('overview', None)
    core.rebind_action('tutorial', None)
    core.rebind_action('contributing', None)
    core.rebind_action('library', None)
    core.rebind_action('about', None)
