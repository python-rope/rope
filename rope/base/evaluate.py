from operator import itemgetter
from typing import Optional, Tuple

import rope.base.builtins
import rope.base.pynames
import rope.base.pyobjects
from rope.base import (
    arguments,
    ast,
    codeanalyze,
    exceptions,
    nameanalyze,
    pyobjects,
    pyobjectsdef,
    pyscopes,
    worder,
)

BadIdentifierError = exceptions.BadIdentifierError


class SourceValueScope(pyscopes.TemporaryScope):
    """A call's value overlay, without replacing canonical source binders."""

    def __init__(self, canonical_scope, capture_scope, names):
        super().__init__(canonical_scope.pycore, canonical_scope, names)
        self.pyobject = canonical_scope.pyobject
        self.canonical_scope = canonical_scope
        self.capture_scope = capture_scope

    def lookup(self, name):
        if name in self.names:
            return self.names[name]
        if name in self.canonical_scope.get_names():
            return self.canonical_scope.get_names()[name]
        return self.capture_scope.lookup(name)

    def _propagated_lookup(self, name):
        return self.lookup(name)


def eval_location(pymodule, offset):
    """Find the pyname at the offset"""
    return eval_location2(pymodule, offset)[1]


def eval_location2(pymodule, offset):
    """Find the primary and pyname at offset"""
    pyname_finder = ScopeNameFinder(pymodule)
    return pyname_finder.get_primary_and_pyname_at(offset)


def eval_node(scope, node):
    """Evaluate a `ast.AST` node and return a PyName

    Return `None` if the expression cannot be evaluated.
    """
    return eval_node2(scope, node)[1]


def eval_node2(scope, node):
    module = scope.pyobject.get_module()
    context = module.get_source_binding_index().context_for_node(node)
    if context is not None and scope.get_kind() != "Temporary":
        scope = context.environment
    evaluator = StatementEvaluator(scope)
    evaluator.visit(node)
    return evaluator.old_result, evaluator.result


def eval_str(holding_scope, name):
    return eval_str2(holding_scope, name)[1]


def eval_str2(holding_scope, name):
    try:
        # parenthesizing for handling cases like 'a_var.\nattr'
        node = ast.parse("(%s)" % name)
    except SyntaxError:
        raise BadIdentifierError("Not a resolvable python identifier selected.")
    return eval_node2(holding_scope, node)


