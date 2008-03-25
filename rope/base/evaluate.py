import rope.base.builtins
import rope.base.pynames
import rope.base.pyobjects
from rope.base import ast, astutils, exceptions, pyobjects
from rope.base.codeanalyze import WordRangeFinder


BadIdentifierError = exceptions.BadIdentifierError

def get_primary_and_pyname_at(pymodule, offset):
    """Find the primary and pyname at offset"""
    pyname_finder = ScopeNameFinder(pymodule)
    return pyname_finder.get_primary_and_pyname_at(offset)


def get_pyname_at(pymodule, offset):
    """Find the pyname at the offset"""
    return get_primary_and_pyname_at(pymodule, offset)[1]


def get_statement_result(scope, node):
    """Evaluate a `ast.AST` node and return a PyName

    Return `None` if the expression cannot be evaluated.

    """
    return get_primary_and_result(scope, node)[1]


def get_primary_and_result(scope, node):
    evaluator = StatementEvaluator(scope)
    ast.walk(node, evaluator)
    return evaluator.old_result, evaluator.result


def get_pyname_in_scope(holding_scope, name):
    return get_primary_and_pyname_in_scope(holding_scope, name)[1]


def get_primary_and_pyname_in_scope(holding_scope, name):
    try:
        # parenthesizing for handling cases like 'a_var.\nattr'
        node = ast.parse('(%s)' % name)
    except SyntaxError:
        raise BadIdentifierError('Not a resolvable python identifier selected.')
    return get_primary_and_result(holding_scope, node)


def get_string_result(scope, string):
    """use `get_pyname_in_scope` instead"""
    evaluator = StatementEvaluator(scope)
    node = ast.parse(string)
    ast.walk(node, evaluator)
    return evaluator.result


class ScopeNameFinder(object):

    def __init__(self, pymodule):
        self.source_code = pymodule.source_code
        self.module_scope = pymodule.get_scope()
        self.lines = pymodule.lines
        self.word_finder = WordRangeFinder(self.source_code)

    def _is_defined_in_class_body(self, holding_scope, offset, lineno):
        if lineno == holding_scope.get_start() and \
           holding_scope.parent is not None and \
           holding_scope.parent.get_kind() == 'Class' and \
           self.word_finder.is_a_class_or_function_name_in_header(offset):
            return True
        if lineno != holding_scope.get_start() and \
           holding_scope.get_kind() == 'Class' and \
           self.word_finder._is_name_assigned_in_class_body(offset):
            return True
        return False

    def _is_function_name_in_function_header(self, scope, offset, lineno):
        if scope.get_start() <= lineno <= scope.get_body_start() and \
           scope.get_kind() == 'Function' and \
           self.word_finder.is_a_class_or_function_name_in_header(offset):
            return True
        return False

    def get_pyname_at(self, offset):
        return self.get_primary_and_pyname_at(offset)[1]

    def get_primary_and_pyname_at(self, offset):
        lineno = self.lines.get_line_number(offset)
        holding_scope = self.module_scope.get_inner_scope_for_line(lineno)
        # function keyword parameter
        if self.word_finder.is_function_keyword_parameter(offset):
            keyword_name = self.word_finder.get_word_at(offset)
            pyobject = self.get_enclosing_function(offset)
            if isinstance(pyobject, pyobjects.PyFunction):
                return (None, pyobject.get_parameters().get(keyword_name, None))

        # class body
        if self._is_defined_in_class_body(holding_scope, offset, lineno):
            class_scope = holding_scope
            if lineno == holding_scope.get_start():
                class_scope = holding_scope.parent
            name = self.word_finder.get_primary_at(offset).strip()
            try:
                return (None, class_scope.pyobject[name])
            except rope.base.exceptions.AttributeNotFoundError:
                return (None, None)
        # function header
        if self._is_function_name_in_function_header(holding_scope, offset, lineno):
            name = self.word_finder.get_primary_at(offset).strip()
            return (None, holding_scope.parent[name])
        # from statement module
        if self.word_finder.is_from_statement_module(offset):
            module = self.word_finder.get_primary_at(offset)
            module_pyname = self._find_module(module)
            return (None, module_pyname)
        if self.word_finder.is_from_aliased(offset):
            name = self.word_finder.get_from_aliased(offset)
        else:
            name = self.word_finder.get_primary_at(offset)
        return get_primary_and_pyname_in_scope(holding_scope, name)

    def get_enclosing_function(self, offset):
        function_parens = self.word_finder.find_parens_start_from_inside(offset)
        try:
            function_pyname = self.get_pyname_at(function_parens - 1)
        except BadIdentifierError:
            function_pyname = None
        if function_pyname is not None:
            pyobject = function_pyname.get_object()
            if isinstance(pyobject, pyobjects.AbstractFunction):
                return pyobject
            elif isinstance(pyobject, pyobjects.AbstractClass) and \
                 '__init__' in pyobject:
                return pyobject['__init__'].get_object()
            elif '__call__' in pyobject:
                return pyobject['__call__'].get_object()
        return None

    def _find_module(self, module_name):
        dots = 0
        while module_name[dots] == '.':
            dots += 1
        return rope.base.pynames.ImportedModule(
            self.module_scope.pyobject, module_name[dots:], dots)


