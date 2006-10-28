import os.path
import inspect
import threading
import socket

import Tkinter
from SimpleXMLRPCServer import SimpleXMLRPCServer

from rope.ui.uihelpers import DescriptionList
import rope.ui.runtest


class GUITestResult(object):
    
    def __init__(self, gui_runner):
        self.count = -1
        self.run_count = 0
        self.label = gui_runner.test_name
        self.color = 'green'
        self.gui_runner = gui_runner
        self.canvas = canvas = gui_runner.canvas
        canvas.create_rectangle(0, 0, canvas['width'], canvas['height'], fill='')
        canvas.create_rectangle(0, 0, 0, canvas['height'],
                                fill=self.color, outline=self.color)
    
    def start_test(self, test_name):
        self.label['text'] = test_name
        return True
    
    def add_success(self, test_name):
        return True
    
    def add_error(self, test_name, error):
        self.gui_runner.add_failure(test_name, error)
        self.gui_runner.description_list.add_entry(test_name)
        self.color = 'red'
        return True
    
    def add_failure(self, test_name, error):
        self.gui_runner.add_failure(test_name, error)
        self.gui_runner.description_list.add_entry(test_name)
        self.color = 'red'
        return True
    
    def set_test_count(self, count):
        self.count = count
        return True
    
    def stop_test(self, test_name):
        self.run_count += 1
        self.label['text'] = ('ran %d of %d' % (self.run_count, self.count))
        self._draw_shape()
        return True
    
    def _draw_shape(self):
        width = int(self.canvas['width']) * self.run_count / self.count
        self.canvas.create_rectangle(0, 0, width, self.canvas['height'], fill=self.color)
    
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
        self.toplevel.title('Running Unit Tests in <%s>' % resource.get_path())
        label = Tkinter.Label(self.toplevel,
                              text='Running Unit Tests in <%s>' % resource.get_path())
        label.grid(row=0)
        self.test_name = Tkinter.Label(self.toplevel, width=80)
        self.test_name.grid(row=1)
        self.canvas = Tkinter.Canvas(self.toplevel, height=20)
        self.canvas.grid(row=2)
        
        self.result = GUITestResult(self)
        self.failures = {}
        def description(test_name):
            return self.failures[test_name]
        self.description_list = DescriptionList(self.toplevel, 'Failures', description)
        self.ok_button = Tkinter.Button(self.toplevel, text='Stop',
                                        command=self._ok)
        self.ok_button.grid(row=4)
        self.toplevel.bind('<Control-g>', self._ok)
        self.toplevel.bind('<Escape>', self._ok)
    
    def add_failure(self, test_name, error):
        self.failures[test_name] = error
    
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
            run_test_py = self.project.get_out_of_project_resource(
                inspect.getsourcefile(rope.ui.runtest))
            self.process = self.project.get_pycore().run_module(
                run_test_py, args=[str(rpc_port), self.resource._get_real_path()])
            while not self.result._is_finished() and not self.is_stopped:
                server.handle_request()
        finally:
            server.server_close()
            self.ok_button['text'] = 'OK'


def run_unit_test(project, resource):
    runner = GUITestRunner(project, resource)
    runner.start()
