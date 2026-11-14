def __rope_start_everything():
    import ast
    import os
    import socket
    import struct
    import sys

    try:
        import cPickle as pickle  # type: ignore
    except ImportError:
        import pickle
    import base64
    import hashlib
    import hmac
    import inspect
    import marshal
    import threading
    import types

    class _MessageSender:
        def send_data(self, data):
            pass

    class _SocketSender(_MessageSender):
        def __init__(self, port, key):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", port))
            self.my_file = s.makefile("wb")
            self.key = base64.b64decode(key)

        def send_data(self, data):
            if not self.my_file.closed:
                pickled_data = base64.b64encode(
                    pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
                )
                dgst = hmac.new(self.key, pickled_data, hashlib.sha256).digest()
                self.my_file.write(base64.b64encode(dgst) + b":" + pickled_data + b"\n")

        def close(self):
            self.my_file.close()

    class _FileSender(_MessageSender):
        def __init__(self, file_name):
            self.my_file = open(file_name, "wb")

        def send_data(self, data):
            if not self.my_file.closed:
                marshal.dump(data, self.my_file)

        def close(self):
            self.my_file.close()

    def _cached(func):
        cache = {}

        def newfunc(self, arg):
            if arg in cache:
                return cache[arg]
            result = func(self, arg)
            cache[arg] = result
            return result

        return newfunc

    class _FunctionCallDataSender:
        def __init__(self, send_info, project_root):
            self.project_root = project_root
            self._source_provenance = {}
            if send_info[0].isdigit():
                port, key = send_info.split(":", 1)
                self.sender = _SocketSender(int(port), key)
            else:
                self.sender = _FileSender(send_info)

            def global_trace(frame, event, arg):
                # HACK: Ignoring out->in calls
                # This might lose some information
                if self._is_an_interesting_call(frame):
                    return self.on_function_call

            sys.settrace(global_trace)
            threading.settrace(global_trace)

        def on_function_call(self, frame, event, arg):
            if event != "return":
                return
            args = []
            returned = ("unknown",)
            code = frame.f_code
            for argname in code.co_varnames[: code.co_argcount]:
                try:
                    argvalue = self._object_to_persisted_form(frame.f_locals[argname])
                    args.append(argvalue)
                except (TypeError, AttributeError):
                    args.append(("unknown",))
            try:
                returned = self._object_to_persisted_form(arg)
            except (TypeError, AttributeError):
                pass
            try:
                data = (
                    self._object_to_persisted_form(frame.f_code),
                    tuple(args),
                    returned,
                    self._get_body_provenance(code),
                )
                self.sender.send_data(data)
            except TypeError:
                pass
            return self.on_function_call

        def _get_body_provenance(self, code):
            source_path = self._path(code.co_filename)
            if source_path is None:
                return None
            try:
                with open(source_path, "rb") as source_file:
                    source = source_file.read()
                cache_key = (source_path, code.co_filename)
                cached = self._source_provenance.get(cache_key)
                if cached is None or cached[0] != source:
                    tree = ast.parse(source, filename=code.co_filename)
                    compiled = compile(
                        source,
                        code.co_filename,
                        "exec",
                        dont_inherit=True,
                        optimize=sys.flags.optimize,
                    )
                    signatures = []
                    pending = [compiled]
                    while pending:
                        compiled_code = pending.pop()
                        signatures.append(self._code_signature(compiled_code))
                        pending.extend(
                            value
                            for value in compiled_code.co_consts
                            if isinstance(value, types.CodeType)
                        )
                    cached = (source, tree, signatures)
                    self._source_provenance[cache_key] = cached
                _, tree, signatures = cached
                runtime_signature = self._code_signature(code)
                if signatures.count(runtime_signature) != 1:
                    return None
                functions = [
                    node
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == code.co_name
                    and code.co_firstlineno
                    in (
                        node.lineno,
                        min(
                            [node.lineno]
                            + [item.lineno for item in node.decorator_list]
                        ),
                    )
                ]
                if len(functions) != 1:
                    return None
                body = ast.Module(body=functions[0].body, type_ignores=[])
                body_version = (
                    "function-body-v1:"
                    + hashlib.sha256(
                        ast.dump(body, include_attributes=False).encode("utf-8")
                    ).hexdigest()
                )
                module_version = hashlib.sha256(
                    ast.dump(tree, include_attributes=False).encode("utf-8")
                ).hexdigest()
                return ("function-body-v1", body_version, module_version)
            except (OSError, SyntaxError, ValueError, TypeError, RecursionError):
                return None

        def _code_signature(self, code):
            fields = (
                "co_argcount",
                "co_posonlyargcount",
                "co_kwonlyargcount",
                "co_nlocals",
                "co_stacksize",
                "co_flags",
                "co_code",
                "co_names",
                "co_varnames",
                "co_filename",
                "co_name",
                "co_qualname",
                "co_firstlineno",
                "co_linetable",
                "co_exceptiontable",
                "co_freevars",
                "co_cellvars",
            )
            return (
                tuple((field, getattr(code, field, None)) for field in fields),
                tuple(self._constant_signature(value) for value in code.co_consts),
                tuple(code.co_positions()) if hasattr(code, "co_positions") else None,
                tuple(code.co_lines()) if hasattr(code, "co_lines") else None,
                (
                    getattr(code, "co_lnotab", None)
                    if not hasattr(code, "co_linetable")
                    else None
                ),
            )

        def _constant_signature(self, value):
            value_type = type(value)
            if value_type in (str, bytes, int, bool, type(None)):
                return (value_type.__name__, value)
            if value is Ellipsis:
                return ("ellipsis", value)
            if value_type is float:
                return ("float", struct.pack("!d", value))
            if value_type is complex:
                return ("complex", struct.pack("!dd", value.real, value.imag))
            if isinstance(value, types.CodeType):
                return ("code", self._code_signature(value))
            if value_type is tuple:
                return (
                    "tuple",
                    tuple(self._constant_signature(item) for item in value),
                )
            if value_type is frozenset:
                counts = {}
                for item in value:
                    signature = self._constant_signature(item)
                    counts[signature] = counts.get(signature, 0) + 1
                return ("frozenset", frozenset(counts.items()))
            raise TypeError("unsupported code constant")

        def _is_an_interesting_call(self, frame):
            # if frame.f_code.co_name in ['?', '<module>']:
            #    return False
            # return not frame.f_back or
            #    not self._is_code_inside_project(frame.f_back.f_code)
            if not self._is_code_inside_project(frame.f_code) and (
                not frame.f_back
                or not self._is_code_inside_project(frame.f_back.f_code)
            ):
                return False
            return True

        def _is_code_inside_project(self, code):
            source = self._path(code.co_filename)
            return (
                source is not None
                and os.path.exists(source)
                and _realpath(source).startswith(self.project_root)
            )

        @_cached
        def _get_persisted_code(self, object_):
            source = self._path(object_.co_filename)
            if not os.path.exists(source):
                raise TypeError("no source")
            return ("defined", _realpath(source), str(object_.co_firstlineno))

        @_cached
        def _get_persisted_class(self, object_):
            try:
                return (
                    "defined",
                    _realpath(inspect.getsourcefile(object_)),
                    object_.__name__,
                )
            except (TypeError, AttributeError):
                return ("unknown",)

        def _get_persisted_builtin(self, object_):
            if isinstance(object_, str):
                return ("builtin", "str")
            if isinstance(object_, list):
                holding = None
                if len(object_) > 0:
                    holding = object_[0]
                return ("builtin", "list", self._object_to_persisted_form(holding))
            if isinstance(object_, dict):
                keys = None
                values = None
                if len(object_) > 0:
                    # @todo - fix it properly, why is __locals__ being
                    # duplicated ?
                    keys = [key for key in object_.keys() if key != "__locals__"][0]
                    values = object_[keys]
                return (
                    "builtin",
                    "dict",
                    self._object_to_persisted_form(keys),
                    self._object_to_persisted_form(values),
                )
            if isinstance(object_, tuple):
                objects = []
                if len(object_) < 3:
                    for holding in object_:
                        objects.append(self._object_to_persisted_form(holding))
                else:
                    objects.append(self._object_to_persisted_form(object_[0]))
                return tuple(["builtin", "tuple"] + objects)
            if isinstance(object_, set):
                holding = None
                if len(object_) > 0:
                    for o in object_:
                        holding = o
                        break
                return ("builtin", "set", self._object_to_persisted_form(holding))
            return ("unknown",)

        def _object_to_persisted_form(self, object_):
            if object_ is None:
                return ("none",)
            if isinstance(object_, types.CodeType):
                return self._get_persisted_code(object_)
            if isinstance(object_, types.FunctionType):
                return self._get_persisted_code(object_.__code__)
            if isinstance(object_, types.MethodType):
                return self._get_persisted_code(object_.__func__.__code__)
            if isinstance(object_, types.ModuleType):
                return self._get_persisted_module(object_)
            if isinstance(object_, (str, list, dict, tuple, set)):
                return self._get_persisted_builtin(object_)
            if isinstance(object_, type):
                return self._get_persisted_class(object_)
            return ("instance", self._get_persisted_class(type(object_)))

        @_cached
        def _get_persisted_module(self, object_):
            path = self._path(object_.__file__)
            if path and os.path.exists(path):
                return ("defined", _realpath(path))
            return ("unknown",)

        def _path(self, path):
            if path.endswith(".pyc"):
                path = path[:-1]
            if path.endswith(".py"):
                return path

        def close(self):
            sys.settrace(None)
            threading.settrace(None)
            self.sender.close()

    def _realpath(path):
        return os.path.realpath(os.path.abspath(os.path.expanduser(path)))

    send_info = os.environ.pop("ROPE_DOA_SOCK", default=sys.argv[1])
    project_root = sys.argv[2]
    file_to_run = sys.argv[3]
    run_globals = globals()
    run_globals.update(
        {"__name__": "__main__", "__builtins__": __builtins__, "__file__": file_to_run}
    )

    if send_info != "-":
        data_sender = _FunctionCallDataSender(send_info, project_root)
    del sys.argv[1:4]
    with open(file_to_run) as f:
        code = compile(f.read(), file_to_run, "exec")
        exec(code, run_globals)
    if send_info != "-":
        data_sender.close()


if __name__ == "__main__":
    __rope_start_everything()
