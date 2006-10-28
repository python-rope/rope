import os
import re
import subprocess
import sys
import socket
import cPickle as pickle
import marshal
import tempfile
import threading

import rope.base.pyobjects


class DynamicObjectInference(object):
    
    def __init__(self, pycore):
        self.pycore = pycore
        self.files = {}
    
    def run_module(self, resource, args=None, stdin=None, stdout=None):
        """Return a PythonFileRunner for controlling the process"""
        return PythonFileRunner(self.pycore, resource, args, stdin,
                                stdout, self._data_received)
    
    def infer_returned_object(self, pyobject):
        organizer = self._find_organizer(pyobject)
        if organizer:
            return organizer.returned.to_pyobject(self.pycore.project)

    def infer_parameter_objects(self, pyobject):
        organizer = self._find_organizer(pyobject)
        if organizer:
            pyobjects = [parameter.to_pyobject(self.pycore.project)
                         for parameter in organizer.args]
            return pyobjects
    
    def _find_organizer(self, pyobject):
        resource = pyobject.get_module().get_resource()
        if resource is None:
            return
        path = os.path.abspath(resource._get_real_path())
        lineno = pyobject._get_ast().lineno
        if path in self.files and lineno in self.files[path]:
            organizer = self.files[path][lineno]
            return organizer
    
    def _data_received(self, data):
        path = data[0][1]
        lineno = data[0][2]
        if path not in self.files:
            self.files[path] = {}
        if lineno not in self.files[path]:
            self.files[path][lineno] = _CallInformationOrganizer()
        returned = _ObjectPersistedForm.create_persistent_object(data[2])
        args = [_ObjectPersistedForm.create_persistent_object(arg) for arg in data[1]]
        self.files[path][lineno].add_call_information(args, returned)


class _CallInformationOrganizer(object):
    
    def __init__(self):
        self.args = None
        self.returned = None
    
    def add_call_information(self, args, returned):
        if self.returned is None or \
           not isinstance(returned, (_PersistedNone, _PersistedUnknown)):
            self.returned = returned
        if self.returned is None or args and \
           not isinstance(args[0], (_PersistedNone, _PersistedUnknown)):
            self.args = args


class _ObjectPersistedForm(object):
    
    def _get_pymodule(self, project, path):
        root = os.path.abspath(project.get_root_address())
        if path.startswith(root):
            relative_path = path[len(root):]
            if relative_path.startswith('/'):
                relative_path = relative_path[1:]
            resource = project.get_resource(relative_path)
        else:
            resource = project.get_out_of_project_resource(path)
        return project.get_pycore().resource_to_pyobject(resource)
    
    def _get_pyobject_at(self, project, path, lineno):
        scope = self._get_pymodule(project, path).get_scope()
        inner_scope = scope.get_inner_scope_for_line(lineno)
        return inner_scope.pyobject

    # TODO: Implement __eq__ for subclasses
    def __eq__(self, object_):
        if type(object) != type(self):
            return False

    @staticmethod
    def create_persistent_object(data):
        type_ = data[0]
        if type_ == 'none':
            return _PersistedNone()
        if type_ == 'module':
            return _PersistedModule(*data[1:])
        if type_ == 'function':
            return _PersistedFunction(*data[1:])
        if type_ == 'class':
            return _PersistedClass(*data[1:])
        if type_ == 'instance':
            return _PersistedClass(is_instance=True, *data[1:])
        return _PersistedUnknown()


class _PersistedNone(_ObjectPersistedForm):

    def to_pyobject(self, project):
        return None


class _PersistedUnknown(_ObjectPersistedForm):

    def to_pyobject(self, project):
        return None


class _PersistedModule(_ObjectPersistedForm):
    
    def __init__(self, path):
        self.path = path
    
    def to_pyobject(self, project):
        return self._get_pymodule(project, self.path)


class _PersistedFunction(_ObjectPersistedForm):
    
    def __init__(self, path, lineno):
        self.path = path
        self.lineno = lineno
    
    def to_pyobject(self, project):
        return self._get_pyobject_at(project, self.path, self.lineno)


