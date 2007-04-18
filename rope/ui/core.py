import os
import imp

import tkFileDialog
from Tkinter import *

import rope.ui.editor
import rope.ui.editorpile
import rope.ui.keybinder
import rope.ui.statusbar
from rope.base.exceptions import RopeError
from rope.base.project import Project, get_no_project
from rope.ui import editingcontexts, registers
from rope.ui.extension import ActionContext
from rope.ui.menubar import MenuBarManager
import rope.base.prefs


class Core(object):
    """The Core of the IDE"""

    def __init__(self):
        self.root = Tk()
        self.root.title('Rope')
        editingcontexts.init_contexts(self)
        for context in editingcontexts.contexts.values():
            context.menu = Menu(self.root, relief=RAISED, borderwidth=1)
            context.menu_manager = MenuBarManager(context.menu)

        self.main = Frame(self.root, height='13c', width='26c', relief=RIDGE, bd=2)
        self.editor_panel = Frame(self.main, borderwidth=0)
        self.status_bar = Frame(self.main, borderwidth=1, relief=RIDGE)

        self.status_bar_manager = rope.ui.statusbar.StatusBarManager(self.status_bar)
        buffer_status = self.status_bar_manager.create_status('buffer')
        buffer_status.set_width(40)
        self.editor_manager = rope.ui.editorpile.EditorPile(self.editor_panel, self,
                                                            buffer_status)

        line_status = self.status_bar_manager.create_status('line')
        line_status.set_width(8)

        for context in editingcontexts.contexts.values():
            context.key_binding = rope.ui.keybinder.KeyBinder(
                self.status_bar_manager)
        self.root.protocol('WM_DELETE_WINDOW', self._close_project_and_exit)
        self.project = get_no_project()
        self.rebound_keys = {}
        self.actions = []
        self.prefs = rope.base.prefs.Prefs()
        self.last_action = None
        self.registers = registers.Registers()

    def _load_actions(self):
        """Load extension modules.

        The modules that are loaded here use `Core.register_action`
        to register their `Action`\s.
        """
        import rope.ui.fileactions
        import rope.ui.editactions
        import rope.ui.sourceactions
        import rope.ui.refactor
        import rope.ui.helpactions

    def set(self, key, value):
        """Set a preference

        Set the preference for `key` to `value`.
        """
        self.prefs.set(key, value)

    def add(self, key, value):
        """Add an entry to a list preference

        Add `value` to the list of entries for the `key` preference.

        """
        self.prefs.add(key, value)

    def get_prefs(self):
        """Return a `rope.ui.pref.Prefs` object"""
        return self.prefs

    def add_menu_cascade(self, menu_address, active_contexts):
        active_contexts = self._get_matching_contexts(active_contexts)
        for context in active_contexts:
            context.menu_manager.add_menu_cascade(menu_address)

    def _close_project_and_exit(self):
        self._close_project_dialog(exit_=True)

    def _init_key_binding(self):
        def do_switch_active_editor(event):
            self.switch_active_editor()
            return 'break'
        self._bind_key('<Control-KeyRelease-F6>', do_switch_active_editor)
        line_status = self.status_bar_manager.get_status('line')
        def show_current_line_number(event):
            line_text = ' '
            if self.editor_manager.active_editor:
                editor = self.editor_manager.active_editor.get_editor()
                line_text = '%d: %d' % (editor.get_current_line_number(),
                                        editor.get_current_column_number())
            line_status.set_text(line_text)
        self.root.bind('<Any-KeyRelease>', show_current_line_number)
        self.root.bind('<Any-Button>', show_current_line_number)
        self.root.bind('<FocusIn>', show_current_line_number)
        for action in self.actions:
            callback = self._make_callback(action)
            key = self._get_action_key(action)
            if key:
                self._bind_key(key, callback, action.get_active_contexts())

    def _get_action_key(self, action):
        key = action.get_default_key()
        if action.get_name() in self.rebound_keys:
            key = self.rebound_keys[action.get_name()]
        return key

    def _init_menus(self):
        for action in self.actions:
            callback = self._make_callback(action)
            menu = action.get_menu()
            key = self._get_action_key(action)
            if menu:
                if key:
                    menu.address[-1] = menu.address[-1].ljust(32) + key
                self._add_menu_command(menu, callback, action.get_active_contexts())
        self._editor_changed()

    def _bind_none_context_keys(self):
        context = editingcontexts.none
        context.key_binding.bind(self.root)

    def _get_matching_contexts(self, contexts):
        result = set()
        for name in self._get_matching_context_names(contexts):
            if name in editingcontexts.contexts:
                result.add(editingcontexts.contexts[name])
        return result

    def _get_matching_context_names(self, contexts):
        contexts = set(contexts)
        result = set()
        if 'all' in contexts:
            contexts.remove('all')
            for name in editingcontexts.contexts.keys():
                if name != 'none':
                    result.add(name)
        for name in contexts:
                result.add(name)
        return result

    def _bind_key(self, key, function, active_contexts=['all']):
        active_contexts = self._get_matching_contexts(active_contexts)
        for context in active_contexts:
            context.key_binding.add_key(key, function)

    def _set_key_binding(self, graphical_editor):
        context = graphical_editor.get_editing_context()
        context.key_binding.bind(graphical_editor.getWidget())

    def _open_project_dialog(self, event=None):
        def doOpen(projectRoot):
            self.open_project(projectRoot)
        directory = tkFileDialog.askdirectory(parent=self.root, title='Open Project')
        if directory:
            doOpen(directory)
        return 'break'

    def _close_active_editor_dialog(self):
        active_editor = self.editor_manager.active_editor
        if not active_editor:
            return
        if not active_editor.get_editor().is_modified():
            return self.close_active_editor()
        toplevel = Toplevel()
        toplevel.title('Killing Unsaved Buffer')
        label = Label(toplevel, text='Killing Unsaved Buffer <%s>' %
                      active_editor.get_file().path)
        def save():
            active_editor.save()
            self.close_active_editor()
            toplevel.destroy()
        def dont_save():
            self.close_active_editor()
            toplevel.destroy()
        def cancel(event=None):
            toplevel.destroy()
        save_button = Button(toplevel, text='Save', command=save)
        dont_save_button = Button(toplevel, text="Don't Save", command=dont_save)
        cancel_button = Button(toplevel, text='Cancel', command=cancel)
        toplevel.bind('<Control-g>', cancel)
        toplevel.bind('<Escape>', cancel)
        label.grid(row=0, column=0, columnspan=3)
        save_button.grid(row=1, column=0)
        dont_save_button.grid(row=1, column=1)
        cancel_button.grid(row=1, column=2)
        save_button.focus_set()

    def run(self):
        self._load_actions()
        self._load_dot_rope()
        self._init_key_binding()
        self._bind_none_context_keys()
        self._init_menus()
        self.editor_manager.show(self.prefs.get('show_buffer_list', True))
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.main.rowconfigure(0, weight=1)
        self.main.columnconfigure(0, weight=1)
        self.editor_panel.pack(fill=BOTH, expand=1)
        if self.prefs.get('show_status_bar', True):
            self.status_bar.pack(fill=BOTH, side=BOTTOM)
        self.main.pack(fill=BOTH, expand=1)
        self.main.pack_propagate(0)
        self.root.mainloop()

    def _load_dot_rope(self):
        dot_rope = os.path.expanduser('~%s.rope' % os.path.sep)
        try:
            if not os.path.exists(dot_rope):
                write_dot_rope(dot_rope)
            run_globals = {}
            run_globals.update({'__name__': '__main__',
                                '__builtins__': __builtins__,
                                '__file__': dot_rope})
            execfile(dot_rope, run_globals)
            if 'starting_rope' in run_globals:
                run_globals['starting_rope'](self)
        except IOError, e:
            print 'Unable to load <~.rope> file: ' + e

    def open_file(self, file_name):
        if self.project is get_no_project():
            raise RopeError('No project is open')
        file_ = self.project.get_resource(file_name)
        return self.editor_manager.get_resource_editor(file_)

    def activate_editor(self, editor):
        self.editor_manager.activate_editor(editor)

    def close_active_editor(self):
        self.editor_manager.close_active_editor()

    def save_active_editor(self):
        active_editor = self.editor_manager.active_editor
        if active_editor:
            active_editor.save()

    def save_all_editors(self):
        for editor in self.editor_manager.editors:
            editor.save()

    def create_file(self, file_name):
        if self.project is  get_no_project():
            raise RopeError('No project is open')
        try:
            last_slash = file_name.rindex('/')
            parent = project.get_resource(file_name[: last_slash])
            file_name = file_name[last_slash + 1:]
        except ValueError:
            parent = self.project.root
        parent.create_file(file_name)
        return self.open_file(file_name)

    def open_project(self, project_root):
        if self.project:
            self.close_project()
        ropefolder = self.prefs.get('project_rope_folder', '.ropeproject')
        self.project = Project(project_root, ropefolder=ropefolder)

    def _close_project_dialog(self, exit_=False):
        modified_editors = [editor for editor in self.editor_manager.editors
                            if editor.get_editor().is_modified()]
        if not modified_editors:
            self.close_project()
            if exit_:
                self.exit()
            return
        toplevel = Toplevel()
        toplevel.title('Closing Project')
        label = Label(toplevel, text='Which modified editors to save?')
        label.grid(row=0, columnspan=2)
        int_vars = []
        for i, editor in enumerate(modified_editors):
            int_var = IntVar()
            button = Checkbutton(toplevel, text=editor.get_file().path,
                                 variable=int_var, onvalue=1, offvalue=0)
            int_vars.append(int_var)
            button.grid(row=i+1, columnspan=2)
        def done():
            for editor, int_var in zip(modified_editors, int_vars):
                if int_var.get() == 1:
                    editor.save()
            self.close_project()
            toplevel.destroy()
            if exit_:
                self.exit()
        def cancel():
            toplevel.destroy()
        done_button = Button(toplevel, text='Done', command=done)
        done_button.grid(row=len(int_vars) + 1, column=0)
        cancel_button = Button(toplevel, text='Cancel', command=cancel)
        toplevel.bind('<Escape>', lambda event: cancel())
        toplevel.bind('<Control-g>', lambda event: cancel())
        toplevel.bind('<Return>', lambda event: done())
        cancel_button.grid(row=len(int_vars) + 1, column=1)

    def close_project(self):
        while self.editor_manager.active_editor is not None:
            self.close_active_editor()
        self.project.close()
        self.registers.project_closed()
        self.project = get_no_project()

    def create_folder(self, folder_name):
        try:
            last_slash = folder_name.rindex('/')
            parent = project.get_resource(folder_name[:last_slash])
            folder_name = folder_name[last_slash + 1:]
        except ValueError:
            parent = self.project.root
        parent.create_folder(folder_name)

    def exit(self):
        self.root.quit()

    def get_open_project(self):
        return self.project

    def switch_active_editor(self):
        self.editor_manager.switch_active_editor()

    def get_active_editor(self):
        return self.editor_manager.active_editor

    def get_editor_manager(self):
        return self.editor_manager

    def register_action(self, action):
        """Register a `rope.ui.extension.Action`"""
        self.actions.append(action)

    def rebind_action(self, name, key):
        self.rebound_keys[name] = key

    def _add_menu_command(self, menu, callback, active_contexts):
        active_contexts = self._get_matching_contexts(active_contexts)
        for context in active_contexts:
            context.menu_manager.add_menu_command(menu, callback)

    def _make_callback(self, action):
        def callback(event=None):
            try:
                action.do(ActionContext(self))
                if action.get_name() != 'repeat_last_action':
                    self.last_action = action
            except RopeError, e:
                self._report_error(e, type(e).__name__)
            if event:
                return 'break'
        return callback

    def perform_action(self, action):
        self._make_callback(action)()

    def repeat_last_action(self):
        if self.last_action is not None:
            self.perform_action(self.last_action)

    def _report_error(self, message, title='RopeError Was Raised'):
        toplevel = Toplevel()
        toplevel.title(title)
        label = Label(toplevel, text=str(message))
        def ok(event=None):
            toplevel.destroy()
            return 'break'
        ok_button = Button(toplevel, text='OK', command=ok)
        label.grid(row=0)
        toplevel.bind('<Control-g>', lambda event: ok())
        toplevel.bind('<Escape>', lambda event: ok())
        toplevel.bind('<Return>', lambda event: ok())
        ok_button.grid(row=1)
        toplevel.grab_set()
        ok_button.focus_set()

    def _editor_changed(self):
        active_editor = self.editor_manager.active_editor
        if not self.prefs.get('show_menu_bar', True):
            self.root['menu'] = None
            return
        if active_editor:
            self.root['menu'] = active_editor.get_editor().get_editing_context().menu
        else:
            self.root['menu'] = editingcontexts.none.menu

    def get_available_actions(self):
        """Return the applicable actions in current context"""
        context = 'none'
        active_editor = self.editor_manager.active_editor
        if active_editor:
            context = active_editor.get_editor().get_editing_context().name
        for action in self.actions:
            action_contexts = self._get_matching_context_names(
                action.get_active_contexts())
            if context in action_contexts:
                yield action

    _core = None

    @staticmethod
    def get_core():
        """Get the singleton instance of Core"""
        result = Core._core
        if result is None:
            result = Core._core = Core()
        return result


def get_core():
    return Core.get_core()


def write_dot_rope(dot_rope):
    import rope.ui.dot_rope
    import inspect
    text = inspect.getsource(rope.ui.dot_rope)
    output = open(dot_rope, 'w')
    output.write(text)
    output.close()