class ScopeNameFinder:
    def __init__(self, pymodule):
        self.module_scope = pymodule.get_scope()
        self.lines = pymodule.lines
        self.worder = worder.Worder(pymodule.source_code, True)

    def _is_defined_in_class_body(self, holding_scope, offset, lineno):
        if (
            lineno == holding_scope.get_start()
            and holding_scope.parent is not None
            and holding_scope.parent.get_kind() == "Class"
            and self.worder.is_a_class_or_function_name_in_header(offset)
        ):
            return True
        if (
            lineno != holding_scope.get_start()
            and holding_scope.get_kind() == "Class"
            and self.worder.is_name_assigned_in_class_body(offset)
        ):
            return True
        return False

    def _is_function_name_in_function_header(self, scope, offset, lineno):
        return (
            scope.get_start() <= lineno <= scope.get_body_start()
            and scope.get_kind() == "Function"
            and self.worder.is_a_class_or_function_name_in_header(offset)
        )

    def get_pyname_at(self, offset):
        return self.get_primary_and_pyname_at(offset)[1]

    def get_primary_and_pyname_at(
        self,
        offset: int,
    ) -> Tuple[Optional[rope.base.pynames.PyName], Optional[rope.base.pynames.PyName]]:
        lineno = self.lines.get_line_number(offset)
        index = self.module_scope.pyobject.get_source_binding_index()
        context = index.context_at(offset)
        holding_scope = context.environment
        structural_scope = context.structural_scope
        parameter = index.binding_for_token(offset)
        if parameter is not None:
            return (None, parameter)
        # function keyword parameter
        if self.worder.is_function_keyword_parameter(offset):
            keyword_name = self.worder.get_word_at(offset)
            pyobject = self.get_enclosing_function(offset)
            from rope.base.sourcebindings import SourceLambdaFunction

            if isinstance(pyobject, SourceLambdaFunction):
                parameter_name = None
                if keyword_name in pyobject.get_keyword_param_names():
                    parameter_name = pyobject.get_parameters().get(keyword_name)
                return (None, parameter_name)
            elif isinstance(pyobject, pyobjectsdef.PyFunction):
                parameter_name = pyobject.get_parameters().get(keyword_name, None)
                return (None, parameter_name)
            elif isinstance(pyobject, pyobjects.AbstractFunction):
                parameter_name = rope.base.pynames.ParameterName()
                return (None, parameter_name)
        # class body
        if self._is_defined_in_class_body(structural_scope, offset, lineno):
            class_scope = structural_scope
            if lineno == structural_scope.get_start():
                class_scope = structural_scope.parent
            name = self.worder.get_primary_at(offset).strip()
            try:
                return (None, class_scope.pyobject[name])
            except rope.base.exceptions.AttributeNotFoundError:
                return (None, None)
        # function header
        if self._is_function_name_in_function_header(structural_scope, offset, lineno):
            name = self.worder.get_primary_at(offset).strip()
            return (None, structural_scope.parent[name])
        # module in a from statement or an imported name that is aliased
        if self.worder.is_from_statement_module(
            offset
        ) or self.worder.is_import_statement_aliased_module(offset):
            module = self.worder.get_primary_at(offset)
            module_pyname = self._find_module(module)
            return (None, module_pyname)
        if self.worder.is_from_aliased(offset):
            name = self.worder.get_from_aliased(offset)
        else:
            name = self.worder.get_primary_at(offset)
        primary, pyname = eval_str2(holding_scope, name)
        from rope.base.sourcebindings import SourceValueName

        if isinstance(pyname, SourceValueName):
            pyname = pyname.source_pyname
        return primary, pyname

    def get_enclosing_function(self, offset):
        module = self.module_scope.pyobject
        lines = codeanalyze.ASTLinesAdapter(module.source_code)
        for node in ast.walk(module.get_ast()):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg is None:
                    continue
                start, _ = lines[keyword]
                if start <= offset < start + len(keyword.arg):
                    return self._callable_object(
                        eval_node(self.module_scope, node.func)
                    )
        function_parens = self.worder.find_parens_start_from_inside(offset)
        try:
            function_pyname = self.get_pyname_at(function_parens - 1)
        except BadIdentifierError:
            function_pyname = None
        return self._callable_object(function_pyname)

    @staticmethod
    def _callable_object(function_pyname):
        if function_pyname is not None:
            pyobject = function_pyname.get_object()
            if isinstance(pyobject, pyobjects.AbstractFunction):
                return pyobject
            elif (
                isinstance(pyobject, pyobjects.AbstractClass) and "__init__" in pyobject
            ):
                return pyobject["__init__"].get_object()
            elif "__call__" in pyobject:
                return pyobject["__call__"].get_object()
        return None

    def _find_module(self, module_name):
        dots = 0
        while module_name[dots] == ".":
            dots += 1
        return rope.base.pynames.ImportedModule(
            self.module_scope.pyobject, module_name[dots:], dots
        )


