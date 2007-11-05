# The default ~/.ropeide file for *ropeide*.
#
# You can edit this file to change some of rope's preferences.  If
# you like you can edit this file using rope itself.
# (``edit_dot_ropeide`` in execute command or ``Edit ~/.ropeide``
# in ``Edit`` menu.)
#
# Note: Since this file is not inside a project you cannot perform
#   refactorings on it.
#


def starting_rope(core):
    """Change rope preferences.

    This function is called when rope starts.

    """

    # Changing editor font
    #core.set('font', ('Courier', 16))
    #core.set('font', ('Bitstream Vera Sans Mono', 16))

    # Changing other fonts
    core.set('menu_font', ('Courier', 12, 'bold'))
    core.set('statusbar_font', ('Courier', 12))
    core.set('editorlist_font', ('Courier', 12))

    # Hiding menu bar
    #core.set('show_menu_bar', False)

    # Hiding buffer list
    #core.set('show_buffer_list', False)

    # Hiding status bar
    #core.set('show_status_bar', False)


    # If you don't like emacs keybindings, change this to False
    i_like_emacs = True
    if not i_like_emacs:
        _change_to_nonemacs_keybinding(core)

    # The key used for prefixing actions
    #core.set('action_prefix', 'C-u')


    # Add your python templates
    core.add('templates', ('say_hello', "print 'Hello, my name is ${name}'\n"))
    core.add('templates', ('set_field', "self.${field}${cursor} = ${field}\n"))


    # The folder relative to project root that holds config files and
    # information about the project.  If this folder does not exist it is
    # created.  Specifying `None` means do not make and use a rope folder.
    #core.set('project_rope_folder', '.ropeproject')

    # You can register your own actions
    _register_my_actions(core)


def _register_my_actions(core):
    # Adding your own `Action`\s:
    # If you're interested in adding your own actions to rope you can do so
    # like this.
    # Plugins can use this interface for registering their actions.  For
    # more information see `rope.ui.extension` module.
    from ropeide.extension import SimpleAction

    def say_hello(context):
        print('Hello Action!')

    hello_action = SimpleAction('hello_action', say_hello, 'C-h h')
    core.register_action(hello_action)

    # A more advanced example that uses `Tkinter`
    def rope_info(context):
        import gc
        import Tkinter
        import rope.base.pyobjects

        info = 'Rope Running Info\n=================\n\n'
        info += 'Rope version %s\n\n' % rope.VERSION
        info += str(context.project.history) + '\n'
        module_count = 0
        for obj in gc.get_objects():
            # Checking the real type; not isinstance
            if type(obj) in (rope.base.pyobjects.PyModule,
                             rope.base.pyobjects.PyPackage):
                module_count += 1
        info += 'Memory contains %s PyModules\n' % module_count
        info += str(context.project.pycore) + '\n'

        toplevel = Tkinter.Toplevel()
        toplevel.title('Rope Running Info')
        label = Tkinter.Label(toplevel, text=info, height=10, width=50,
                              justify=Tkinter.LEFT, relief=Tkinter.GROOVE)
        label.grid(row=0)
        def ok():
            toplevel.destroy()
        ok_button = Tkinter.Button(toplevel, text='OK', command=ok, width=20)
        ok_button.grid(row=1)
        ok_button.focus_set()
        toplevel.bind('<Escape>', lambda event: ok())
        toplevel.bind('<Control-g>', lambda event: ok())
        toplevel.bind('<Return>', lambda event: ok())

    info_action = SimpleAction('rope_info', rope_info, 'C-h i')
    core.register_action(info_action)

    # Alternatively you can put your actions in an extension module
    # and register the module using `Core.add_extension()`.  When
    # rope starts it loads all extension modules.  You should register
    # your actions when the module is loading
    #core.add_extension('my.extension.module')


