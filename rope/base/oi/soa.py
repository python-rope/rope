import rope.base.ast
import rope.base.oi.soi
import rope.base.pynames
from rope.base import arguments, classfunctions, evaluate, nameanalyze, pyobjects


def analyze_module(
    pycore,
    pymodule,
    should_analyze,
    search_subscopes,
    followed_calls,
    *,
    visitor_factory=None,
):
    """Analyze `pymodule` for static object inference

    Analyzes scopes for collecting object information.  The analysis
    starts from inner scopes.

    """
    _analyze_node(
        pycore,
        pymodule,
        should_analyze,
        search_subscopes,
        followed_calls,
        visitor_factory,
    )


def _analyze_node(
    pycore, pydefined, should_analyze, search_subscopes, followed_calls, visitor_factory
):
    if search_subscopes(pydefined):
        for scope in pydefined.get_scope().get_scopes():
            _analyze_node(
                pycore,
                scope.pyobject,
                should_analyze,
                search_subscopes,
                followed_calls,
                visitor_factory,
            )
    if should_analyze(pydefined):
        new_followed_calls = max(0, followed_calls - 1)
        return_true = lambda pydefined: True
        return_false = lambda pydefined: False

        def _follow(pyfunction):
            _analyze_node(
                pycore,
                pyfunction,
                return_true,
                return_false,
                new_followed_calls,
                visitor_factory,
            )

        factory = SOAVisitor if visitor_factory is None else visitor_factory
        visitor = factory(pycore, pydefined, _follow if followed_calls else None)
        for child in rope.base.ast.iter_child_nodes(pydefined.get_ast()):
            visitor.visit(child)


