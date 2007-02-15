import Tkinter


class ConfirmEditorsAreSaved(object):

    def __init__(self, callback, all=True):
        self.callback = callback
        self.all = all

    def __call__(self, context):
        fileeditor = context.fileeditor
        if self.all:
            editors = context.get_core().get_editor_manager().editors
        else:
            editors = [context.fileeditor]
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
        message = 'These editors should be saved before performing this action:\n* '
        label = Tkinter.Label(frame, text=message +
                              '\n* '.join([fileeditor.file.path
                                           for fileeditor in editors]))
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
