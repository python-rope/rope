import os
import re
import socket
import subprocess
import sys
import cPickle as pickle
import marshal
import tempfile
import threading

import rope
from rope.base import pyobjects
from rope.base import builtins
from rope.base import pyscopes


class DynamicObjectInference(object):
    
    def __init__(self, pycore):
        self.info = pycore.call_info
        self.to_pyobject = _TextualToPyObject(pycore.project)
    
    def infer_returned_object(self, pyobject, args):
        organizer = self.info.find_organizer(pyobject)
        if organizer:
            return self.to_pyobject.transform(organizer.get_returned_object(
                                              pyobject, args))

    def infer_parameter_objects(self, pyobject):
        organizer = self.info.find_organizer(pyobject)
        if organizer is not None:
            pyobjects = [self.to_pyobject.transform(parameter)
                         for parameter in organizer.get_parameters()]
            return pyobjects
    
    def infer_assigned_object(self, pyname):
        pass
    
    def infer_for_object(self, pyname):
        pass


class CallInformationCollector(object):
    
    def __init__(self, pycore):
        self.pycore = pycore
        self.files = {}
        self.to_textual = _PyObjectToTextual(pycore.project)
    
    def run_module(self, resource, args=None, stdin=None, stdout=None):
        """Return a PythonFileRunner for controlling the process"""
        return PythonFileRunner(self.pycore, resource, args, stdin,
                                stdout, self._data_received)
    
    def _data_received(self, data):
        path = data[0][1]
        lineno = data[0][2]
        if path not in self.files:
            self.files[path] = {}
        if lineno not in self.files[path]:
            self.files[path][lineno] = _CallInformationOrganizer(self.to_textual)
        self.files[path][lineno].add_call_information(data[1], data[2])

    def find_organizer(self, pyobject):
        resource = pyobject.get_module().get_resource()
        if resource is None:
            return
        path = os.path.abspath(resource._get_real_path())
        lineno = pyobject._get_ast().lineno
        if path in self.files and lineno in self.files[path]:
            organizer = self.files[path][lineno]
            return organizer
    

class _CallInformationOrganizer(object):
    
    def __init__(self, to_textual):
        self.info = {}
        self.to_textual = to_textual
    
    def add_call_information(self, args, returned):
        self.info[args] = returned
    
    def get_parameters(self):
        for args in self.info.keys():
            if len(args) > 0 and args[0] not in ('unknown', 'none'):
                return args
        return self.info.keys()[0]

    def get_returned_object(self, pyfunction, args):
        if len(self.info) <= 1 or args is None:
            return self._get_default_returned()
        arguments = args.get_arguments(pyfunction.parameters)
        textual_args = tuple([self.to_textual.transform(arg) for arg in arguments])
        if textual_args in self.info:
            return self.info[textual_args]
        return self._get_default_returned()
    
    def _get_default_returned(self):
        default = ('unknown')
        for returned in self.info.values():
            if returned not in ('unknown', 'none'):
                return returned
            default = returned
        return default


class _PyObjectToTextual(object):
    
    def __init__(self, project):
        self.project = project
    
    def transform(self, pyobject):
        """Transform a `PyObject` to textual form"""
        if pyobject is None:
            return ('none',)
        object_type = type(pyobject)
        method = getattr(self, object_type.__name__ + '_to_textual')
        return method(pyobject)

    def PyObject_to_textual(self, pyobject):
        if type(pyobject.get_type()) != pyobjects.PyObject:
            result = self.transform(pyobject.get_type())
            if result[0] == 'class':
                return ('instance',) + result[1:]
            return result
        return ('unknown',)

    def PyFunction_to_textual(self, pyobject):
        return ('function', self._get_pymodule_path(pyobject.get_module()),
                pyobject._get_ast().lineno)
    
    def PyClass_to_textual(self, pyobject):
        return ('class', self._get_pymodule_path(pyobject.get_module()),
                pyobject._get_ast().name)
    
    def PyModule_to_textual(self, pyobject):
        return ('module', self._get_pymodule_path(pyobject))
    
    def PyPackage_to_textual(self, pyobject):
        return ('module', self._get_pymodule_path(pyobject))
    
    def List_to_textual(self, pyobject):
        return ('builtin', 'list', self.transform(pyobject.holding))
    
    def Dict_to_textual(self, pyobject):
        return ('builtin', 'dict', self.transform(pyobject.keys),
                self.transform(pyobject.values))
    
    def Tuple_to_textual(self, pyobject):
        objects = [self.transform(holding) for holding in pyobject.get_holding_objects()]
        return tuple(['builtin', 'tuple'] + objects)
    
    def Set_to_textual(self, pyobject):
        return ('builtin', 'set', self.transform(pyobject.holding))
    
    def Str_to_textual(self, pyobject):
        return ('builtin', 'str')
    
    def _get_pymodule_path(self, pymodule):
        resource = pymodule.get_resource()
        resource_path = resource.get_path()
        if os.path.isabs(resource_path):
            return resource_path
        path = os.path.abspath(os.path.normpath(os.path.join(
                                                self.project.get_root_address(),
                                                resource_path)))
        return path
    

