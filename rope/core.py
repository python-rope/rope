from threading import Thread
from Tkinter import *
import tkMessageBox
import tkFileDialog
import tkSimpleDialog

from rope.fileeditor import FileEditor
from rope.editor import GraphicalEditor
from rope.project import Project, FileFinder, PythonFileRunner

class Core(object):
    '''The main class for the IDE'''
    def __init__(self):
        self.root = Tk()
        self.root.title('Rope')
        self.menubar = Menu(self.root, relief=RAISED, borderwidth=1)
        self.root['menu'] = self.menubar
        self._create_menu()

        self.main = Frame(self.root, height='13c', width='26c', relief=RIDGE, bd=2)
        self.editor_list = Frame(self.main, borderwidth=0)
        self.editor_frame = Frame(self.main, borderwidth=0, relief=RIDGE)
        self.status_bar = Frame(self.main, borderwidth=1, relief=RIDGE)
        self.status_text = Label(self.status_bar, text='')
        self.status_text.pack(side=LEFT)

        self.editors = []
        self.active_file_path = StringVar('')
        self.active_editor = None

        self._set_key_binding(self.root)
        self.root.protocol('WM_DELETE_WINDOW', self.exit)
        self.runningThread = Thread(target=self.run)
        self.project = None
    
    def _create_menu(self):
        fileMenu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='File', menu=fileMenu, underline=1)
        fileMenu.add_command(label='Open Project ...', command=self._open_project, underline=6)
        fileMenu.add_command(label='Close Project', command=self.close_project, underline=3)
        fileMenu.add_separator()
        fileMenu.add_command(label='New File ...', command=self._create_new_file, underline=0)
        fileMenu.add_command(label='New Folder ...', command=self._create_new_folder, underline=0)
        fileMenu.add_separator()
        fileMenu.add_command(label='Open File ...', command=self._open_file, underline=0)
        fileMenu.add_command(label='Find File ...', command=self._find_file, underline=0)
        fileMenu.add_separator()
        fileMenu.add_command(label='Exit', command=self.exit, underline=1)

    def _set_key_binding(self, widget):
        widget.bind('<Control-x><Control-f>', self._open_file)
        widget.bind('<Control-x><Control-n>', self._create_new_file)
        def _save_active_editor(event):
            self.save_file()
            return 'break'
        widget.bind('<Control-x><Control-s>', _save_active_editor)
        widget.bind('<Control-x><Control-p>', self._open_project)
        def _exit(event):
            self.exit()
            return 'break'
        widget.bind('<Control-x><Control-c>', _exit)
        widget.bind('<Control-x><Control-d>', self._create_new_folder)
        widget.bind('<Control-R>', self._find_file)
        widget.bind('<Control-F11>', self._run_active_editor)
        def _close_active_editor(event):
            self.close_active_editor()
            return 'break'
        widget.bind('<Control-x><k>', _close_active_editor)


    def _find_file(self, event=None):
        if not self.project:
            tkMessageBox.showerror(parent=self.root, title='No Open Project',
                                   message='No project is open')
            return
        toplevel = Toplevel()
        toplevel.title('Find Project File')
        find_dialog = Frame(toplevel)
        name_label = Label(find_dialog, text='Name')
        name = Entry(find_dialog)
        found_label = Label(find_dialog, text='Matching Files')
        found = Listbox(find_dialog, selectmode=SINGLE, width=46, height=15)
        scrollbar = Scrollbar(find_dialog, orient=VERTICAL)
        scrollbar['command'] = found.yview
        found.config(yscrollcommand=scrollbar.set)
        file_finder = FileFinder(self.project)
        def name_changed(event):
            if name.get() == '':
                result = ()
            else:
                result = file_finder.find_files_starting_with(name.get())
            found.delete(0, END)
            for file in result:
                found.insert(END, file.get_path())
            if result:
                found.selection_set(0)
        def open_selected():
            selection = found.curselection()
            if selection:
                resource_name = found.get(selection[0])
                self.open_file(resource_name)
                toplevel.destroy()
        def cancel():
            toplevel.destroy()
        name.bind('<Any-KeyRelease>', name_changed)
        name.bind('<Return>', lambda event: open_selected())
        name.bind('<Escape>', lambda event: cancel())
        found.bind('<Return>', lambda event: open_selected())
        found.bind('<Escape>', lambda event: cancel())
        def select_prev(event):
            active = found.index(ACTIVE)
            if active - 1 >= 0:
                found.activate(active - 1)
                found.see(active - 1)
        found.bind('<Control-p>', select_prev)
        def select_next(event):
            active = found.index(ACTIVE)
            if active + 1 < found.size():
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

    def _run_active_editor(self, event=None):
        if not self.get_active_editor():
            tkMessageBox.showerror(parent=self.root, title='No Open Editor',
                                   message='No Editor is open.')
            return
        self.run_active_editor()
        return 'break'

    def _open_file(self, event=None):
        if not self.project:
            tkMessageBox.showerror(parent=self.root, title='No Open Project',
                                   message='No project is open')
            return 'break'
        def doOpen(fileName):
                self.open_file(fileName)
        self._show_open_dialog(doOpen, 'Open File Dialog')
        return 'break'

    def _create_new_file(self, event=None):
        if not self.project:
            tkMessageBox.showerror(parent=self.root, title='No Open Project',
                                   message='No project is open')
            return 'break'
        def doOpen(fileName):
            self.create_file(fileName)
        self._show_open_dialog(doOpen, 'New File Dialog')
        return 'break'

    def _create_new_folder(self, event=None):
        if not self.project:
            tkMessageBox.showerror(parent=self.root, title='No Open Project',
                                   message='No project is open')
            return 'break'
        def doOpen(fileName):
            self.create_folder(fileName)
        self._show_open_dialog(doOpen, 'New Folder Dialog')
        return 'break'

    def _open_project(self, event=None):
        def doOpen(projectRoot):
            self.open_project(projectRoot)
        directory = tkFileDialog.askdirectory(parent=self.root, title='Open Project')
        if directory:
            doOpen(directory)
        return 'break'

    def _show_open_dialog(self, openCommand, title='Open Dialog'):
        input = tkSimpleDialog.askstring(title, 'Address :', parent=self.root)
        if input:
            try:
                openCommand(input)
            except Exception, e:
                tkMessageBox.showerror(parent=self.root, title='Failed',
                                       message=str(e))

    def start(self):
        self.runningThread.start()

    def run(self):
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.main.rowconfigure(0, weight=1)
        self.main.columnconfigure(0, weight=1)
        self.editor_list.pack(fill=BOTH, side=TOP)
        self.editor_frame.pack(fill=BOTH, expand=1)
        self.status_bar.pack(fill=BOTH, side=BOTTOM)
        self.main.pack(fill=BOTH, expand=1)
        self.main.pack_propagate(0)
        self.root.mainloop()

    def open_file(self, fileName):
        if self.project is None:
            raise RopeException('No project is open')
        file = self.project.get_resource(fileName)
        for editor in self.editors:
            if editor.get_file() == file:
                editor._rope_title.invoke()
                return editor
        editor = FileEditor(file, GraphicalEditor(self.editor_frame))
        self.editors.append(editor)
        title = Radiobutton(self.editor_list, text=file.get_name(), variable=self.active_file_path,
                            value=file.get_path(), indicatoron=0, bd=2,
                            command=lambda: self.activate_editor(editor),
                            selectcolor='#99A', relief=GROOVE)
        editor._rope_title = title
        title.select()
        title.pack(fill=BOTH, side=LEFT)
        self.activate_editor(editor)
        self._set_key_binding(editor.get_editor().getWidget())
        return editor

    def activate_editor(self, editor):
        if self.get_active_editor():
            self.get_active_editor().get_editor().getWidget().forget()
        editor.get_editor().getWidget().pack(fill=BOTH, expand=1)
        editor.get_editor().getWidget().focus_set()
        editor._rope_title.select()
        self.active_editor = editor
        self.editors.remove(editor)
        self.editors.insert(0, editor)

    def get_active_editor(self):
        return self.active_editor

    def close_active_editor(self):
        if self.active_editor is None:
            return
        self.active_editor.get_editor().getWidget().forget()
        self.editors.remove(self.active_editor)
        self.active_editor._rope_title.forget()
        self.active_editor = None
        if self.editors:
            self.editors[0]._rope_title.invoke()

    def save_file(self):
        activeEditor = self.get_active_editor()
        if activeEditor:
            activeEditor.save()

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

    def close_project(self):
        while self.get_active_editor() is not None:
            self.close_active_editor()
        self.project = None

    def create_folder(self, folder_name):
        try:
            last_slash = folder_name.rindex('/')
            parent = project.get_resource(folder_name[: last_slash])
            folder_name = folder_name[last_slash + 1:]
        except ValueError:
            parent = self.project.get_root_folder()
        parent.create_folder(folder_name)

    def exit(self):
        self.root.quit()

    def get_open_project(self):
        return self.project

    def run_active_editor(self):
        activeEditor = self.get_active_editor()
        if activeEditor:
            runner = PythonFileRunner(activeEditor.get_file())
            return runner

    @staticmethod
    def get_core():
        '''Get the singleton instance of Core'''
        if not hasattr(Core, '_core'):
            Core._core = Core()
        return Core._core


class RopeException(Exception):
    '''Base exception for rope'''
    pass
