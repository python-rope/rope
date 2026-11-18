import operator
import sys
import typing
from operator import itemgetter
from typing import Optional, Tuple

import rope.base.builtins
import rope.base.pynames
import rope.base.pyobjects
from rope.base import (
    arguments,
    ast,
    classfunctions,
    codeanalyze,
    exceptions,
    nameanalyze,
    pyobjects,
    pyobjectsdef,
    pyscopes,
    utils,
    worder,
)

BadIdentifierError = exceptions.BadIdentifierError


def _has_stdlib_import_prelude(module, node):
    """Certify a direct header without loading its imported modules."""
    project = module.pycore.project
    resource = module.get_resource()
    folder = resource.parent if resource is not None else None
    for statement in module.get_ast().body:
        if statement is node:
            return True
        if (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            continue
        if isinstance(statement, ast.Import):
            imported = [alias.name for alias in statement.names]
        elif isinstance(statement, ast.ImportFrom) and not statement.level:
            if any(alias.name == "*" for alias in statement.names):
                return False
            imported = [statement.module]
        else:
            return False
        for name in imported:
            if not name or name.partition(".")[0] not in sys.stdlib_module_names:
                return False
            runtime = sys.modules.get(name)
            if type(runtime) is not type(sys):
                return False
            if name in sys.builtin_module_names:
                continue
            runtime_file = vars(runtime).get("__file__")
            origin = project.find_module(name, folder)
            if origin is None:
                return False
            if origin.is_folder():
                if not origin.has_child("__init__.py"):
                    return False
                origin = origin.get_child("__init__.py")
            if not utils.same_file_path(origin.real_path, runtime_file):
                return False
    return False


def _header_version_guard(module, names, node):
    """Prove a header sys.version_info comparison; return None when unproved.

    The current native bindings and an authenticated standard-library prelude
    supply the runtime. No target package or expression is executed. Other
    guards, scopes and comparison domains keep their existing treatment.
    """
    if module is None:
        return None
    if not all(
        isinstance(statement, (ast.Import, ast.ImportFrom))
        for statement in node.body + node.orelse
    ):
        return None
    test = node.test
    if not (
        isinstance(test, ast.Compare)
        and len(test.ops) == len(test.comparators) == 1
        and isinstance(test.left, ast.Attribute)
        and test.left.attr == "version_info"
        and isinstance(test.left.value, ast.Name)
        and isinstance(test.comparators[0], ast.Tuple)
    ):
        return None
    binding = names.get(test.left.value.id)
    if not (
        isinstance(binding, rope.base.pynames.ImportedModule)
        and binding.importing_module is module
        and binding.module_name == "sys"
        and binding.level == 0
        and _has_stdlib_import_prelude(module, node)
    ):
        return None
    namespace = binding.get_object()
    if not (
        isinstance(namespace, rope.base.builtins.BuiltinModule)
        and namespace.name == "sys"
        and namespace.module is sys
    ):
        return None
    version = namespace.get_attribute("version_info").get_object()
    if not (
        isinstance(version, rope.base.builtins.BuiltinUnknown)
        and version.builtin is sys.version_info
    ):
        return None
    try:
        compared = ast.literal_eval(test.comparators[0])
    except (TypeError, ValueError):
        return None
    if any(
        type(value) is not type(actual)
        for value, actual in zip(compared, version.builtin)
    ):
        return None
    comparison = {
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
    }.get(type(test.ops[0]))
    if comparison is None:
        return None
    return comparison(version.builtin, compared)


class SourceValueScope(pyscopes.TemporaryScope):
    """A call's value overlay, without replacing canonical source binders."""

    def __init__(
        self,
        canonical_scope,
        capture_scope,
        names,
        *,
        branch_context=(),
        source_epoch=None,
    ):
        super().__init__(canonical_scope.pycore, canonical_scope, names)
        self.pyobject = canonical_scope.pyobject
        self.canonical_scope = canonical_scope
        self.capture_scope = capture_scope
        self.branch_context = branch_context
        self.source_epoch = source_epoch

    def lookup(self, name, *, read_node=None):
        if name in self.names:
            return self.names[name]
        if self.source_epoch is not None:
            from rope.base import pynamesdef
            from rope.base.sourcebindings import SourceValueName

            binding = self.canonical_scope.lookup(name)
            if isinstance(binding, pynamesdef.AssignedName):
                return SourceValueName(
                    binding, binding.get_object(read_node=self.source_epoch)
                )
            return binding
        if name in self.canonical_scope.get_names():
            binding = self.canonical_scope.get_names()[name]
            from rope.base import pynamesdef
            from rope.base.sourcebindings import SourceLocalName, SourceValueName

            if (
                isinstance(binding, pynamesdef.ParameterName)
                and binding.assigned_value is not None
                and read_node is not None
            ):
                return SourceValueName(
                    binding,
                    binding.assigned_value.get_object(
                        branch_context=self.branch_context, read_node=read_node
                    ),
                )
            if self.branch_context and isinstance(
                binding, (pynamesdef.AssignedName, SourceLocalName)
            ):
                return SourceValueName(
                    binding,
                    binding.get_object(branch_context=self.branch_context),
                )
            return binding
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
    context = module._get_source_binding_index().context_for_node(node)
    if context is not None and scope.get_kind() != "Temporary":
        scope = context.environment
    parameter_facts = False
    owner = context.structural_scope.pyobject if context is not None else scope.pyobject
    if isinstance(owner, pyobjectsdef.PyFunction):
        owner.get_scope().get_names()
        parameter_facts = any(
            parameter.assigned_value is not None
            for parameter in owner.get_parameters().values()
        )
    if context is not None and (context.branch_context or parameter_facts):
        if isinstance(scope, SourceValueScope):
            if scope.pyobject is context.environment.pyobject:
                branches = dict(scope.branch_context)
                branches.update(context.branch_context)
                scope = SourceValueScope(
                    scope.canonical_scope,
                    scope.capture_scope,
                    scope.names,
                    branch_context=tuple(branches.items()),
                    source_epoch=scope.source_epoch,
                )
        elif scope.get_kind() != "Temporary":
            scope = SourceValueScope(
                scope, scope, {}, branch_context=context.branch_context
            )
    evaluator = StatementEvaluator(scope)
    evaluator.visit(node)
    if (
        evaluator.result is not None
        and evaluator.old_result is not None
        and isinstance(evaluator.old_result.get_object(), pyobjects.SampledValue)
    ):
        from rope.base.sourcebindings import SourceValueName

        evaluator.result = SourceValueName(
            evaluator.result,
            pyobjects.sampled_value(
                evaluator.result.get_object(), evaluator.old_result.get_object()
            ),
        )
    return evaluator.old_result, evaluator.result


def get_callable(pyname):
    """Return the function and receiver selected by a callable value."""
    value = pyname.get_object()
    if isinstance(value, pyobjects.AbstractFunction):
        return value, None
    if "__call__" in value:
        function = value["__call__"].get_object()
        if isinstance(function, pyobjects.AbstractFunction):
            return function, pyname
    return None, None


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
        # Occurrence searches resolve the same (module, offset) many times
        # while the project data does not change.  The memo lives on the
        # PyModule and is stamped with the project-wide data epoch, so any
        # resource invalidation (forget_all_data) retires every entry.
        pymodule = self.module_scope.pyobject
        cache = getattr(getattr(pymodule, "pycore", None), "module_cache", None)
        epoch = getattr(cache, "data_epoch", None)
        memo = getattr(pymodule, "_offset_resolution_memo", None)
        if epoch is not None and memo is not None and memo[0] == epoch:
            try:
                return memo[1][offset]
            except KeyError:
                pass
        result = self._resolve_primary_and_pyname_at(offset)
        if epoch is not None:
            if memo is None or memo[0] != epoch:
                memo = (epoch, {})
                pymodule._offset_resolution_memo = memo
            memo[1][offset] = result
        return result

    def _resolve_primary_and_pyname_at(
        self,
        offset: int,
    ) -> Tuple[Optional[rope.base.pynames.PyName], Optional[rope.base.pynames.PyName]]:
        lineno = self.lines.get_line_number(offset)
        index = self.module_scope.pyobject._get_source_binding_index()
        context = index.context_at(offset)
        holding_scope = context.environment
        structural_scope = context.structural_scope
        parameter = index.binding_for_token(offset)
        if parameter is not None:
            return (None, parameter)
        # function keyword parameter
        if self.worder.is_function_keyword_parameter(offset) and not (
            isinstance(context.source_node, ast.Name)
            and isinstance(context.source_node.ctx, ast.Store)
        ):
            keyword_name = self.worder.get_word_at(offset)
            pyobject = self.get_enclosing_function(offset)
            from rope.base.sourcebindings import SourceLambdaFunction

            if isinstance(pyobject, SourceLambdaFunction):
                parameter_name = None
                if keyword_name in pyobject.get_keyword_param_names():
                    parameter_name = pyobject.get_parameters().get(keyword_name)
                return (None, parameter_name)
            elif isinstance(pyobject, pyobjectsdef.PyFunction):
                parameter_name = None
                if keyword_name in pyobject.get_keyword_param_names():
                    parameter_name = pyobject.get_parameters().get(keyword_name)
                return (None, parameter_name)
            elif isinstance(pyobject, pyobjects.AbstractFunction):
                parameter_name = rope.base.pynames.ParameterName()
                return (None, parameter_name)
            return (None, None)
        # A class data overlay must not replace the imported source symbol.
        if holding_scope.get_kind() == "Class":
            from rope.base import externaldata

            imported = externaldata.import_source_name(
                holding_scope,
                lineno,
                offset,
                self.worder.get_word_at(offset),
                self.worder.get_primary_at(offset),
                self.worder.get_from_module(offset),
                self.worder.is_from_aliased(offset),
                self.worder.is_from_statement_module(offset),
            )
            if imported is not None:
                return (None, imported)
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

    def _get_parameter_at(self, scope, offset):
        if scope.get_kind() != "Function":
            return None
        function = scope.pyobject
        args = function.arguments
        nodes = (
            args.posonlyargs + args.args + args.kwonlyargs + [args.vararg, args.kwarg]
        )
        for node in nodes:
            if node is None:
                continue
            prefix = self.lines.get_line(node.lineno).encode("utf-8")[: node.col_offset]
            start = self.lines.get_line_start(node.lineno) + len(prefix.decode("utf-8"))
            _, end = self.worder.get_word_range(start)
            if start <= offset < end:
                return function.get_parameters()[node.arg]
        return None

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
            pyobject = classfunctions.canonical_function(function_pyname.get_object())
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
        if isinstance(self.scope, SourceValueScope):
            self.result = self.scope.lookup(node.id, read_node=node)
        else:
            self.result = self.scope.lookup(node.id)

    def _IfExp(self, node):
        if isinstance(node.test, ast.Constant):
            self.old_result, self.result = eval_node2(
                self.scope, node.body if node.test.value else node.orelse
            )
            return
        left_primary, left = eval_node2(self.scope, node.body)
        right_primary, right = eval_node2(self.scope, node.orelse)
        same_receiver = left_primary is right_primary or (
            left_primary is not None
            and right_primary is not None
            and left_primary.get_object() is right_primary.get_object()
        )
        if (
            left is not None
            and right is not None
            and left.get_object() is right.get_object()
            and same_receiver
        ):
            self.result = left
            self.old_result = left_primary
        else:
            self.result = rope.base.pynames.UnboundName()

    def _Attribute(self, node):
        pyname = eval_node(self.scope, node.value)
        if pyname is None:
            pyname = rope.base.pynames.UnboundName()
        self.old_result = pyname
        if pyname.get_object() != rope.base.pyobjects.get_unknown():
            try:
                self.result = pyname.get_object()[node.attr]
                self.result = classfunctions.instance_access(
                    pyname, node.attr, self.result, self.scope
                )
                self.result = classfunctions.descriptor_access(
                    pyname, node.attr, self.result, self.scope
                )
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
        primary, func_pyname = eval_node2(self.scope, node.func)
        pyobject = None
        if func_pyname is not None:
            pyobject = func_pyname.get_object()
        if pyobject is None:
            return
        self.old_result = (
            func_pyname if isinstance(pyobject, pyobjects.SampledValue) else primary
        )
        if not isinstance(pyobject, pyobjects.SampledValue):
            for argument in (*node.args, *node.keywords):
                expression = (
                    argument.value
                    if isinstance(argument, (ast.Starred, ast.keyword))
                    else argument
                )
                binding = eval_node(self.scope, expression)
                if binding is not None and isinstance(
                    binding.get_object(), pyobjects.SampledValue
                ):
                    self.old_result = binding
                    break

        if (
            isinstance(pyobject, rope.base.builtins.BuiltinType)
            and len(node.args) == 1
            and not node.keywords
            and not isinstance(node.args[0], ast.Starred)
        ):
            binding = eval_node(self.scope, node.args[0])
            self.result = rope.base.pynames.UnboundName(
                pyobject.type_of(binding.get_object() if binding is not None else None)
            )
            return

        def _get_returned(pyobject):
            args = arguments.create_arguments(
                primary,
                pyobject,
                node,
                self.scope,
            )
            modeled = rope.base.builtins.infer_runtime_call(pyobject, args)
            if modeled is not None:
                return modeled
            return pyobject.get_returned_object(args)

        if isinstance(pyobject, pyobjects.SampledValue) and isinstance(
            pyobject.representative, pyobjects.AbstractFunction
        ):
            self.result = rope.base.pynames.UnboundName(
                _get_returned(pyobject.representative)
            )
            return

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
                if rope.base.builtins.BuiltinType.is_constructor(new_function) or (
                    isinstance(new_function, rope.base.pyobjects.PyFunction)
                    and new_function.get_kind() != "classmethod"
                ):
                    args = arguments.create_arguments(
                        None, new_function, node, self.scope, ignore_instance=True
                    )
                    args = arguments.MixedArguments(
                        rope.base.pynames.UnboundName(pyobject), args, self.scope
                    )
                    self.result = rope.base.pynames.UnboundName(
                        new_function.get_returned_object(args)
                    )
                    return
                result = _get_returned(new_function)
            if result is None or result == rope.base.pyobjects.get_unknown():
                result = rope.base.pyobjects.PyObject(pyobject)
            self.result = rope.base.pynames.UnboundName(pyobject=result)
            return

        pyfunction, receiver = get_callable(func_pyname)
        if pyfunction is not None:
            if receiver is None:
                result = _get_returned(pyfunction)
            else:
                args = arguments.create_arguments(
                    None, pyfunction, node, self.scope, ignore_instance=True
                )
                args = arguments.bind_method(
                    receiver,
                    pyfunction,
                    args,
                    self.scope,
                    owner=receiver.get_object().get_type(),
                )
                result = pyfunction.get_returned_object(args)
            self.result = rope.base.pynames.UnboundName(pyobject=result)

    def _Str(self, node):
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.LiteralString(node.s)
        )

    def _Num(self, node):
        type_name = type(node.n).__name__
        self.result = self._get_builtin_name(type_name)

    def _JoinedStr(self, node):
        self.result = self._get_builtin_name("str")

    def _Constant(self, node):
        if isinstance(node.value, str):
            self.result = rope.base.pynames.UnboundName(
                rope.base.builtins.LiteralString(node.value)
            )
            return
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
        left = self._get_object_for_node(node.left)
        if isinstance(node.op, ast.BitOr):
            right = self._get_object_for_node(node.right)
            parts = (node.left, node.right)
            values = (left, right)
            if any(
                isinstance(
                    value, (pyobjects.AbstractClass, rope.base.builtins.GenericAlias)
                )
                for value in values
            ):
                from rope.base.oi.type_hinting.utils import _hint_value, union_type

                alternatives = tuple(
                    (
                        rope.base.builtins._runtime_class(type(None))
                        if isinstance(part, ast.Constant) and part.value is None
                        else _hint_value(value)
                    )
                    for part, value in zip(parts, values)
                )
                self.result = rope.base.pynames.UnboundName(union_type(alternatives))
                return
        self.result = rope.base.pynames.UnboundName(left)

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
        entries = {}
        for key, value in zip(node.keys, node.values):
            if key is None:
                entries = None
                break
            key_object = self._get_object_for_node(key)
            if not isinstance(key_object, rope.base.builtins.LiteralString):
                entries = None
                break
            binding = eval_node(self.scope, value)
            if binding is None:
                entries = None
                break
            entries[key_object.value] = rope.base.pynames.UnboundName(
                binding.get_object()
            )
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.LiteralDict(keys, values, entries)
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
        binding_scope = module._get_source_binding_index().comprehension_scope(node)
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
        objects = [self._get_object_for_node(stmt) for stmt in node.elts]
        self.result = rope.base.pynames.UnboundName(
            pyobject=rope.base.builtins.get_tuple(*objects)
        )

    def _get_object_for_node(self, stmt):
        pyname = eval_node(self.scope, stmt)
        pyobject = None
        if pyname is not None:
            pyobject = pyname.get_object()
        return pyobject

    def _Subscript(self, node):
        receiver = eval_node(self.scope, node.value)
        if receiver is None:
            return
        self.old_result = receiver
        value = receiver.get_object()
        is_class = isinstance(value, pyobjects.AbstractClass)
        owner = value.get_metaclass() if is_class else value.get_type()
        if is_class and not isinstance(owner, pyobjects.AbstractClass):
            self.result = rope.base.pynames.UnboundName(owner)
            return
        if rope.base.builtins._runtime_unpack(value) is not None:
            # PEP 646: an explicit ``Unpack[Ts]`` evaluates to the typing
            # alias carrying the parameter, mirroring the runtime's
            # ``_GenericAlias``; the generic-alias validation recognizes
            # the form through its origin.
            key = node.slice.value if isinstance(node.slice, ast.Index) else node.slice
            if isinstance(key, ast.Starred):
                # The runtime rejects starred subscripting of ``Unpack``;
                # rope models that failure as no result.
                return
            target = eval_node(self.scope, key)
            if target is None:
                return
            module = self.scope.pyobject.get_module()
            self.result = rope.base.pynames.UnboundName(
                rope.base.builtins.GenericAlias(
                    value, (target.get_object(),), module.pycore.project, True
                )
            )
            return
        if isinstance(owner, rope.base.builtins.Tuple):
            try:
                if isinstance(node.slice, ast.Slice):
                    bounds = (
                        ast.literal_eval(bound) if bound is not None else None
                        for bound in (
                            node.slice.lower,
                            node.slice.upper,
                            node.slice.step,
                        )
                    )
                    result = rope.base.builtins.get_tuple(
                        *owner.get_holding_objects()[slice(*bounds)]
                    )
                else:
                    key = ast.literal_eval(node.slice)
                    result = owner.get_item(key) if isinstance(key, int) else None
            except (ValueError, TypeError):
                result = None
            self.result = rope.base.pynames.UnboundName(result)
            return
        if "__getitem__" in owner:
            called, callable_receiver = get_callable(owner["__getitem__"])
            descriptor_owner = owner
        elif is_class and "__class_getitem__" in value:
            called, callable_receiver = get_callable(value["__class_getitem__"])
            descriptor_owner = value
        else:
            return
        if called is None:
            return
        if callable_receiver is not None:
            receiver = callable_receiver
            descriptor_owner = receiver.get_object().get_type()
        key = node.slice.value if isinstance(node.slice, ast.Index) else node.slice
        starred = isinstance(key, ast.Starred)
        if starred:
            # PEP 646: the starred subscription syntax exists only at the
            # expression level; evaluate the target so the typing alias
            # validation receives the unpack fact, not the star node.
            key = key.value
        args = arguments.Arguments([key], self.scope, called)
        args = arguments.bind_method(
            receiver, called, args, self.scope, owner=descriptor_owner
        )
        if starred:
            target = eval_node(self.scope, key)
            if target is None or not rope.base.builtins._is_runtime_class(
                target.get_object().get_type(), typing.TypeVarTuple
            ):
                # Runtime rejects every non-TypeVarTuple starred subscript;
                # rope models that failure as no result.
                return
            args = arguments.bind_method(
                receiver,
                called,
                arguments.ObjectArguments(
                    [
                        rope.base.pynames.UnboundName(
                            rope.base.builtins.UnpackedTypeVarTuple(target.get_object())
                        )
                    ]
                ),
                self.scope,
                owner=descriptor_owner,
            )
        self.result = rope.base.pynames.UnboundName(called.get_returned_object(args))

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
            arguments_ = arguments.Arguments(args, self.scope, called)
            self.result = rope.base.pynames.UnboundName(
                pyobject=called.get_returned_object(arguments_)
            )

    def _Lambda(self, node):
        module = self.scope.pyobject.get_module()
        function = module._get_source_binding_index().callable_for_node(node)
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
