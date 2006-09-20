
def __rope_start_everything():
    import os
    import sys
    import socket
    import cPickle as pickle
    import inspect
    import types
    
    class _FunctionCallDataSender(object):
        
        def __init__(self, port, project_root):
            self.project_root = project_root
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('', port))
            self.my_file = s.makefile('w')
        
            def local_trace(frame, event, arg):
                if event == 'return':
                    self.on_function_call(frame, event, arg)
            def global_trace(frame, event, arg):
                # Note: Ignoring out to in calls
                if self._is_code_inside_project(frame.f_code):
                    return local_trace
            sys.settrace(global_trace)

        def on_function_call(self, frame, event, arg):
            if event == 'return':
                if not self._is_an_interesting_call(frame):
                    return
                args = []
                returned = ('unknown')
                code = frame.f_code
                for argname in code.co_varnames[:code.co_argcount]:
                    try:
                        args.append(self._object_to_persisted_form(frame.f_locals[argname]))
                    except TypeError:
                        args.append(('unknown'))
                    except AttributeError:
                        args.append(('unknown'))
                try:
                    returned = self._object_to_persisted_form(arg)
                except TypeError:
                    pass
                except AttributeError:
                    pass
                try:
                    data = (self._object_to_persisted_form(frame.f_code),
                            args, returned)
                    pickle.dump(data, self.my_file)
                except TypeError, e:
                    pass
                except AttributeError, e:
                    pass
        
        def _is_an_interesting_call(self, frame):
            if frame.f_code.co_name in ['?', '<module>']:
                return False
            if not self._is_code_inside_project(frame.f_code) and \
               (not frame.f_back or not self._is_code_inside_project(frame.f_back)):
                return False
            return True
        
        def _is_code_inside_project(self, code):
            source = inspect.getsourcefile(code)
            return source and os.path.abspath(source).startswith(self.project_root)
    
        def _get_persisted_code(self, object_):
            return ('function', os.path.abspath(object_.co_filename), object_.co_firstlineno)
    
        def _get_persisted_class(self, object_, type_):
            return (type_, os.path.abspath(inspect.getsourcefile(object_)),
                    object_.__name__)
    
        def _object_to_persisted_form(self, object_):
            if object_ == None:
                return ('none')
            if isinstance(object_, types.CodeType):
                return self._get_persisted_code(object_)
            if isinstance(object_, types.FunctionType):
                return self._get_persisted_code(object_.func_code)
            if isinstance(object_, types.MethodType):
                return self._get_persisted_code(object_.im_func.func_code)
            if isinstance(object_, types.ModuleType):
                return ('module', os.path.abspath(object_.__file__))
            if isinstance(object_, (types.TypeType, types.ClassType)):
                return self._get_persisted_class(object_, 'class')
            return self._get_persisted_class(type(object_), 'instance')


    data_port = int(sys.argv[1])
    project_root = sys.argv[2]
    file_to_run = sys.argv[3]
    run_globals = globals()
    run_globals.update({'__name__': '__main__',
                        '__builtins__': __builtins__,
                        '__file__': file_to_run})
    if data_port != -1:
        data_sender = _FunctionCallDataSender(data_port, project_root)
    del sys.argv[1:4]
    execfile(file_to_run, run_globals)
    

if __name__ == '__main__':
    __rope_start_everything()