class SOAVisitor(rope.base.ast.RopeNodeVisitor):
    def __init__(self, pycore, pydefined, follow_callback=None):
        self.pycore = pycore
        self.pymodule = pydefined.get_module()
        self.scope = pydefined.get_scope()
        self.follow = follow_callback

    def _FunctionDef(self, node):
        pass

    def _ClassDef(self, node):
        pass

    def _Call(self, node):
        for child in rope.base.ast.iter_child_nodes(node):
            self.visit(child)
        primary, pyname = evaluate.eval_node2(self.scope, node.func)
        if pyname is None:
            return
        pyfunction = pyname.get_object()
        if isinstance(pyfunction, pyobjects.AbstractFunction):
            args = arguments.create_arguments(primary, pyfunction, node, self.scope)
        elif isinstance(pyfunction, pyobjects.PyClass):
            pyclass = pyfunction
            if "__init__" in pyfunction:
                pyfunction = pyfunction["__init__"].get_object()
            pyname = rope.base.pynames.UnboundName(pyobjects.PyObject(pyclass))
            args = self._args_with_self(primary, pyname, pyfunction, node)
        elif "__call__" in pyfunction:
            pyfunction = pyfunction["__call__"].get_object()
            args = self._args_with_self(primary, pyname, pyfunction, node)
        else:
            return
        self._call(pyfunction, args)

    def _args_with_self(self, primary, self_pyname, pyfunction, node):
        base_args = arguments.create_arguments(
            primary, pyfunction, node, self.scope, ignore_instance=True
        )
        return arguments.MixedArguments(self_pyname, base_args, self.scope)

    def _call(self, pyfunction, args):
        if isinstance(pyfunction, classfunctions.BoundFunction):
            args = pyfunction.bind_arguments(args)
            pyfunction = pyfunction.function
        if isinstance(pyfunction, pyobjects.PyFunction):
            if self.follow is not None:
                before = self._parameter_objects(pyfunction)
            self.pycore.object_info.function_called(
                pyfunction, args.get_arguments(pyfunction.get_param_names(False))
            )
            pyfunction._set_parameter_pyobjects(None)
            if self.follow is not None:
                after = self._parameter_objects(pyfunction)
                if after != before:
                    self.follow(pyfunction)
        # XXX: Maybe we should not call every builtin function
        if isinstance(pyfunction, rope.base.builtins.BuiltinFunction):
            pyfunction.get_returned_object(args)

    def _parameter_objects(self, pyfunction):
        return [
            pyfunction.get_parameter(i)
            for i in range(len(pyfunction.get_param_names(False)))
        ]

    def _AnnAssign(self, node):
        for child in rope.base.ast.iter_child_nodes(node):
            self.visit(child)
        visitor = _SOAAssignVisitor()
        nodes = []

        visitor.visit(node.target)
        nodes.extend(visitor.nodes)

        self._evaluate_assign_value(node, nodes, type_hint=node.annotation)

    def _Assign(self, node):
        for child in rope.base.ast.iter_child_nodes(node):
            self.visit(child)
        visitor = _SOAAssignVisitor()
        nodes = []
        for child in node.targets:
            visitor.visit(child)
            nodes.extend(visitor.nodes)
        self._evaluate_assign_value(node, nodes)

    def _operator_effects(self, node, left, right, *, inplace=False):
        for child in rope.base.ast.iter_child_nodes(node):
            self.visit(child)
        operation = {
            rope.base.ast.Add: "add",
            rope.base.ast.Sub: "sub",
            rope.base.ast.Mult: "mul",
            rope.base.ast.MatMult: "matmul",
            rope.base.ast.Div: "truediv",
            rope.base.ast.FloorDiv: "floordiv",
            rope.base.ast.Mod: "mod",
            rope.base.ast.Pow: "pow",
            rope.base.ast.LShift: "lshift",
            rope.base.ast.RShift: "rshift",
            rope.base.ast.BitOr: "or",
            rope.base.ast.BitXor: "xor",
            rope.base.ast.BitAnd: "and",
        }[type(node.op)]
        left = evaluate.eval_node(self.scope, left)
        right = evaluate.eval_node(self.scope, right)
        effects = [
            (left, right, "__" + operation + "__"),
            (right, left, "__r" + operation + "__"),
        ]
        if self._reflected_first(left, right, effects[1][2]):
            effects.reverse()
        if inplace:
            effects.insert(0, (left, right, "__i" + operation + "__"))
        # Python tries each method in order and falls back only when one is
        # missing or returns NotImplemented.
        for receiver, operand, name in effects:
            if receiver is None or name not in receiver.get_object():
                continue
            result = self._protocol_call(receiver, name, [operand])
            if not self._may_be_not_implemented(result):
                break

    @staticmethod
    def _reflected_first(left, right, name):
        """A right operand of a proper subclass overriding the method goes first."""
        if left is None or right is None:
            return False
        left_type = left.get_object().get_type()
        right_type = right.get_object().get_type()
        if (
            not isinstance(left_type, pyobjects.PyClass)
            or not isinstance(right_type, pyobjects.PyClass)
            or left_type is right_type
        ):
            return False
        from rope.base.pyobjectsdef import _inheritance_order

        if left_type not in _inheritance_order(right_type):
            return False
        reflected = right_type.get_attributes().get(name)
        inherited = left_type.get_attributes().get(name)
        return reflected is not None and (
            inherited is None or reflected.get_object() is not inherited.get_object()
        )

    @staticmethod
    def _may_be_not_implemented(result):
        if result is None:
            return True
        value = result.get_object()
        if value is None or value == pyobjects.get_unknown():
            return True
        return value.get_type() is rope.base.builtins._runtime_class(
            type(NotImplemented)
        )

    def _AugAssign(self, node):
        self._operator_effects(node, node.target, node.value, inplace=True)

    def _BinOp(self, node):
        self._operator_effects(node, node.left, node.right)

    def _protocol_call(self, receiver, name, operands=()):
        if receiver is None or name not in receiver.get_object():
            return None
        function = receiver.get_object()[name].get_object()
        args = arguments.ObjectArguments([receiver, *operands])
        self._call(function, args)
        if isinstance(function, pyobjects.AbstractFunction):
            result = function.get_returned_object(args)
            if result is not None:
                return rope.base.pynames.UnboundName(result)

    def _Compare(self, node):
        for child in rope.base.ast.iter_child_nodes(node):
            self.visit(child)
        left = evaluate.eval_node(self.scope, node.left)
        for operation, expression in zip(node.ops, node.comparators):
            right = evaluate.eval_node(self.scope, expression)
            if isinstance(operation, (rope.base.ast.In, rope.base.ast.NotIn)):
                if right is not None and "__contains__" in right.get_object():
                    self._protocol_call(right, "__contains__", [left])
                else:
                    iterator = self._protocol_call(right, "__iter__")
                    if iterator is not None:
                        # Rope's builtin iterators model `next`, not `__next__`.
                        item = self._protocol_call(
                            iterator,
                            (
                                "__next__"
                                if "__next__" in iterator.get_object()
                                else "next"
                            ),
                        )
                    else:
                        item = self._protocol_call(
                            right,
                            "__getitem__",
                            [
                                rope.base.pynames.UnboundName(
                                    pyobjects.PyObject(
                                        rope.base.builtins.builtins["int"].get_object()
                                    )
                                )
                            ],
                        )
                    self._protocol_call(item, "__eq__", [left])
                    self._protocol_call(left, "__eq__", [item])
            else:
                names = {
                    rope.base.ast.Eq: ("__eq__", "__eq__"),
                    rope.base.ast.NotEq: ("__ne__", "__ne__"),
                    rope.base.ast.Lt: ("__lt__", "__gt__"),
                    rope.base.ast.LtE: ("__le__", "__ge__"),
                    rope.base.ast.Gt: ("__gt__", "__lt__"),
                    rope.base.ast.GtE: ("__ge__", "__le__"),
                }.get(type(operation))
                if names is not None:
                    self._protocol_call(left, names[0], [right])
                    self._protocol_call(right, names[1], [left])
            left = right

    def _evaluate_assign_value(self, node, nodes, type_hint=None):
        for target, levels in nodes:
            instance = evaluate.eval_node(self.scope, target.value)
            if isinstance(target, rope.base.ast.Attribute):
                operation = "__setattr__"
                key = rope.base.pynames.UnboundName(
                    rope.base.builtins.LiteralString(target.attr)
                )
            else:
                operation = "__setitem__"
                key = evaluate.eval_node(self.scope, target.slice)
            args_pynames = [key]
            value = rope.base.oi.soi._infer_assignment(
                rope.base.pynames.AssignmentValue(
                    node.value, levels, type_hint=type_hint
                ),
                self.pymodule,
            )
            args_pynames.append(rope.base.pynames.UnboundName(value))
            if instance is not None and value is not None:
                pyobject = instance.get_object()
                if operation == "__setattr__" and isinstance(
                    pyobject, pyobjects.AbstractClass
                ):
                    # Assigning a class attribute calls the metaclass method.
                    pyobject = pyobject.get_metaclass()
                if pyobject is not None and operation in pyobject:
                    pyfunction = pyobject[operation].get_object()
                    args = arguments.ObjectArguments([instance] + args_pynames)
                    self._call(pyfunction, args)
                # IDEA: handle `__setslice__`, too


class _SOAAssignVisitor(nameanalyze._NodeNameCollector):
    def __init__(self):
        super().__init__()
        self.nodes = []

    def _added(self, node, levels):
        if isinstance(node, rope.base.ast.Attribute) or (
            isinstance(node, rope.base.ast.Subscript)
            and isinstance(node.slice, (rope.base.ast.Index, rope.base.ast.expr))
        ):
            self.nodes.append((node, levels))