class StatementEvaluator(ast.RopeNodeVisitor):
    def __init__(self, scope):
        self.scope = scope
        self.result = None
        self.old_result = None

    def _Name(self, node):
        self.result = self.scope.lookup(node.id)

    def _Attribute(self, node):
        pyname = eval_node(self.scope, node.value)
        if pyname is None:
            pyname = rope.base.pynames.UnboundName()
        self.old_result = pyname
        if pyname.get_object() != rope.base.pyobjects.get_unknown():
            try:
                self.result = pyname.get_object()[node.attr]
                from rope.base.sourcebindings import (
                    SourceLambdaFunction,
                    SourceValueName,
                    source_lambda_attribute_value,
                )

                selected = source_lambda_attribute_value(pyname, self.result)
                if selected is not None:
                    self.result = selected
                function = self.result.get_object()
                if isinstance(function, SourceLambdaFunction):
                    receiver = function.descriptor_receiver(pyname, self.result)
                    if receiver is not None:
                        self.result = SourceValueName(
                            self.result, function.bind_receiver(receiver)
                        )
            except exceptions.AttributeNotFoundError:
                self.result = None

    def _Call(self, node):
        primary, pyobject = self._get_primary_and_object_for_node(node.func)
        if pyobject is None:
            return

        def _get_returned(pyobject):
            args = arguments.create_arguments(primary, pyobject, node, self.scope)
            return pyobject.get_returned_object(args)

        if isinstance(pyobject, rope.base.pyobjects.AbstractClass):
            from rope.base.sourcebindings import SourceLambdaFunction

            if (
                isinstance(pyobject, rope.base.builtins.BuiltinClass)
                and pyobject.builtin in (staticmethod, classmethod)
                and node.args
            ):
                function = eval_node(self.scope, node.args[0])
                if function is not None and isinstance(
                    function.get_object(), SourceLambdaFunction
                ):
                    self.result = rope.base.pynames.UnboundName(
                        function.get_object().as_descriptor(pyobject.builtin.__name__)
                    )
                    return
            result = None
            if "__new__" in pyobject:
                new_function = pyobject["__new__"].get_object()
                result = _get_returned(new_function)
            if result is None or result == rope.base.pyobjects.get_unknown():
                result = rope.base.pyobjects.PyObject(pyobject)
            self.result = rope.base.pynames.UnboundName(pyobject=result)
            return

        pyfunction = None
        if isinstance(pyobject, rope.base.pyobjects.AbstractFunction):
            pyfunction = pyobject
        elif "__call__" in pyobject:
            pyfunction = pyobject["__call__"].get_object()
            from rope.base.sourcebindings import SourceLambdaFunction

            if isinstance(pyfunction, SourceLambdaFunction):
                pyfunction = pyfunction.bind_receiver(
                    rope.base.pynames.UnboundName(pyobject)
                )
        if pyfunction is not None:
            self.result = rope.base.pynames.UnboundName(
                pyobject=_get_returned(pyfunction)
            )

    def _Str(self, node):
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_str()
        )

    def _Num(self, node):
        type_name = type(node.n).__name__
        self.result = self._get_builtin_name(type_name)

    def _Constant(self, node):
        type_name = type(node.value).__name__
        try:
            self.result = self._get_builtin_name(type_name)
        except exceptions.AttributeNotFoundError:
            # XXX: Right way to fix this is to add missing NoneType to builtins?
            pass

    def _get_builtin_name(self, type_name):
        pytype = rope.base.builtins.builtins[type_name].get_object()
        return rope.base.pynames.UnboundName(rope.base.pyobjects.PyObject(pytype))

    def _BinOp(self, node):
        self.result = rope.base.pynames.UnboundName(
            self._get_object_for_node(node.left)
        )

    def _BoolOp(self, node):
        pyobject = self._get_object_for_node(node.values[0])
        if pyobject is None:
            pyobject = self._get_object_for_node(node.values[1])
        self.result = rope.base.pynames.UnboundName(pyobject)

    def _Repr(self, node):
        self.result = self._get_builtin_name("str")

    def _UnaryOp(self, node):
        self.result = rope.base.pynames.UnboundName(
            self._get_object_for_node(node.operand)
        )

    def _Compare(self, node):
        self.result = self._get_builtin_name("bool")

    def _Dict(self, node):
        keys = None
        values = None
        if node.keys and node.keys[0]:
            keys, values = next(
                iter(filter(itemgetter(0), zip(node.keys, node.values))), (None, None)
            )
            if keys:
                keys = self._get_object_for_node(keys)
            if values:
                values = self._get_object_for_node(values)
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_dict(keys, values)
        )

    def _List(self, node):
        holding = None
        if node.elts:
            holding = self._get_object_for_node(node.elts[0])
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_list(holding)
        )

    def _ListComp(self, node):
        pyobject = self._what_does_comprehension_hold(node)
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_list(pyobject)
        )

    def _GeneratorExp(self, node):
        pyobject = self._what_does_comprehension_hold(node)
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_iterator(pyobject)
        )

    def _SetComp(self, node):
        pyobject = self._what_does_comprehension_hold(node)
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_set(pyobject)
        )

    def _DictComp(self, node):
        scope = self._make_comprehension_scope(node)
        key = eval_node(scope, node.key)
        value = eval_node(scope, node.value)
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_dict(
                key.get_object() if key is not None else None,
                value.get_object() if value is not None else None,
            )
        )

    def _what_does_comprehension_hold(self, node):
        scope = self._make_comprehension_scope(node)
        pyname = eval_node(scope, node.elt)
        return pyname.get_object() if pyname is not None else None

    def _make_comprehension_scope(self, node):
        module = self.scope.pyobject.get_module()
        binding_scope = module.get_source_binding_index().comprehension_scope(node)
        if binding_scope is not None:
            if self.scope.get_kind() == "Temporary":
                values = {
                    name: rope.base.pynames.UnboundName()
                    for name in binding_scope.get_names()
                }
                value_scope = SourceValueScope(binding_scope, self.scope, values)
                for number, generator in enumerate(node.generators):
                    entry = self.scope if number == 0 else value_scope
                    iterator = eval_node(entry, generator.iter)
                    if iterator is None:
                        continue
                    iterator_scope = pyscopes.TemporaryScope(
                        entry.pycore, entry, {"__rope_iterable": iterator}
                    )
                    element = eval_str(
                        iterator_scope, "__rope_iterable.__iter__().next()"
                    )
                    if element is None:
                        continue
                    for name, levels in nameanalyze.get_name_levels(generator.target):
                        value = element
                        for level in levels:
                            element_type = value.get_object().get_type()
                            if isinstance(element_type, rope.base.builtins.Tuple):
                                holdings = element_type.get_holding_objects()
                                value = (
                                    rope.base.pynames.UnboundName(holdings[level])
                                    if level < len(holdings)
                                    and holdings[level] is not None
                                    else None
                                )
                            else:
                                item_scope = pyscopes.TemporaryScope(
                                    entry.pycore, entry, {"__rope_element": value}
                                )
                                value = eval_str(
                                    item_scope, "__rope_element[%s]" % level
                                )
                            if value is None:
                                break
                        if value is not None:
                            values[name] = value
                return value_scope
            return binding_scope
        scope = self.scope
        module = scope.pyobject.get_module()
        names = {}
        for comp in node.generators:
            new_names = _get_evaluated_names(
                comp.target, comp.iter, module, ".__iter__().next()", node.lineno
            )
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
            pyobject=rope.base.builtins.get_tuple(*objects)
        )

    def _get_object_for_node(self, stmt):
        pyname = eval_node(self.scope, stmt)
        pyobject = None
        if pyname is not None:
            pyobject = pyname.get_object()
        return pyobject

    def _get_primary_and_object_for_node(self, stmt):
        primary, pyname = eval_node2(self.scope, stmt)
        pyobject = None
        if pyname is not None:
            pyobject = pyname.get_object()
        return primary, pyobject

    def _Subscript(self, node):
        if isinstance(node.slice, ast.Index):
            self._call_function(node.value, "__getitem__", [node.slice.value])
        elif isinstance(node.slice, ast.Slice):
            self._call_function(node.value, "__getitem__", [node.slice])
        elif isinstance(node.slice, ast.expr):
            self._call_function(node.value, "__getitem__", [node.value])

    def _Slice(self, node):
        self.result = self._get_builtin_name("slice")

    def _call_function(self, node, function_name, other_args=None):
        pyname = eval_node(self.scope, node)
        if pyname is not None:
            pyobject = pyname.get_object()
        else:
            return
        if function_name in pyobject:
            called = pyobject[function_name].get_object()
            if not called or not isinstance(called, pyobjects.AbstractFunction):
                return
            args = [node]
            if other_args:
                args += other_args
            arguments_ = arguments.Arguments(args, self.scope)
            self.result = rope.base.pynames.UnboundName(
                pyobject=called.get_returned_object(arguments_)
            )

    def _Lambda(self, node):
        module = self.scope.pyobject.get_module()
        function = module.get_source_binding_index().callable_for_node(node)
        if function is None:
            function = rope.base.builtins.Lambda(node, self.scope)
        elif self.scope.get_kind() == "Temporary":
            function = function.bind_creation_scope(self.scope)
        self.result = rope.base.pynames.UnboundName(pyobject=function)


def _get_evaluated_names(targets, assigned, module, evaluation, lineno):
    result = {}
    for name, levels in nameanalyze.get_name_levels(targets):
        assignment = rope.base.pynames.AssignmentValue(assigned, levels, evaluation)
        # XXX: this module should not access `rope.base.pynamesdef`!
        pyname = rope.base.pynamesdef.AssignedName(lineno, module)
        pyname.assignments.append(assignment)
        result[name] = pyname
    return result