class _TextualToPyObject(object):
    
    def __init__(self, project):
        self.project = project
    
    def transform(self, textual):
        """Transform an object from textual form to `PyObject`"""
        type = textual[0]
        method = getattr(self, type + '_to_pyobject')
        return method(textual)

    def module_to_pyobject(self, textual):
        path = textual[1]
        return self._get_pymodule(path)
    
    def builtin_to_pyobject(self, textual):
        name = textual[1]
        if name == 'str':
            return builtins.get_str()
        if name == 'list':
            holding = self.transform(textual[2])
            return builtins.get_list(holding)
        if name == 'dict':
            keys = self.transform(textual[2])
            values = self.transform(textual[3])
            return builtins.get_dict(keys, values)
        if name == 'tuple':
            objects = []
            for holding in textual[2:]:
                objects.append(self.transform(holding))
            return builtins.get_tuple(*objects)
        if name == 'set':
            holding = self.transform(textual[2])
            return builtins.get_set(holding)
        return None
    
    def unknown_to_pyobject(self, textual):
        return None
    
    def none_to_pyobject(self, textual):
        return None
    
    def function_to_pyobject(self, textual):
        return self._get_pyobject_at(textual[1], textual[2])
    
    def class_to_pyobject(self, textual):
        path, name = textual[1:]
        pymodule = self._get_pymodule(path)
        module_scope = pymodule.get_scope()
        suspected_pyobject = None
        if name in module_scope.get_names():
            suspected_pyobject = module_scope.get_name(name).get_object()
        if suspected_pyobject is not None and \
           suspected_pyobject.get_type() == pyobjects.PyObject.get_base_type('Type'):
            return suspected_pyobject
        else:
            lineno = self._find_occurrence(name, pymodule.get_resource().read())
            if lineno is not None:
                inner_scope = module_scope.get_inner_scope_for_line(lineno)
                return inner_scope.pyobject
    
    def instance_to_pyobject(self, textual):
        return pyobjects.PyObject(self.class_to_pyobject(textual))
    
    def _find_occurrence(self, name, source):
        pattern = re.compile(r'^\s*class\s*' + name + r'\b')
        lines = source.split('\n')
        for i in range(len(lines)):
            if pattern.match(lines[i]):
                return i + 1

    def _get_pymodule(self, path):
        root = os.path.abspath(self.project.get_root_address())
        if path.startswith(root):
            relative_path = path[len(root):]
            if relative_path.startswith('/') or relative_path.startswith(os.sep):
                relative_path = relative_path[1:]
            resource = self.project.get_resource(relative_path)
        else:
            resource = self.project.get_out_of_project_resource(path)
        return self.project.get_pycore().resource_to_pyobject(resource)
    
    def _get_pyobject_at(self, path, lineno):
        scope = self._get_pymodule(path).get_scope()
        inner_scope = scope.get_inner_scope_for_line(lineno)
        return inner_scope.pyobject


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
        for folder in self.pycore.get_source_folders():
            source_folders.append(os.path.abspath(folder._get_real_path()))
        env['PYTHONPATH'] = env.get('PYTHONPATH', '') + os.pathsep + \
                            os.pathsep.join(source_folders)
        runmod_path = self.pycore.find_module('rope.base.oi.runmod')._get_real_path()
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
        #temp = open('/dev/shm/info', 'w')
        for data in self.receiver.receive_data():
            self.analyze_data(data)
            #temp.write(str(data) + '\n')
        #temp.close()
        for observer in self.observers:
            observer()

    def wait_process(self):
        """Wait for the process to finish"""
        self.process.wait()
        if self.analyze_data:
            self.receiving_thread.join()

    def kill_process(self):
        """Stop the process. This does *not* work on windows."""
        if os.name != 'nt':
            os.kill(self.process.pid, 9)
        else:
            import ctypes
            ctypes.windll.kernel32.TerminateProcess(int(self.process._handle), -1)
    
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