class _PersistedClass(_ObjectPersistedForm):
    
    def __init__(self, path, name, is_instance=False):
        self.path = path
        self.name = name
        self.is_instance = is_instance
    
    def to_pyobject(self, project):
        pymodule = self._get_pymodule(project, self.path)
        module_scope = pymodule.get_scope()
        suspected_pyobject = None
        if self.name in module_scope.get_names():
            suspected_pyobject = module_scope.get_name(self.name).get_object()
        if suspected_pyobject is not None and \
           suspected_pyobject.get_type() == rope.base.pyobjects.PyObject.get_base_type('Type'):
            if self.is_instance:
                return rope.base.pyobjects.PyObject(suspected_pyobject)
            else:
                return suspected_pyobject
        else:
            lineno = self._find_occurrence(pymodule.get_resource().read())
            if lineno is not None:
                inner_scope = module_scope.get_inner_scope_for_line(lineno)
                return inner_scope.pyobject
    
    def _find_occurrence(self, source):
        pattern = re.compile(r'^\s*class\s*' + self.name + r'\b')
        lines = source.split('\n')
        for i in range(len(lines)):
            if pattern.match(lines[i]):
                return i + 1


class PythonFileRunner(object):
    """A class for running python project files"""

    def __init__(self, pycore, file_, args=None, stdin=None,
                 stdout=None, analyze_data=None):
        self.pycore = pycore
        self.file = file_
        self.analyze_data = analyze_data
        self.observers = []
        self.args = args
        self.stdin = stdin
        self.stdout = stdout
    
    def run(self):
        env = dict(os.environ)
        source_folders = []
        file_path = self.file._get_real_path()
        for folder in self.file.get_project().get_pycore().get_source_folders():
            source_folders.append(os.path.abspath(folder._get_real_path()))
        env['PYTHONPATH'] = env.get('PYTHONPATH', '') + os.pathsep + \
                            os.pathsep.join(source_folders)
        runmod_path = self.pycore.find_module('rope.base.runmod')._get_real_path()
        self.receiver = None
        self._init_data_receiving()
        send_info = '-'
        if self.receiver:
            send_info = self.receiver.get_send_info()
        args = [sys.executable, runmod_path, send_info,
                os.path.abspath(self.pycore.project.get_root_address()),
                os.path.abspath(self.file._get_real_path())]
        if self.args is not None:
            args.extend(self.args)
        self.process = subprocess.Popen(executable=sys.executable, args=args,
                                        cwd=os.path.split(file_path)[0], stdin=self.stdin,
                                        stdout=self.stdout, stderr=self.stdout, env=env)
    
    def _init_data_receiving(self):
        if self.analyze_data is None:
            return
        # Disabling FIFO data transfer due to blocking for running
        # unittests.
        # XXX: Handle FIFO data transfer for rope.ui.testview
        if True or os.name == 'nt':
            self.receiver = _SocketReceiver()
        else:
            self.receiver = _FIFOReceiver()
        self.receiving_thread = threading.Thread(target=self._receive_information)
        self.receiving_thread.setDaemon(True)
        self.receiving_thread.start()
    
    def _receive_information(self):
        for data in self.receiver.receive_data():
            self.analyze_data(data)
        for observer in self.observers:
            observer()

    def wait_process(self):
        """Wait for the process to finish"""
        self.process.wait()
        if self.analyze_data:
            self.receiving_thread.join()

    def kill_process(self):
        """Stop the process. This does *not* work on windows."""
        os.kill(self.process.pid, 9)
    
    def add_finishing_observer(self, observer):
        self.observers.append(observer)


class _MessageReceiver(object):
    
    def receive_data(self):
        pass
    
    def get_send_info(self):
        pass


class _SocketReceiver(_MessageReceiver):
    
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_port = 3037
        while self.data_port < 4000:
            try:
                self.server_socket.bind(('', self.data_port))
                break
            except socket.error, e:
                self.data_port += 1
        self.server_socket.listen(1)
    
    def get_send_info(self):
        return str(self.data_port)
        
    def receive_data(self):
        conn, addr = self.server_socket.accept()
        self.server_socket.close()
        my_file = conn.makefile('r')
        while True:
            try:
                yield pickle.load(my_file)
            except EOFError:
                break
        my_file.close()
        conn.close()


class _FIFOReceiver(_MessageReceiver):
    
    def __init__(self):
        # XXX: this is unsecure and might cause race conditions
        self.file_name = self._get_file_name()
        os.mkfifo(self.file_name)
    
    def _get_file_name(self):
        prefix = tempfile.gettempdir() + '/__rope_'
        i = 0
        while os.path.exists(prefix + str(i).rjust(4, '0')):
            i += 1
        return prefix + str(i).rjust(4, '0')
    
    def get_send_info(self):
        return self.file_name
        
    def receive_data(self):
        my_file = open(self.file_name, 'rb')
        while True:
            try:
                yield marshal.load(my_file)
            except EOFError:
                break
        my_file.close()
        os.remove(self.file_name)
