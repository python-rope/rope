import os.path
import inspect
import threading

import Tkinter
from SimpleXMLRPCServer import SimpleXMLRPCServer

import rope.ui.runtest


class GUITestResult(object):
    
    def __init__(self, label, canvas):
        self.count = -1
        self.run_count = 0
        self.label = label
        self.color = 'green'
        self.canvas = canvas
        canvas.create_rectangle(0, 0, canvas['width'], canvas['height'], fill='')
        canvas.create_rectangle(0, 0, 0, canvas['height'],
                                fill=self.color, outline=self.color)
        self.failures = {}
    
    def start_test(self, test_name):
        self.label['text'] = test_name
        return True
    
    def add_success(self, test_name):
        return True
    
    def add_error(self, test_name, error):
        self.failures[test_name] = error
        self.color = 'red'
        return True
    
    def add_failure(self, test_name, error):
        self.failures[test_name] = error
        self.color = 'red'
        return True
    
    def set_test_count(self, count):
        self.count = count
        return True
    
    def stop_test(self, test_name):
        self.run_count += 1
        self.label['text'] = ''
        self._draw_shape()
        return True
    
    def _draw_shape(self):
        width = int(self.canvas['width']) * self.run_count / self.count
        self.canvas.create_rectangle(0, 0, width, self.canvas['height'], fill=self.color)
    
    def is_finished(self):
        return self.run_count == self.count


class GUITestRunner(object):
    
    def __init__(self, project, resource):
        self.project = project
        self.resource = resource
        self.running_thread = threading.Thread(target=self.run)
        self.toplevel = Tkinter.Toplevel()
        self.toplevel.title('Running Unit Tests in <%s>' % resource.get_path())
        label = Tkinter.Label(self.toplevel,
                              text='Running Unit Tests in <%s>' % resource.get_path())
        label.grid(row=0)
        test_name = Tkinter.Label(self.toplevel, width=80)
        test_name.grid(row=1)
        run_shape = Tkinter.Canvas(self.toplevel, height=20)
        run_shape.grid(row=2)
        self.result = GUITestResult(test_name, run_shape)
        ok_button = Tkinter.Button(self.toplevel, text='OK', command=self._ok)
        ok_button.grid(row=3)
    
    def _ok(self):
        self.toplevel.destroy()
    
    def start(self):
        self.running_thread.start()
    
    def run(self):
        rpc_port = 8000
        server = SimpleXMLRPCServer(('localhost', rpc_port), logRequests=False)
        server.register_introspection_functions()
        server.register_instance(self.result)
        run_test_py = self.project.get_out_of_project_resource(
            inspect.getsourcefile(rope.ui.runtest))
        process = self.project.get_pycore().run_module(
            run_test_py, args=[str(rpc_port), self.resource._get_real_path()])
        while not self.result.is_finished():
            server.handle_request()


def run_unit_test(project, resource):
    runner = GUITestRunner(project, resource)
    runner.start()
