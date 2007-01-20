from Tkinter import *

import rope.ui.fileeditor


class EditorPile(object):

    def __init__(self, editor_panel, core):
        self.core = core
        self.editor_list = Frame(editor_panel, borderwidth=0)
        self.editor_frame = Frame(editor_panel, borderwidth=0, relief=RIDGE)
        self.editor_list.pack(fill=BOTH, side=TOP)
        self.editor_frame.pack(fill=BOTH, expand=1)
        self.editor_frame.pack_propagate(0)
        self.editors = []
        self.buttons = {}
        self.active_file_path = StringVar('')
        self.active_editor = None
        self.last_edited_location = None

    def _editor_was_modified(self, editor):
        if editor not in self.buttons:
            return
        new_title = editor.get_file().get_name()
        if editor.get_editor().is_modified():
            new_title = '*' + new_title
        self.buttons[editor]['text'] = new_title

    def _editor_was_changed(self, resource, offset):
        self.last_edited_location = (resource, offset)

    def activate_editor(self, editor):
        if self.active_editor:
            self.active_editor.get_editor().getWidget().forget()
        editor.get_editor().getWidget().pack(fill=BOTH, expand=1)
        editor.get_editor().getWidget().focus_set()
        self.buttons[editor].select()
        self.active_editor = editor
        self.editors.remove(editor)
        self.editors.insert(0, editor)
        self.core._editor_changed()

    def get_resource_editor(self, file_, readonly=False):
        for editor in self.editors:
            if editor.get_file() == file_:
                self.buttons[editor].invoke()
                return editor
        editor = rope.ui.fileeditor.FileEditor(
            self.core.get_open_project(), file_,
            rope.ui.editor.GraphicalEditorFactory(self.editor_frame), readonly)
        editor.get_editor().set_status_bar_manager(self.core.status_bar_manager)
        editor.add_change_observer(self._editor_was_changed)
        self.editors.append(editor)
        title = Radiobutton(self.editor_list, text=file_.get_name(),
                            variable=self.active_file_path,
                            value=file_.path, indicatoron=0, bd=2,
                            command=lambda: self.activate_editor(editor),
                            selectcolor='#99A', relief=GROOVE)
        self.buttons[editor] = title
        title.select()
        title.pack(fill=BOTH, side=LEFT)
        self.activate_editor(editor)
        self.core._set_key_binding(editor.get_editor())
        editor.add_modification_observer(self._editor_was_modified)
        return editor

    def switch_active_editor(self):
        if len(self.editors) >= 2:
            self.activate_editor(self.editors[1])

    def close_active_editor(self):
        if self.active_editor is None:
            return
        widget = self.active_editor.get_editor().getWidget()
        widget.forget()
        widget.destroy()
        self.editors.remove(self.active_editor)
        button = self.buttons[self.active_editor]
        button.forget()
        button.destroy()
        self.active_editor.close()
        del self.buttons[self.active_editor]
        self.active_editor = None
        if self.editors:
            self.buttons[self.editors[0]].invoke()
        else:
            self.core._editor_changed()

    def get_editor_list(self):
        if not self.editors:
            return []
        result = self.editors[1:]
        result.append(self.editors[0])
        return result

    def goto_last_edit_location(self):
        if self.last_edited_location is not None:
            self.get_resource_editor(self.last_edited_location[0])
            self.active_editor.get_editor().set_insert(self.last_edited_location[1])