class StatementEvaluator(object):

    def __init__(self, scope):
        self.scope = scope
        self.result = None
        self.old_result = None

    def _Name(self, node):
        self.result = self.scope.lookup(node.id)

    def _Attribute(self, node):
        pyname = get_statement_result(self.scope, node.value)
        if pyname is None:
            pyname = rope.base.pynames.UnboundName()
        self.old_result = pyname
        if pyname.get_object() != rope.base.pyobjects.get_unknown():
            try:
                self.result = pyname.get_object()[node.attr]
            except exceptions.AttributeNotFoundError:
                self.result = None

    def _Call(self, node):
        primary, pyobject = self._get_primary_and_object_for_node(node.func)
        if pyobject is None:
            return
        def _get_returned(pyobject):
            args = create_arguments(primary, pyobject, node, self.scope)
            return pyobject.get_returned_object(args)
        if isinstance(pyobject, rope.base.pyobjects.AbstractClass):
            result = None
            if '__new__' in pyobject:
                new_function = pyobject['__new__'].get_object()
                result = _get_returned(new_function)
            if result is None or \
               result == rope.base.pyobjects.get_unknown():
                result = rope.base.pyobjects.PyObject(pyobject)
            self.result = rope.base.pynames.UnboundName(pyobject=result)
            return

        pyfunction = None
        if isinstance(pyobject, rope.base.pyobjects.AbstractFunction):
            pyfunction = pyobject
        elif '__call__' in pyobject:
            pyfunction = pyobject['__call__'].get_object()
        if pyfunction is not None:
            self.result = rope.base.pynames.UnboundName(
                pyobject=_get_returned(pyfunction))

    def _Str(self, node):
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_str())

    def _Num(self, node):
        type_name = type(node.n).__name__
        self.result = self._get_builtin_name(type_name)

    def _get_builtin_name(self, type_name):
        pytype = rope.base.builtins.builtins[type_name].get_object()
        return rope.base.pynames.UnboundName(
            rope.base.pyobjects.PyObject(pytype))

    def _BinOp(self, node):
        self.result = rope.base.pynames.UnboundName(
            self._get_object_for_node(node.left))

    def _BoolOp(self, node):
        self.result = rope.base.pynames.UnboundName(
            self._get_object_for_node(node.values[0]))

    def _Repr(self, node):
        self.result = self._get_builtin_name('str')

    def _UnaryOp(self, node):
        self.result = rope.base.pynames.UnboundName(
            self._get_object_for_node(node.operand))

    def _Compare(self, node):
        self.result = self._get_builtin_name('bool')

    def _Dict(self, node):
        keys = None
        values = None
        if node.keys:
            keys = self._get_object_for_node(node.keys[0])
            values = self._get_object_for_node(node.values[0])
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_dict(keys, values))

    def _List(self, node):
        holding = None
        if node.elts:
            holding = self._get_object_for_node(node.elts[0])
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_list(holding))

    def _ListComp(self, node):
        pyobject = self._what_does_comprehension_hold(node)
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_list(pyobject))

    def _GeneratorExp(self, node):
        pyobject = self._what_does_comprehension_hold(node)
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_iterator(pyobject))

    def _what_does_comprehension_hold(self, node):
        scope = self._make_comprehension_scope(node)
        pyname = get_statement_result(scope, node.elt)
        return pyname.get_object() if pyname is not None else None

    def _make_comprehension_scope(self, node):
        scope = self.scope
        module = scope.pyobject.get_module()
        names = {}
        for comp in node.generators:
            new_names = _get_evaluated_names(
                comp.target, comp.iter, evaluation='.__iter__().next()',
                lineno=node.lineno, module=module)
            names.update(new_names)
        return rope.base.pyscopes.TemporaryScope(scope.pycore, scope, names)

    def _Tuple(self, node):
        objects = []
        if len(node.elts) < 4:
            for stmt in node.elts:
                pyobject = self._get_object_for_node(stmt)
                objects.append(pyobject)
        else:
            objects.append(self._get_object_for_node(node.elts[0]))
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_tuple(*objects))

    def _get_object_for_node(self, stmt):
        pyname = get_statement_result(self.scope, stmt)
        pyobject = None
        if pyname is not None:
            pyobject = pyname.get_object()
        return pyobject

    def _get_primary_and_object_for_node(self, stmt):
        primary, pyname = get_primary_and_result(self.scope, stmt)
        pyobject = None
        if pyname is not None:
            pyobject = pyname.get_object()
        return primary, pyobject

    def _Subscript(self, node):
        if isinstance(node.slice, ast.Index):
            self._call_function(node.value, '__getitem__',
                                [node.slice.value])
        elif isinstance(node.slice, ast.Slice):
            self._call_function(node.value, '__getslice__')

    def _call_function(self, node, function_name, other_args=None):
        pyname = get_statement_result(self.scope, node)
        if pyname is not None:
            pyobject = pyname.get_object()
        else:
            return
        if function_name in pyobject:
            call_function = pyobject[function_name].get_object()
            args = [node]
            if other_args:
                args += other_args
            arguments = Arguments(args, self.scope)
            self.result = rope.base.pynames.UnboundName(
                pyobject=call_function.get_returned_object(arguments))

    def _Lambda(self, node):
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.Lambda(node, self.scope))


