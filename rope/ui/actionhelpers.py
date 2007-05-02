import threading

import Tkinter

import rope.base.project
import rope.refactor.change_signature
import rope.ui.uihelpers
import rope.base.taskhandle


class StoppableTaskRunner(object):

    def __init__(self, task, title='Task'):
        """Task is a function that takes a `TaskHandle`"""
        self.task = task
        self.title = title

    def __call__(self):
        handle = rope.base.taskhandle.TaskHandle(self.title)
        toplevel = Tkinter.Toplevel()
        toplevel.title('Performing Task ' + self.title)
        frame = Tkinter.Frame(toplevel)
        progress = rope.ui.uihelpers.ProgressBar(frame)
        def update_progress():
            job_sets = handle.get_job_sets()
            if job_sets:
                job_set = job_sets[-1]
                text = ''
                if job_set.get_name() is not None:
                    text += job_set.get_name()
                if job_set.get_active_job_name() is not None:
                    text += ' : ' + job_set.get_active_job_name()
                progress.set_text(text)
                percent = job_set.get_percent_done()
                if percent is not None:
                    progress.set_done_percent(percent)
        handle.add_observer(update_progress)
        class Calculate(object):

            def __init__(self, task):
                self.task = task
                self.result = None
                self.exception = None

            def __call__(self):
                try:
                    try:
                        self.result = self.task(handle)
                    except Exception, e:
                        self.exception = e
                finally:
                    toplevel.quit()
        
        calculate = Calculate(self.task)
        def stop(event=None):
            handle.stop()
        frame.grid(row=0)
        stop_button = Tkinter.Button(toplevel, text='Stop', command=stop)
        toplevel.bind('<Control-g>', stop)
        toplevel.bind('<Escape>', stop)
        stop_button.grid(row=1)

        toplevel.grab_set()
        stop_button.focus_set()
        thread = threading.Thread(target=calculate)
        thread.start()
        toplevel.mainloop()
        toplevel.destroy()
        if calculate.exception is not None:
            description = type(calculate.exception).__name__ + ': ' + \
                          str(calculate.exception)
            raise rope.base.exceptions.InterruptedTaskError(
                'Task <%s> was interrupted.\nReason: <%s>' %
                (self.title, description))
        return calculate.result

def simple_stoppable(description):
    def decorator(function):
        def caller():
            def do_call(handle):
                return function(handle)
            return StoppableTaskRunner(do_call, description)()
        return caller
    return decorator


def check_project(core):
    if core.project is rope.base.project.get_no_project():
        core._report_error(message='Open a project first!',
                           title='No Open Project')
        return False
    return True


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
        ok_button = Tkinter.Button(frame, text='Save All',
                                   command=ok, width=10)
        cancel_button = Tkinter.Button(frame, text='Cancel',
                                       command=cancel, width=10)
        ok_button.grid(row=1, column=0)
        toplevel.bind('<Return>', lambda event: ok())
        toplevel.bind('<Escape>', lambda event: cancel())
        toplevel.bind('<Control-g>', lambda event: cancel())
        cancel_button.grid(row=1, column=1)
        frame.grid()
        ok_button.focus_set()