def _change_to_nonemacs_keybinding(core):
    # file actions
    core.rebind_action('open_project', 'C-P')
    core.rebind_action('close_project', None)
    core.rebind_action('create_file', None)
    core.rebind_action('create_folder', None)
    core.rebind_action('create_module', None)
    core.rebind_action('create_package', None)
    core.rebind_action('project_tree', 'M-Q r')
    core.rebind_action('validate_project', 'F5')
    core.rebind_action('edit_project_config', None)
    core.rebind_action('sync_project', None)
    core.rebind_action('find_file', 'C-R')
    core.rebind_action('find_type', 'C-T')
    core.rebind_action('change_buffer', 'C-E')
    core.rebind_action('save_buffer', 'C-s')
    core.rebind_action('save_all_buffers', 'C-S')
    core.rebind_action('close_buffer', 'C-w')
    core.rebind_action('exit', 'C-W')

    core.rebind_action('undo_project', 'C-Z')
    core.rebind_action('redo_project', 'C-Y')
    core.rebind_action('project_history', None)
    core.rebind_action('current_file_history', None)

    # edit actions
    core.rebind_action('set_mark', None)
    core.rebind_action('copy', 'C-c')
    core.rebind_action('cut', 'C-x')
    core.rebind_action('paste', 'C-v')
    core.rebind_action('yank', None)
    core.rebind_action('goto_line', 'C-l')
    core.rebind_action('goto_last_edit_location', 'C-q')
    core.rebind_action('swap_mark_and_insert', None)
    core.rebind_action('undo', 'C-z')
    core.rebind_action('redo', 'C-y')
    core.rebind_action('repeat_last_action', None)
    core.rebind_action('search_forward', 'C-f')
    core.rebind_action('search_backward', 'C-F')
    core.rebind_action('edit_dot_ropeide', None)
    core.rebind_action('execute_command', None)

    # source actions
    core.rebind_action('correct_line_indentation', 'C-i')
    core.rebind_action('show_codetags', None)
    core.rebind_action('show_errors', None)
    core.rebind_action('show_warnings', None)
    core.rebind_action('show_annotations', None)
    core.rebind_action('format_code', 'C-F')
    core.rebind_action('comment_line', 'C-3')
    core.rebind_action('comment_region', None)
    core.rebind_action('generate_variable', 'M-G v')
    core.rebind_action('generate_function', 'M-G f')
    core.rebind_action('generate_class', 'M-G c')
    core.rebind_action('generate_module', 'M-G m')
    core.rebind_action('generate_package', 'M-G g')
    core.rebind_action('memorize_location', 'M-M m')
    core.rebind_action('remember_location', 'M-M b')
    core.rebind_action('memorize_string', 'M-M s')
    core.rebind_action('remember_string', 'M-M i')
    core.rebind_action('spellcheck_word', None)
    core.rebind_action('spellcheck_buffer', None)
    core.rebind_action('spellcheck_region', None)
    core.rebind_action('sort_by_alpha', None)
    core.rebind_action('sort_by_kind', None)
    core.rebind_action('sort_by_pydoc', None)
    core.rebind_action('sort_by_underlined', None)
    core.rebind_action('sort_by_special', None)

    core.rebind_action('code_assist', 'C-space')
    core.rebind_action('goto_definition', 'F3')
    core.rebind_action('show_doc', 'F2')
    core.rebind_action('quick_outline', 'C-o')
    core.rebind_action('find_occurrences', 'C-G')
    core.rebind_action('run_module', 'M-X p')
    core.rebind_action('run_unit_tests', 'M-X t')
    core.rebind_action('run_soi', 'M-X s')

    # refactorings
    core.rebind_action('rename', 'M-R')
    core.rebind_action('move', 'M-V')
    core.rebind_action('extract_method', 'M-M')
    core.rebind_action('inline', 'M-I')
    core.rebind_action('extract_local_variable', 'M-L')
    core.rebind_action('rename_in_file', None)
    core.rebind_action('change_signature', 'M-C')
    core.rebind_action('introduce_factory', None)
    core.rebind_action('encapsulate_field', None)
    core.rebind_action('change_occurrences', None)
    core.rebind_action('local_to_field', None)
    core.rebind_action('inline_argument_default', None)
    core.rebind_action('introduce_parameter', None)
    core.rebind_action('method_object', None)
    core.rebind_action('module_to_package', None)
    core.rebind_action('rename_current_module', None)
    core.rebind_action('move_current_module', None)
    core.rebind_action('restructure', None)
    # import actions
    core.rebind_action('organize_imports', 'C-O')
    core.rebind_action('expand_star_imports', None)
    core.rebind_action('relatives_to_absolutes', None)
    core.rebind_action('froms_to_imports', None)
    core.rebind_action('handle_long_imports', None)

    # help actions
    core.rebind_action('readme', None)
    core.rebind_action('features', None)
    core.rebind_action('overview', None)
    core.rebind_action('tutorial', None)
    core.rebind_action('contributing', None)
    core.rebind_action('library', None)
    core.rebind_action('about', None)

    # other actions
    core.rebind_action('prev_word', 'C-Left')
    core.rebind_action('next_word', 'C-Right')
    core.rebind_action('lower_next_word', None)
    core.rebind_action('upper_next_word', None)
    core.rebind_action('capitalize_next_word', None)
    core.rebind_action('goto_center_line', None)
    core.rebind_action('prev_statement', None)
    core.rebind_action('next_statement', None)
    core.rebind_action('prev_scope', 'C-Up')
    core.rebind_action('next_scope', 'C-Down')
