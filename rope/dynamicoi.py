import os
import subprocess
import sys
import socket
import cPickle as pickle
import threading


class DynamicObjectInference(object):
    
    def __init__(self, pycore):
        self.pycore = pycore
        self.objectdb = {}
    
    def run_module(self, resource, stdin=None, stdout=None):
        return PythonFileRunner(self.pycore, resource, stdin, stdout, self._data_received)
    
    def _data_received(self, data):
        self.objectdb[data[0]] = (data[1], data[2])
    
    def infer_returned_object(self, pyobject):
        resource = pyobject.get_module().get_resource()
        if resource is None:
            return
        name = (True, os.path.abspath(resource._get_real_path()),
                pyobject.get_scope().get_start())
        if name not in self.objectdb:
            return
        result = self.objectdb[name][1]
        return _persisted_form_to_pyobject(self.pycore.project, result[1], result[2])


def _persisted_form_to_pyobject(project, path, lineno):
    root = os.path.abspath(project.get_root_address())
    if path.startswith(root):
        relative_path = path[len(root):]
        if relative_path.startswith('/'):
            relative_path = relative_path[1:]
        resource = project.get_resource(relative_path)
    else:
        resource = project.get_out_of_project_resource(path)
    scope = project.get_pycore().resource_to_pyobject(resource).get_scope()
    inner_scope = scope.get_inner_scope_for_line(lineno)
    return inner_scope.pyobject    


class PythonFileRunner(object):
    """A class for running python project files"""

    def __init__(self, pycore, file_, stdin=None, stdout=None, analyze_data=None):
        self.pycore = pycore
        self.file = file_
        self.analyze_data = analyze_data
        file_path = self.file._get_real_path()
        env = {}
        env.update(os.environ)
        source_folders = []
        for folder in file_.get_project().get_pycore().get_source_folders():
            source_folders.append(os.path.abspath(folder._get_real_path()))
        env['PYTHONPATH'] = env.get('PYTHONPATH', '') + os.pathsep + \
                            os.pathsep.join(source_folders)
        runmod_path = self.pycore.find_module('rope.runmod')._get_real_path()
        self.data_port = -1
        self._init_data_receiving()
        args = (sys.executable, runmod_path, str(self.data_port),
                os.path.abspath(self.file._get_real_path()))
        self.process = subprocess.Popen(executable=sys.executable, args=args,
                                        cwd=os.path.split(file_path)[0], stdin=stdin,
                                        stdout=stdout, stderr=stdout, env=env)
    
    def _init_data_receiving(self):
        if self.analyze_data is None:
            return
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_port = 3037
        while self.data_port < 4000:
            try:
                self.server_socket.bind(('', self.data_port))
                break
            except socket.error, e:
                self.data_port += 1
        self.server_socket.listen(1)
        self.receiving_thread = threading.Thread(target=self._receive_information)
        self.receiving_thread.setDaemon(True)
        self.receiving_thread.start()
    
    def _receive_information(self):
        conn, addr = self.server_socket.accept()
        self.server_socket.close()
        my_file = conn.makefile('r')
        while True:
            try:
                self.analyze_data(pickle.load(my_file))
            except EOFError:
                break

        my_file.close()
        conn.close()

    def wait_process(self):
        """Wait for the process to finish"""
        self.process.wait()
        if self.analyze_data:
            self.receiving_thread.join()

    def kill_process(self):
        """Stop the process. This does *not* work on windows."""
        os.kill(self.process.pid, 9)
