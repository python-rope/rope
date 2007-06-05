import rope.base
from rope.base import ast, pyobjects, pynames, evaluate, builtins


class StaticObjectInference(object):

    def __init__(self, pycore):
        self.pycore = pycore

    def infer_returned_object(self, pyobject, args):
        if args:
            # HACK: Setting parameter objects manually
            # This is not thread safe and might cause problems if `args`
            # does not come from a good call site
            pyobject.get_scope().invalidate_data()
            pyobject._set_parameter_pyobjects(
                args.get_arguments(pyobject.get_param_names(special_args=False)))
        scope = pyobject.get_scope()
        if not scope._get_returned_asts():
            return
        for returned_node in reversed(scope._get_returned_asts()):
            try:
                resulting_pyname = evaluate.get_statement_result(scope,
                                                                 returned_node)
                if resulting_pyname is None:
                    return None
                pyobject = resulting_pyname.get_object()
                if pyobject == pyobjects.get_unknown():
                    return
                if not scope._is_generator():
                    return resulting_pyname.get_object()
                else:
                    return builtins.get_generator(resulting_pyname.get_object())
            except pyobjects.IsBeingInferredError:
                pass

    def infer_parameter_objects(self, pyobject):
        objects = []
        if pyobject.parent is not None and \
           isinstance(pyobject.parent, pyobjects.PyClass):
            if not pyobject.decorators:
                objects.append(pyobjects.PyObject(pyobject.parent))
            elif self._is_staticmethod_decorator(pyobject.decorators[0]):
                objects.append(pyobjects.get_unknown())
            elif self._is_classmethod_decorator(pyobject.decorators[0]):
                objects.append(pyobject.parent)
            elif pyobject.get_param_names()[0] == 'self':
                objects.append(pyobjects.PyObject(pyobject.parent))
        params = pyobject.get_param_names(special_args=False)
        for parameter in params[len(objects):]:
            objects.append(pyobjects.get_unknown())
        return objects

    def _is_staticmethod_decorator(self, node):
        return isinstance(node, ast.Name) and node.id == 'staticmethod'

    def _is_classmethod_decorator(self, node):
        return isinstance(node, ast.Name) and node.id == 'classmethod'

    def analyze_module(self, pymodule, should_analyze=None):
        """Analyze `pymodule` for static object inference"""
        _analyze_node(self.pycore, pymodule, should_analyze)


def _analyze_node(pycore, pydefined, should_analyze):
    if should_analyze is not None and not should_analyze(pydefined):
        return
    #    if hasattr(pydefined, 'get_name'):
    #        print pydefined.get_name()
    visitor = SOIVisitor(pycore, pydefined, should_analyze)
    for child in ast.get_child_nodes(pydefined.get_ast()):
        ast.walk(child, visitor)


class SOIVisitor(object):

    def __init__(self, pycore, pydefined, should_analyze):
        self.pycore = pycore
        self.pymodule = pydefined.get_module()
        self.scope = pydefined.get_scope()
        self.should_analyze = should_analyze

    def _FunctionDef(self, node):
        self._analyze_child(node)

    def _ClassDef(self, node):
        self._analyze_child(node)

    def _analyze_child(self, node):
        pydefined = self.scope.get_name(node.name).get_object()
        _analyze_node(self.pycore, pydefined, self.should_analyze)

    def _Call(self, node):
        for child in ast.get_child_nodes(node):
            ast.walk(child, self)
        primary, pyname = evaluate.get_primary_and_result(self.scope,
                                                          node.func)
        if pyname is None:
            return
        pyfunction = pyname.get_object()
        if isinstance(pyfunction, pyobjects.AbstractFunction):
            args = evaluate.create_arguments(primary, pyfunction,
                                             node, self.scope)
        elif isinstance(pyfunction, pyobjects.PyClass):
            pyclass = pyfunction
            if '__init__' in pyfunction.get_attributes():
                pyfunction = pyfunction.get_attribute('__init__').get_object()
            pyname = pynames.UnboundName(pyobjects.PyObject(pyclass))
            args = self._args_with_self(primary, pyname, pyfunction, node)
        elif '__call__' in pyfunction.get_attributes():
            pyfunction = pyfunction.get_attribute('__call__').get_object()
            args = self._args_with_self(primary, pyname, pyfunction, node)
        else:
            return
        self._call(pyfunction, args)

    def _args_with_self(self, primary, self_pyname, pyfunction, node):
        base_args = evaluate.create_arguments(primary, pyfunction,
                                              node, self.scope)
        return evaluate.MixedArguments(self_pyname, base_args, self.scope)

    def _call(self, pyfunction, args):
        if isinstance(pyfunction, pyobjects.PyFunction):
            self.pycore.object_info.function_called(
                pyfunction, args.get_arguments(pyfunction.get_param_names()))
        # XXX: Maybe we should not call every builtin function
        if isinstance(pyfunction, builtins.BuiltinFunction):
            pyfunction.get_returned_object(args)

    def _Assign(self, node):
        for child in ast.get_child_nodes(node):
            ast.walk(child, self)
        visitor = _SOIAssignVisitor()
        nodes = []
        for child in node.targets:
            ast.walk(child, visitor)
            nodes.extend(visitor.nodes)
        for subscript, levels in nodes:
            instance = evaluate.get_statement_result(self.scope, subscript.value)
            args_pynames = []
            args_pynames.append(evaluate.get_statement_result(
                                self.scope, subscript.slice.value))
            value = self.pycore.object_infer._infer_assignment(
                pynames._Assigned(node.value, levels), self.pymodule)
            args_pynames.append(pynames.UnboundName(value))
            if instance is not None and value is not None:
                pyobject = instance.get_object()
                if '__setitem__' in pyobject.get_attributes():
                    pyfunction = pyobject.get_attribute('__setitem__').get_object()
                    args = evaluate.ObjectArguments([instance] + args_pynames)
                    self._call(pyfunction, args)
                # IDEA: handle `__setslice__` too


class _SOIAssignVisitor(pyobjects._NodeNameCollector):

    def __init__(self):
        super(_SOIAssignVisitor, self).__init__()
        self.nodes = []

    def _added(self, node, levels):
        if isinstance(node, ast.Subscript) and \
           isinstance(node.slice, ast.Index):
            self.nodes.append((node, levels))
