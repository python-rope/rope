import compiler

import rope.base.exceptions
import rope.base.pynames
import rope.base.pyobjects


class StatementEvaluator(object):

    def __init__(self, scope):
        self.scope = scope
        self.result = None

    def visitName(self, node):
        self.result = self.scope.lookup(node.name)

    def visitGetattr(self, node):
        pyname = get_statement_result(self.scope, node.expr)
        if pyname is not None and pyname.get_object() is not None:
            try:
                self.result = pyname.get_object().get_attribute(node.attrname)
            except rope.base.exceptions.AttributeNotFoundError:
                self.result = None

    def visitCallFunc(self, node):
        pyobject = self._get_object_for_node(node.node)
        if pyobject is None:
            return
        def _get_returned(pyobject):
            args = create_arguments(pyobject, node, self.scope)
            return pyobject.get_returned_object(args)
        if isinstance(pyobject, rope.base.pyobjects.AbstractClass):
            result = None
            if '__new__' in pyobject.get_attributes():
                new_function = pyobject.get_attribute('__new__').get_object()
                result = _get_returned(new_function)
            if result is None or \
               result == rope.base.pyobjects.get_unknown():
                result = rope.base.pyobjects.PyObject(pyobject)
            self.result = rope.base.pynames.AssignedName(pyobject=result)
            return

        pyfunction = None
        if isinstance(pyobject, rope.base.pyobjects.AbstractFunction):
            pyfunction = pyobject
        elif '__call__' in pyobject.get_attributes():
            pyfunction = pyobject.get_attribute('__call__').get_object()
        if pyfunction is not None:
            self.result = rope.base.pynames.AssignedName(
                pyobject=_get_returned(pyfunction))

    def visitConst(self, node):
        if isinstance(node.value, (str, unicode)):
            self.result = rope.base.pynames.AssignedName(
                pyobject=rope.base.builtins.get_str())

    def visitAdd(self, node):
        pass

    def visitAnd(self, node):
        pass

    def visitBackquote(self, node):
        pass

    def visitBitand(self, node):
        pass

    def visitBitor(self, node):
        pass

    def visitXor(self, node):
        pass

    def visitCompare(self, node):
        pass

    def visitDict(self, node):
        keys = None
        values = None
        if node.items:
            item = node.items[0]
            keys = self._get_object_for_node(item[0])
            values = self._get_object_for_node(item[1])
        self.result = rope.base.pynames.AssignedName(
            pyobject=rope.base.builtins.get_dict(keys, values))

    def visitFloorDiv(self, node):
        pass

    def visitList(self, node):
        holding = None
        if node.nodes:
            holding = self._get_object_for_node(node.nodes[0])
        self.result = rope.base.pynames.AssignedName(
            pyobject=rope.base.builtins.get_list(holding))

    def visitListComp(self, node):
        self.result = rope.base.pynames.AssignedName(
            pyobject=rope.base.builtins.get_list())

    def visitGenExpr(self, node):
        self.result = rope.base.pynames.AssignedName(
            pyobject=rope.base.builtins.get_iterator())

    def visitMul(self, node):
        pass

    def visitNot(self, node):
        pass

    def visitOr(self, node):
        pass

    def visitPower(self, node):
        pass

    def visitRightShift(self, node):
        pass

    def visitLeftShift(self, node):
        pass

    def visitSlice(self, node):
        self._call_function(node.expr, '__getslice__')

    def visitSliceobj(self, node):
        pass

    def visitTuple(self, node):
        objects = []
        if len(node.nodes) < 4:
            for stmt in node.nodes:
                pyobject = self._get_object_for_node(stmt)
                objects.append(pyobject)
        else:
            objects.append(self._get_object_for_node(node.nodes[0]))
        self.result = rope.base.pynames.AssignedName(
            pyobject=rope.base.builtins.get_tuple(*objects))

    def _get_object_for_node(self, stmt):
        pyname = get_statement_result(self.scope, stmt)
        pyobject = None
        if pyname is not None:
            pyobject = pyname.get_object()
        return pyobject

    def visitSubscript(self, node):
        self._call_function(node.expr, '__getitem__')

    def _call_function(self, node, function_name):
        pyobject = self._get_object_for_node(node)
        if pyobject is None:
            return
        if function_name in pyobject.get_attributes():
            call_function = pyobject.get_attribute(function_name)
            self.result = rope.base.pynames.AssignedName(
                pyobject=call_function.get_object().get_returned_object())

    def visitLambda(self, node):
        self.result = rope.base.pynames.AssignedName(
            pyobject=rope.base.builtins.Lambda(node, self.scope))


def get_statement_result(scope, node):
    """Evaluate a `compiler.ast` node and return a PyName

    Returns `None` if the expression cannot be evaluated.

    """
    evaluator = StatementEvaluator(scope)
    compiler.walk(node, evaluator)
    return evaluator.result


def get_string_result(scope, string):
    evaluator = StatementEvaluator(scope)
    node = compiler.parse(string)
    compiler.walk(node, evaluator)
    return evaluator.result


class Arguments(object):
    """A class for evaluating parameters passed to a function

    Always use the `create_argument` factory.  It handles when the
    first argument is implicit

    """

    def __init__(self, args, scope):
        self.args = args
        self.scope = scope

    def get_arguments(self, parameters):
        result = [None] * max(len(parameters), len(self.args))
        for index, arg in enumerate(self.args):
            if isinstance(arg, compiler.ast.Keyword) and arg.name in parameters:
                pyname = self._evaluate(arg.expr)
                if pyname is not None:
                    result[parameters.index(arg.name)] = pyname.get_object()
            else:
                pyname = self._evaluate(arg)
                if pyname is not None:
                    result[index] = pyname.get_object()
        return result

    def _evaluate(self, ast_node):
        return get_statement_result(self.scope, ast_node)


def create_arguments(pyfunction, call_func_node, scope):
    """A factory for creating `Arguments`'"""
    args = call_func_node.args
    called = call_func_node.node
    if isinstance(pyfunction, rope.base.pyobjects.PyFunction) and \
       isinstance(pyfunction.parent, rope.base.pyobjects.PyClass) and \
       isinstance(called, compiler.ast.Getattr):
        args = list(args)
        args.insert(0, called.expr)
    return Arguments(args, scope)