class Arguments(object):
    """A class for evaluating parameters passed to a function

    You can use the `create_arguments` factory.  It handles implicit
    first arguments.

    """

    def __init__(self, args, scope):
        self.args = args
        self.scope = scope
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
        result = [None] * max(len(parameters), len(self.args))
        for index, arg in enumerate(self.args):
            if isinstance(arg, ast.keyword) and arg.arg in parameters:
                result[parameters.index(arg.arg)] = self._evaluate(arg.value)
            else:
                result[index] = self._evaluate(arg)
        return result

    def get_instance_pyname(self):
        if self.args:
            return self._evaluate(self.args[0])

    def _evaluate(self, ast_node):
        return get_statement_result(self.scope, ast_node)


class ObjectArguments(object):

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


class MixedArguments(object):

    def __init__(self, pyname, arguments, scope):
        """`argumens` is an instance of `Arguments`"""
        self.pyname = pyname
        self.args = arguments

    def get_pynames(self, parameters):
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


def create_arguments(primary, pyfunction, call_node, scope):
    """A factory for creating `Arguments`"""
    args = list(call_node.args)
    args.extend(call_node.keywords)
    called = call_node.func
    # XXX: Handle constructors
    if _is_method_call(primary, pyfunction) and \
       isinstance(called, ast.Attribute):
        args.insert(0, called.value)
    return Arguments(args, scope)


def _is_method_call(primary, pyfunction):
    if primary is None:
        return False
    pyobject = primary.get_object()
    if isinstance(pyobject.get_type(), rope.base.pyobjects.PyClass) and \
       isinstance(pyfunction, rope.base.pyobjects.PyFunction) and \
       isinstance(pyfunction.parent, rope.base.pyobjects.PyClass):
        return True
    if isinstance(pyobject.get_type(), rope.base.pyobjects.AbstractClass) and \
       isinstance(pyfunction, rope.base.builtins.BuiltinFunction):
        return True
    return False


def _get_evaluated_names(targets, assigned, **kwds):
    """Get `pynames.EvaluatedName`\s

    `kwds` is passed to `pynames.EvaluatedName` and should hold
    things like lineno, evaluation, and module.
    """
    result = {}
    names = astutils.get_name_levels(targets)
    for name, levels in names:
        assignment = rope.base.pynames._Assigned(assigned, levels)
        result[name] = EvaluatedName(assignment=assignment, **kwds)
    return result


class EvaluatedName(rope.base.pynames.EvaluatedName):
    """A `PyName` that will be assigned an expression"""

    def __init__(self, assignment=None, module=None, evaluation= '',
                 lineno=None, eval_type=False):
        """Initialize it

        `evaluation` is a `str` that specifies what to do with the
        `assignment`.  For example for a for object the evaluation is
        '.__iter__().next()'.  That means first call the `__iter__()`
        method and then call `next()` from the resulting object.  As
        another example for with variables it is '.__enter__()'

        """
        self.module = module
        self.assignment = assignment
        self.lineno = lineno
        self.evaluation = evaluation
        self.eval_type = eval_type
        self.pyobject = rope.base.pynames._Inferred(
            self._get_inferred,
            rope.base.pynames._get_concluded_data(module))

    def _get_inferred(self):
        result = rope.base.oi.objectinfer.evaluate_object(
            self.assignment, self.evaluation, self.module, self.lineno)
        if result is not None and self.eval_type:
            result = pyobjects.PyObject(type_=result)
        return result

    def get_object(self):
        return self.pyobject.get()

    def get_definition_location(self):
        return (self.module, self.lineno)

    def invalidate(self):
        """Forget the `PyObject` this `PyName` holds"""
        self.pyobject.set(None)
