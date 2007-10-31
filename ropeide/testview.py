import os.path
import inspect
import threading
import socket

import Tkinter
from SimpleXMLRPCServer import SimpleXMLRPCServer

import rope.base.project
from ropeide.uihelpers import DescriptionList, ProgressBar
import ropeide.runtest


class GUITestResult(object):

    def __init__(self, gui_runner):
        self.gui_runner = gui_runner
        self.count = -1
        self.run_count = 0
        self.progress = gui_runner.progress
        self.progress.set_color('green')

    def start_test(self, test_name):
        self.progress.set_text(test_name)
        return True

    def add_success(self, test_name):
        return True

    def add_error(self, test_name, error):
        self.progress.set_color('red')
        return True

    def add_failure(self, test_name, error):
        self.progress.set_color('red')
        self.gui_runner.add_failure(test_name, error)
        return True

    def set_test_count(self, count):
        self.count = count
        return True

    def stop_test(self, test_name):
        self.run_count += 1
        self.progress.set_text('ran %d of %d' % (self.run_count, self.count))
        self.progress.set_done_percent(self.run_count * 100 // self.count)
        return True

    def _is_finished(self):
        return self.run_count == self.count


class GUITestRunner(object):

    def __init__(self, project, resource):
        self.project = project
        self.resource = resource
        self.running_thread = threading.Thread(target=self.run)
        self.running_thread.setDaemon(True)
        self.process = None
        self.is_stopped = False
        self.toplevel = Tkinter.Toplevel()
        self.toplevel.title('Running Unit Tests in <%s>' % resource.path)
        label = Tkinter.Label(self.toplevel,
                              text='Running Unit Tests in <%s>' % resource.path)
        label.grid(row=0)
        progress_frame = Tkinter.Frame(self.toplevel)
        self.progress = ProgressBar(progress_frame)
        progress_frame.grid(row=1)

        self.result = GUITestResult(self)
        self.failures = {}
        def description(test_name):
            return self.failures[test_name]
        self.description_list = DescriptionList(
            self.toplevel, 'Failures', description, indexwidth=30, height=10)
        self.ok_button = Tkinter.Button(self.toplevel, text='Stop',
                                        command=self._ok)
        self.ok_button.grid(row=4)
        self.toplevel.bind('<Control-g>', self._ok)
        self.toplevel.bind('<Escape>', self._ok)
        self.toplevel.protocol('WM_DELETE_WINDOW', self._ok)

    def add_failure(self, test_name, error):
        self.failures[test_name] = error
        self.description_list.add_entry(test_name)

    def _ok(self, event=None):
        if self.result._is_finished():
            self.toplevel.destroy()
        elif self.process is not None:
            self.is_stopped = True
            self.process.kill_process()
            self.toplevel.destroy()

    def start(self):
        self.running_thread.start()

    def run(self):
        rpc_port = None
        for i in range(8000, 8100):
            try:
                server = SimpleXMLRPCServer(('localhost', i), logRequests=False)
                rpc_port = i
                break
            except socket.error, e:
                pass
        try:
            server.register_instance(self.result)
            run_test_py = rope.base.project.get_no_project().get_resource(
                inspect.getsourcefile(ropeide.runtest))
            self.process = self.project.get_pycore().run_module(
                run_test_py, args=[str(rpc_port), self.resource.real_path])
            while not self.result._is_finished() and not self.is_stopped:
                server.handle_request()
        finally:
            server.server_close()
            self.ok_button['text'] = 'OK'


def run_unit_test(project, resource):
    runner = GUITestRunner(project, resource)
    runner.start()
