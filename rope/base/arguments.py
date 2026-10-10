import rope.base.evaluate
from rope.base import ast


class Arguments:
    """A class for evaluating parameters passed to a function

    You can use the `create_arguments` factory.  It handles implicit
    first arguments.

    """

    def __init__(self, args, scope, pyfunction=None):
        self.args = args
        self.scope = scope
        self.pyfunction = pyfunction
        self.instance = None

    def get_arguments(self, parameters):
        result = []
        for pyname in self.get_pynames(parameters):
            if pyname is None:
                result.append(None)
            else:
                result.append(pyname.get_object())
        return result

    def get_pynames(self, parameters):
        if isinstance(self.pyfunction, rope.base.pyobjects.PyFunction):
            return self._get_function_pynames(parameters)
        result = [None] * max(len(parameters), len(self.args))
        for index, arg in enumerate(self.args):
            if isinstance(arg, ast.keyword) and arg.arg in parameters:
                result[parameters.index(arg.arg)] = self._evaluate(arg.value)
            else:
                result[index] = self._evaluate(arg)
        return result

    def _get_function_pynames(self, parameters):
        positional = [
            name
            for name in self.pyfunction.get_positional_param_names()
            if name in parameters
        ]
        keywords = set(self.pyfunction.get_keyword_param_names()) & set(parameters)
        result = dict.fromkeys(parameters)
        provided = set()
        position = 0
        unknown_positions = False
        unknown_keywords = False
        for arg in self.args:
            if isinstance(arg, ast.Starred):
                unknown_positions = True
            elif isinstance(arg, ast.keyword):
                if arg.arg is None:
                    unknown_keywords = True
                elif arg.arg in keywords:
                    result[arg.arg] = self._evaluate(arg.value)
                    provided.add(arg.arg)
            elif not unknown_positions:
                if position < len(positional):
                    result[positional[position]] = self._evaluate(arg)
                    provided.add(positional[position])
                position += 1
        for name, default in self.pyfunction.get_parameter_defaults().items():
            if name not in result or name in provided:
                continue
            if unknown_positions and name in positional:
                continue
            if unknown_keywords and name in keywords:
                continue
            result[name] = rope.base.evaluate.eval_node(
                self.pyfunction.parent.get_scope(), default
            )
        return [result[name] for name in parameters]

    def get_instance_pyname(self):
        if self.args:
            return self._evaluate(self.args[0])

    def _evaluate(self, ast_node):
        return rope.base.evaluate.eval_node(self.scope, ast_node)


def create_arguments(primary, pyfunction, call_node, scope, ignore_instance=False):
    """A factory for creating `Arguments`"""
    args = list(call_node.args)
    args.extend(call_node.keywords)
    called = call_node.func
    result = Arguments(args, scope, pyfunction)
    if ignore_instance or not isinstance(called, ast.Attribute):
        return result
    if isinstance(pyfunction, rope.base.pyobjects.PyFunction) and primary is not None:
        kind = pyfunction.get_kind()
        receiver = primary.get_object()
        if kind == "classmethod":
            if not isinstance(receiver, rope.base.pyobjects.AbstractClass):
                receiver = receiver.get_type()
            return MixedArguments(
                rope.base.pynames.UnboundName(receiver), result, scope
            )
        if kind == "method" and _is_method_call(primary, pyfunction):
            return MixedArguments(primary, result, scope)
    elif _is_method_call(primary, pyfunction):
        args.insert(0, called.value)
    return result


class ObjectArguments:
    def __init__(self, pynames):
        self.pynames = pynames

    def get_arguments(self, parameters):
        result = []
        for pyname in self.pynames:
            if pyname is None:
                result.append(None)
            else:
                result.append(pyname.get_object())
        return result

    def get_pynames(self, parameters):
        return self.pynames

    def get_instance_pyname(self):
        return self.pynames[0]


class MixedArguments:
    def __init__(self, pyname, arguments, scope):
        """`arguments` is an instance of `Arguments`"""
        self.pyname = pyname
        self.args = arguments

    def get_pynames(self, parameters):
        if not parameters:
            return []
        function = getattr(self.args, "pyfunction", None)
        if isinstance(function, rope.base.pyobjects.PyFunction):
            positional = function.get_positional_param_names()
            if not positional or parameters[0] != positional[0]:
                return self.args.get_pynames(parameters)
        return [self.pyname] + self.args.get_pynames(parameters[1:])

    def get_arguments(self, parameters):
        result = []
        for pyname in self.get_pynames(parameters):
            if pyname is None:
                result.append(None)
            else:
                result.append(pyname.get_object())
        return result

    def get_instance_pyname(self):
        return self.pyname


def _is_method_call(primary, pyfunction):
    if primary is None:
        return False
    pyobject = primary.get_object()
    if (
        isinstance(pyobject.get_type(), rope.base.pyobjects.PyClass)
        and isinstance(pyfunction, rope.base.pyobjects.PyFunction)
        and isinstance(pyfunction.parent, rope.base.pyobjects.PyClass)
    ):
        return True
    if isinstance(
        pyobject.get_type(), rope.base.pyobjects.AbstractClass
    ) and isinstance(pyfunction, rope.base.builtins.BuiltinFunction):
        return True
    return False
