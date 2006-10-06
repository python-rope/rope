import tkFileDialog
from Tkinter import *

from rope.exceptions import RopeException
from rope.project import Project
import rope.ui.editor
import rope.ui.statusbar
import rope.ui.editorpile
from rope.ui.menubar import MenuBarManager, MenuAddress
from rope.ui.extension import ActionContext


class Core(object):
    """The Core of the IDE"""

    def __init__(self):
        self.root = Tk()
        self.root.title('Rope')
        self.menus = {}
        self.menu_managers = {}
        self.all_contexts = ['python', 'rest', 'others', 'none']
        for context in self.all_contexts:
            self.menus[context] = Menu(self.root, relief=RAISED, borderwidth=1)
            self.menu_managers[context] = MenuBarManager(self.menus[context])
        self.root['menu'] = self.menus['none']

        self.main = Frame(self.root, height='13c', width='26c', relief=RIDGE, bd=2)
        self.editor_panel = Frame(self.main, borderwidth=0)
        self.editor_manager = rope.ui.editorpile.EditorPile(self.editor_panel, self)

        self.status_bar = Frame(self.main, borderwidth=1, relief=RIDGE)
        self.status_bar_manager = rope.ui.statusbar.StatusBarManager(self.status_bar)
        line_status = self.status_bar_manager.create_status('line')
        line_status.set_width(8)

        self.key_bindings = dict((context, []) for context in self.all_contexts)
        self.root.protocol('WM_DELETE_WINDOW', self._close_project_and_exit)
        self.project = None
    
    def _load_actions(self):
        """Load extension modules.
        
        The modules that are loaded here use `Core.register_action`
        to register their `Action` s.
        """
        import rope.ui.fileactions
        import rope.ui.editactions
        import rope.ui.codeassist
        import rope.ui.refactor
        for menu_manager in self.menu_managers.values():
            menu_manager.add_menu_cascade(MenuAddress(['Help'], 'p'))
            menu_manager.add_menu_command(MenuAddress(['Help', 'About'], 'a'),
                                             self._show_about_dialog)

    def _add_menu_cascade(self, menu_address, active_contexts):
        active_contexts = self._get_matching_contexts(active_contexts)
        for context in active_contexts:
            menu_manager = self.menu_managers[context]
            menu_manager.add_menu_cascade(menu_address)

    def _close_project_and_exit(self):
        self._close_project_dialog(exit_=True)

    def _show_about_dialog(self):
        toplevel = Toplevel()
        toplevel.title('About Rope')
        text = 'rope, a python refactoring IDE ...\n' + \
               'version ' + rope.VERSION + '\n\n' + \
               'Copyright (C) 2006 Ali Gholami Rudi\n\n' + \
               'This program is free software; you can redistribute it and/or modify it\n' + \
               'under the terms of GNU General Public License as published by the \n' + \
               'Free Software Foundation; either version 2 of the license, or (at your \n' + \
               'opinion) any later version.\n\n' + \
               'This program is distributed in the hope that it will be useful,\n' + \
               'but WITHOUT ANY WARRANTY; without even the implied warranty of\n' + \
               'MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n' + \
               'GNU General Public License for more details.\n'
        label = Label(toplevel, text=text, height=16, width=70, 
                      justify=LEFT, relief=GROOVE)
        def ok():
            toplevel.destroy()
        ok_button = Button(toplevel, text='OK', command=ok)
        label.grid()
        ok_button.grid()
        toplevel.focus_set()

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
        self._bind_key('<Any-KeyRelease>', show_current_line_number)
        self._bind_key('<Any-Button>', show_current_line_number)
        self._bind_key('<FocusIn>', show_current_line_number)
    
    def _get_matching_contexts(self, contexts):
        result = set(contexts)
        if 'all' in contexts:
            result.remove('all')
            for c in self.all_contexts:
                if c != 'none':
                    result.add(c)
        return result
    
    def _bind_key(self, key, function, active_contexts=['all']):
        if not key.startswith('<'):
            key = self._emacs_to_tk(key)
        active_contexts = self._get_matching_contexts(active_contexts)
        for key_binding in self.key_bindings.values():
            for context in active_contexts:
                key_binding = self.key_bindings[context]
                key_binding.append((key, function))
        if 'none' in active_contexts:
            self.root.bind(key, function)
    
    def _emacs_to_tk(self, key):
        result = []
        for token in key.split(' '):
            result.append('<%s>' % token.replace('M-', 'Alt-').replace('C-', 'Control-'))
        return ''.join(result)

    def _set_key_binding(self, graphical_editor):
        widget = graphical_editor.getWidget()
        for (key, function) in self.key_bindings[graphical_editor.get_editing_context()]:
            widget.bind(key, function)
    
    def _change_editor_dialog(self, event=None):
        toplevel = Toplevel()
        toplevel.title('Change Editor')
        find_dialog = Frame(toplevel)
        name_label = Label(find_dialog, text='Name')
        name = Entry(find_dialog)
        found_label = Label(find_dialog, text='Editors')
        found = Listbox(find_dialog, selectmode=SINGLE, width=28, height=9)
        scrollbar = Scrollbar(find_dialog, orient=VERTICAL)
        scrollbar['command'] = found.yview
        found.config(yscrollcommand=scrollbar.set)
        editor_list = self.editor_manager.get_editor_list()
        for editor in editor_list:
            found.insert(END, editor.get_file().get_name())
        if len(editor_list) >= 2:
            found.selection_set(0)
        def name_changed(event):
            if name.get() == '':
                return
            found.select_clear(0, END)
            found_index = -1
            for index, editor in enumerate(editor_list):
                if editor.get_file().get_name().startswith(name.get()):
                    found_index = index
                    break
            if found_index != -1:
                found.selection_set(found_index)
        def open_selected():
            selection = found.curselection()
            if selection:
                editor = editor_list[int(selection[0])]
                self.activate_editor(editor)
                toplevel.destroy()
        def cancel():
            toplevel.destroy()
        name.bind('<Any-KeyRelease>', name_changed)
        name.bind('<Return>', lambda event: open_selected())
        name.bind('<Escape>', lambda event: cancel())
        name.bind('<Control-g>', lambda event: cancel())
        found.bind('<Return>', lambda event: open_selected())
        found.bind('<Escape>', lambda event: cancel())
        found.bind('<Control-g>', lambda event: cancel())
        def select_prev(event):
            active = found.index(ACTIVE)
            if active - 1 >= 0:
                found.select_clear(0, END)
                found.selection_set(active - 1)
                found.activate(active - 1)
                found.see(active - 1)
        found.bind('<Control-p>', select_prev)
        def select_next(event):
            active = found.index(ACTIVE)
            if active + 1 < found.size():
                found.select_clear(0, END)
                found.selection_set(active + 1)
                found.activate(active + 1)
                found.see(active + 1)
        found.bind('<Control-n>', select_next)
        name_label.grid(row=0, column=0, columnspan=2)
        name.grid(row=1, column=0, columnspan=2)
        found_label.grid(row=2, column=0, columnspan=2)
        found.grid(row=3, column=0, columnspan=1)
        scrollbar.grid(row=3, column=1, columnspan=1, sticky=N+S)
        find_dialog.grid()
        name.focus_set()
        toplevel.grab_set()
        self.root.wait_window(toplevel)
        if event:
            return 'break'

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
        toplevel.title('Closing Unsaved Editor')
        label = Label(toplevel, text='Closing Unsaved Editor for <%s>' % 
                      active_editor.get_file().get_path())
        def save():
            active_editor.save()
            self.close_active_editor()
            toplevel.destroy()
        def dont_save():
            self.close_active_editor()
            toplevel.destroy()
        def cancel():
            toplevel.destroy()
        save_button = Button(toplevel, text='Save', command=save)
        dont_save_button = Button(toplevel, text="Don't Save", command=dont_save)
        cancel_button = Button(toplevel, text='Cancel', command=cancel)
        label.grid(row=0, column=0, columnspan=3)
        save_button.grid(row=1, column=0)
        dont_save_button.grid(row=1, column=1)
        cancel_button.grid(row=1, column=2)
        save_button.focus_set()

    def run(self):
        self._init_key_binding()
        self._load_actions()
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.main.rowconfigure(0, weight=1)
        self.main.columnconfigure(0, weight=1)
        self.editor_panel.pack(fill=BOTH, expand=1)
        self.status_bar.pack(fill=BOTH, side=BOTTOM)
        self.main.pack(fill=BOTH, expand=1)
        self.main.pack_propagate(0)
        self.root.mainloop()

    def open_file(self, fileName):
        if self.project is None:
            raise RopeException('No project is open')
        file_ = self.project.get_resource(fileName)
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
        if self.project is None:
            raise RopeException('No project is open')
        try:
            last_slash = file_name.rindex('/')
            parent = project.get_resource(file_name[: last_slash])
            file_name = file_name[last_slash + 1:]
        except ValueError:
            parent = self.project.get_root_folder()
        parent.create_file(file_name)
        return self.open_file(file_name)

    def open_project(self, projectRoot):
        if self.project:
            self.close_project()
        self.project = Project(projectRoot)

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
        label = Label(toplevel, text='Which modified editors to save')
        label.grid(row=0, columnspan=2)
        int_vars = []
        for i, editor in enumerate(modified_editors):
            int_var = IntVar()
            button = Checkbutton(toplevel, text=editor.get_file().get_path(),
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
        cancel_button.grid(row=len(int_vars) + 1, column=1)

    def close_project(self):
        while self.editor_manager.active_editor is not None:
            self.close_active_editor()
        self.project = None

    def create_folder(self, folder_name):
        try:
            last_slash = folder_name.rindex('/')
            parent = project.get_resource(folder_name[:last_slash])
            folder_name = folder_name[last_slash + 1:]
        except ValueError:
            parent = self.project.get_root_folder()
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
        callback = self._make_callback(action)
        menu = action.get_menu()
        key = action.get_default_key()
        if key:
            self._bind_key(key, callback, action.get_active_contexts())
        if menu:
            if key:
                menu.address[-1] = menu.address[-1].ljust(31) + key
            self._add_menu_command(menu, callback, action.get_active_contexts())
    
    def _add_menu_command(self, menu, callback, active_contexts):
        active_contexts = self._get_matching_contexts(active_contexts)
        for context in active_contexts:
            menu_manager = self.menu_managers[context]
            menu_manager.add_menu_command(menu, callback)
    
    def _make_callback(self, action):
        def callback(event=None):
            action.do(ActionContext(self))
            if event:
                return 'break'
        return callback
    
    def _editor_changed(self):
        active_editor = self.editor_manager.active_editor
        if active_editor:
            self.root['menu'] = self.menus[active_editor.get_editor()
                                           .get_editing_context()]
        else:
            self.root['menu'] = self.menus['none']

    @staticmethod
    def get_core():
        """Get the singleton instance of Core"""
        if not hasattr(Core, '_core'):
            Core._core = Core()
        return Core._core

