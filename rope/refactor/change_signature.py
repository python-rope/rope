import contextlib
import copy
import importlib
import sys
from functools import partial
from keyword import iskeyword

import rope.base.exceptions
from rope.base import (
    ast,
    builtins,
    classfunctions,
    codeanalyze,
    evaluate,
    pynames,
    pyobjects,
    simplify,
    taskhandle,
    utils,
    worder,
)
from rope.base.change import ChangeContents, ChangeSet
from rope.base.oi import soa
from rope.refactor import functionutils, occurrences, sourceutils


def _fstring_quotes(pymodule):
    """Return ``(start, end, quote)`` for every f-string of `pymodule`."""
    index = pymodule.get_source_binding_index()
    result = []
    for candidate in ast.walk(pymodule.get_ast()):
        if isinstance(candidate, ast.JoinedStr):
            first, last = index._span(candidate)
            text = pymodule.source_code[first:last].lstrip("rRfFbBuU")
            quote = text[:3] if text[:3] in ("'''", '"""') else text[:1]
            result.append((first, last, quote))
    return result


def _enclosing_fstring_quote(fstrings, start, end):
    """Return the quote of the innermost f-string around ``[start, end)``."""
    enclosing = [
        (last - first, quote)
        for first, last, quote in fstrings
        if first <= start and end <= last
    ]
    return min(enclosing)[1] if enclosing else None


def _replacement_field_text(expression, quote):
    """Render `expression` for a replacement field before PEP 701.

    Before Python 3.12 an f-string replacement field cannot contain its
    enclosing quote or a backslash.  String literals anywhere in the
    expression are written with the other quote character; an expression
    that still cannot be written there is refused.
    """
    text = ast.unparse(expression)
    if quote is None or sys.version_info >= (3, 12):
        return text
    if quote not in text and "\\" not in text:
        return text
    other = '"' if quote[0] == "'" else "'"
    literals = {}

    class _Requote(ast.NodeTransformer):
        def visit_JoinedStr(self, node):
            return node

        def visit_Constant(self, node):
            value = node.value
            if (
                not isinstance(value, str)
                or other in value
                or "\\" in value
                or not value.isprintable()
            ):
                return node
            name = "__rope_literal_%d__" % len(literals)
            literals[name] = other + value + other
            return ast.copy_location(ast.Name(id=name, ctx=ast.Load()), node)

    if "__rope_literal_" not in text:
        text = ast.unparse(_Requote().visit(copy.deepcopy(expression)))
        for name, literal in literals.items():
            text = text.replace(name, literal)
    if quote in text or "\\" in text:
        raise rope.base.exceptions.RefactoringError(
            "Keyword value cannot be written inside this f-string before Python 3.12"
        )
    return text


def _keyword_expression(source):
    if not isinstance(source, str) or not source.strip():
        raise rope.base.exceptions.RefactoringError(
            "Keyword addition requires an explicit Python expression"
        )
    try:
        return ast.parse(source.strip(), mode="eval").body
    except SyntaxError as error:
        raise rope.base.exceptions.RefactoringError(
            "Keyword addition requires one valid Python expression"
        ) from error


class ChangeSignature:
    def __init__(self, project, resource, offset):
        self.project = project
        self.resource = resource
        self.offset = offset
        self._set_name_and_pyname()
        if (
            self.pyname is None
            or self.pyname.get_object() is None
            or not isinstance(self.pyname.get_object(), pyobjects.PyFunction)
        ):
            raise rope.base.exceptions.RefactoringError(
                "Change method signature should be performed on functions"
            )

    def _set_name_and_pyname(self):
        self.name = worder.get_name_at(self.resource, self.offset)
        this_pymodule = self.project.get_pymodule(self.resource)
        self.primary, self.pyname = evaluate.eval_location2(this_pymodule, self.offset)
        if self.pyname is None:
            return
        pyobject = self.pyname.get_object()
        if isinstance(pyobject, pyobjects.PyClass) and "__init__" in pyobject:
            self.pyname = pyobject["__init__"]
            self.name = "__init__"
        pyobject = self.pyname.get_object()
        self.others = None
        if (
            self.name == "__init__"
            and isinstance(pyobject, pyobjects.PyFunction)
            and isinstance(pyobject.parent, pyobjects.PyClass)
        ):
            pyclass = pyobject.parent
            self.others = (
                pyclass.get_name(),
                pyclass.parent.get_scope()[pyclass.get_name()],
            )

    def _change_calls(
        self,
        call_changer,
        in_hierarchy=None,
        resources=None,
        handle=taskhandle.DEFAULT_TASK_HANDLE,
    ):
        if resources is None:
            resources = self.project.get_python_files()
        changes = ChangeSet("Changing signature of <%s>" % self.name)
        job_set = handle.create_jobset("Collecting Changes", len(resources))
        finder = occurrences.create_finder(
            self.project,
            self.name,
            self.pyname,
            instance=self.primary,
            in_hierarchy=in_hierarchy and self.is_method(),
            unsure=(
                call_changer.refuse_unsure
                if isinstance(call_changer, _KeywordAdditions) and call_changer.required
                else None
            ),
        )
        if self.others:
            name, pyname = self.others
            constructor_finder = occurrences.create_finder(
                self.project,
                name,
                pyname,
                only_calls=not (
                    isinstance(call_changer, _KeywordAdditions)
                    and call_changer.required
                ),
                unsure=(
                    call_changer.refuse_unsure
                    if isinstance(call_changer, _KeywordAdditions)
                    and call_changer.required
                    else None
                ),
            )
            finder = _MultipleFinders([finder, constructor_finder])
        for file in resources:
            job_set.started_job(file.path)
            change_calls = _ChangeCallsInModule(
                self.project, finder, file, call_changer
            )
            changed_file = change_calls.get_changed_module()
            if changed_file is not None:
                changes.add_change(ChangeContents(file, changed_file))
            job_set.finished_job()
        if (
            isinstance(call_changer, _KeywordAdditions)
            and call_changer.required
            and changes.changes
        ):
            call_changer.resources = call_changer.resources | frozenset(
                change.resource for change in changes.changes
            )
            for file in sorted(
                call_changer.resources, key=lambda resource: resource.path
            ):
                call_changer.validate_consumers(self.project.get_pymodule(file))
        return changes

    def get_args(self):
        """Get function arguments.

        Return a list of ``(name, default)`` tuples for all but star
        and double star arguments.  For arguments that don't have a
        default, `None` will be used.
        """
        return self._definfo().args_with_defaults

    def is_method(self):
        pyfunction = self.pyname.get_object()
        return isinstance(pyfunction.parent, pyobjects.PyClass)

    @utils.deprecated("Use `ChangeSignature.get_args()` instead")
    def get_definition_info(self):
        return self._definfo()

    def _definfo(self):
        return functionutils.DefinitionInfo.read(self.pyname.get_object())

    @utils.deprecated()
    def normalize(self):
        functionutils._check_signature_parameters(self.pyname.get_object())
        changer = _FunctionChangers(
            self.pyname.get_object(), self._definfo(), [ArgumentNormalizer()]
        )
        return self._change_calls(changer)

    @utils.deprecated()
    def remove(self, index):
        functionutils._check_signature_parameters(self.pyname.get_object())
        changer = _FunctionChangers(
            self.pyname.get_object(),
            self._definfo(),
            [ArgumentRemover(index)],
        )
        return self._change_calls(changer)

    @utils.deprecated()
    def add(self, index, name, default=None, value=None):
        functionutils._check_signature_parameters(self.pyname.get_object())
        changer = _FunctionChangers(
            self.pyname.get_object(),
            self._definfo(),
            [ArgumentAdder(index, name, default, value)],
        )
        return self._change_calls(changer)

    @utils.deprecated()
    def inline_default(self, index):
        functionutils._check_signature_parameters(self.pyname.get_object())
        changer = _FunctionChangers(
            self.pyname.get_object(),
            self._definfo(),
            [ArgumentDefaultInliner(index)],
        )
        return self._change_calls(changer)

    @utils.deprecated()
    def reorder(self, new_ordering):
        functionutils._check_signature_parameters(self.pyname.get_object())
        changer = _FunctionChangers(
            self.pyname.get_object(),
            self._definfo(),
            [ArgumentReorderer(new_ordering)],
        )
        return self._change_calls(changer)

    def get_changes(
        self,
        changers,
        in_hierarchy=False,
        resources=None,
        task_handle=taskhandle.DEFAULT_TASK_HANDLE,
    ):
        """Get changes caused by this refactoring

        `changers` is a list of `_ArgumentChanger`.  If `in_hierarchy`
        is `True` the changers are applied to all matching methods in
        the class hierarchy.
        `resources` can be a list of `rope.base.resource.File` that
        should be searched for occurrences; if `None` all python files
        in the project are searched.

        """
        if any(
            isinstance(changer, ArgumentAdder) and changer.keyword_only
            for changer in changers
        ):
            if not all(
                isinstance(changer, ArgumentAdder) and changer.keyword_only
                for changer in changers
            ):
                raise rope.base.exceptions.RefactoringError(
                    "Keyword-only additions cannot be mixed with legacy signature changes"
                )
            if resources is None:
                resources = self.project.get_python_files()
            addition = _KeywordAdditions(
                changers, self.pyname, self.name, self.others, resources
            )
            return self._change_calls(
                addition,
                in_hierarchy,
                resources,
                task_handle,
            )
        functionutils._check_signature_parameters(self.pyname.get_object())
        function_changer = _FunctionChangers(
            self.pyname.get_object(), self._definfo(), changers
        )
        return self._change_calls(
            function_changer, in_hierarchy, resources, task_handle
        )


class _FunctionChangers:
    def __init__(self, pyfunction, definition_info, changers=None):
        self.pyfunction = pyfunction
        self.definition_info = definition_info
        self.changers = changers
        self.changed_definition_infos = self._get_changed_definition_infos()

    def _get_changed_definition_infos(self):
        definition_info = self.definition_info
        result = [definition_info]
        for changer in self.changers:
            definition_info = copy.deepcopy(definition_info)
            changer.change_definition_info(definition_info)
            result.append(definition_info)
        return result

    def change_definition(self, call):
        return self.changed_definition_infos[-1].to_string(annotated=True)

    def change_call(self, primary, pyname, call):
        call_info = functionutils.CallInfo.read(
            primary, pyname, self.definition_info, call
        )
        mapping = functionutils.ArgumentMapping(self.definition_info, call_info)

        for definition_info, changer in zip(
            self.changed_definition_infos, self.changers
        ):
            changer.change_argument_mapping(definition_info, mapping)

        return mapping.to_call_info(self.changed_definition_infos[-1]).to_string()


class _ArgumentChanger:
    def change_definition_info(self, definition_info):
        pass

    def change_argument_mapping(self, definition_info, argument_mapping):
        pass


class ArgumentNormalizer(_ArgumentChanger):
    pass


class ArgumentRemover(_ArgumentChanger):
    def __init__(self, index):
        self.index = index

    def change_definition_info(self, call_info):
        if self.index < len(call_info.args_with_defaults):
            del call_info.args_with_defaults[self.index]
        elif (
            self.index == len(call_info.args_with_defaults)
            and call_info.args_arg is not None
        ):
            call_info.args_arg = None
        elif (
            self.index == len(call_info.args_with_defaults)
            and call_info.args_arg is None
            and call_info.keywords_arg is not None
        ) or (
            self.index == len(call_info.args_with_defaults) + 1
            and call_info.args_arg is not None
            and call_info.keywords_arg is not None
        ):
            call_info.keywords_arg = None

    def change_argument_mapping(self, definition_info, mapping):
        if self.index < len(definition_info.args_with_defaults):
            name = definition_info.args_with_defaults[0]
            if name in mapping.param_dict:
                del mapping.param_dict[name]


class ArgumentAdder(_ArgumentChanger):
    def __init__(
        self,
        index,
        name,
        default=None,
        value=None,
        *,
        keyword_only=False,
        annotation=None,
    ):
        self.index = index
        self.name = name
        self.default = default
        self.value = value
        self.keyword_only = keyword_only
        self.annotation = annotation
        if keyword_only and (
            (default is None and value is None)
            or not name.isidentifier()
            or iskeyword(name)
        ):
            raise rope.base.exceptions.RefactoringError(
                "Keyword addition needs an identifier and a call value or default"
            )
        if keyword_only:
            for expression in (annotation, default):
                if expression is not None:
                    _keyword_expression(expression)
            if value is not None and not callable(value):
                _keyword_expression(value)

    def change_definition_info(self, definition_info):
        for pair in definition_info.args_with_defaults:
            if pair[0] == self.name:
                raise rope.base.exceptions.RefactoringError(
                    "Adding duplicate parameter: <%s>." % self.name
                )
        definition_info.args_with_defaults.insert(self.index, (self.name, self.default))

    def change_argument_mapping(self, definition_info, mapping):
        if self.value is not None:
            mapping.param_dict[self.name] = self.value


class ArgumentDefaultInliner(_ArgumentChanger):
    def __init__(self, index):
        self.index = index
        self.remove = False

    def change_definition_info(self, definition_info):
        if self.remove:
            definition_info.args_with_defaults[self.index] = (
                definition_info.args_with_defaults[self.index][0],
                None,
            )

    def change_argument_mapping(self, definition_info, mapping):
        default = definition_info.args_with_defaults[self.index][1]
        name = definition_info.args_with_defaults[self.index][0]
        if default is not None and name not in mapping.param_dict:
            mapping.param_dict[name] = default


class ArgumentReorderer(_ArgumentChanger):
    def __init__(self, new_order, autodef=None):
        """Construct an `ArgumentReorderer`

        Note that the `new_order` is a list containing the new
        position of parameters; not the position each parameter
        is going to be moved to. (changed in ``0.5m4``)

        For example changing ``f(a, b, c)`` to ``f(c, a, b)``
        requires passing ``[2, 0, 1]`` and *not* ``[1, 2, 0]``.

        The `autodef` (automatic default) argument, forces rope to use
        it as a default if a default is needed after the change.  That
        happens when an argument without default is moved after
        another that has a default value.  Note that `autodef` should
        be a string or `None`; the latter disables adding automatic
        default.

        """
        self.new_order = new_order
        self.autodef = autodef

    def change_definition_info(self, definition_info):
        new_args = list(definition_info.args_with_defaults)
        for new_index, index in enumerate(self.new_order):
            new_args[new_index] = definition_info.args_with_defaults[index]
        seen_default = False
        for index, (arg, default) in enumerate(list(new_args)):
            if default is not None:
                seen_default = True
            if seen_default and default is None and self.autodef is not None:
                new_args[index] = (arg, self.autodef)
        definition_info.args_with_defaults = new_args


class _KeywordAdditions:
    """Insert required keywords using the native parse and original source bytes."""

    def __init__(self, additions, pyname, name, constructor=None, resources=()):
        self.additions = additions
        self.required = any(addition.default is None for addition in additions)
        self.resources = (
            self._source_component(pyname.get_object().get_module(), resources)
            if self.required
            else frozenset(resources)
        )
        self.reflective_targets = ((name, pyname),) + (
            (constructor,) if constructor is not None else ()
        )
        if constructor is not None:
            owner = constructor[1].get_object()
            self._check_decorators(owner, owner.get_module().get_source_binding_index())
            native_new = (
                builtins.builtins["object"].get_object().get_attributes()["__new__"]
            )
            custom_new = owner.get_attributes().get("__new__")
            if (
                owner.get_metaclass() is not builtins.builtins["type"].get_object()
                or any(
                    isinstance(base, pyobjects.UnresolvedBase)
                    for base in owner.get_mro()
                )
                or custom_new is not None
                and not occurrences.same_pyname(custom_new, native_new)
            ):
                raise rope.base.exceptions.RefactoringError(
                    "Constructor allocation has no proven native keyword behavior"
                )
        if len({addition.name for addition in additions}) != len(additions):
            raise rope.base.exceptions.RefactoringError(
                "Adding duplicate keyword parameters"
            )

    @staticmethod
    def refuse_unsure(occurrence):
        raise rope.base.exceptions.RefactoringError(
            "Unresolved signature consumer at %s:%s"
            % (occurrence.resource.path, occurrence.lineno)
        )

    @staticmethod
    def _source_component(module, resources):
        resources = frozenset(resources)
        root = module.get_resource()
        if root not in resources:
            raise rope.base.exceptions.RefactoringError(
                "Signature owner is outside the analyzed source boundary"
            )
        project = module.pycore.project
        graph = {resource: set() for resource in resources}
        for resource in resources:
            current = project.get_pymodule(resource)
            for call in ast.walk(current.get_ast()):
                if not isinstance(call, ast.Call):
                    continue
                scope = current.get_scope().get_inner_scope_for_line(call.lineno)
                binding = evaluate.eval_node(scope, call.func)
                function = binding.get_object() if binding is not None else None
                if not (
                    getattr(function, "builtin", None) is __import__
                    or builtins._is_runtime_form(function, importlib.import_module)
                ):
                    continue
                if not (
                    call.args
                    and isinstance(call.args[0], ast.Constant)
                    and isinstance(call.args[0].value, str)
                    and not call.args[0].value.startswith(".")
                ):
                    raise rope.base.exceptions.RefactoringError(
                        f"{resource.path}:{call.lineno}: Unresolved dynamic import boundary"
                    )
                imported = project.find_module(call.args[0].value, resource.parent)
                if (
                    imported is not None
                    and imported.is_folder()
                    and imported.has_child("__init__.py")
                ):
                    imported = imported.get_child("__init__.py")
                if imported in graph:
                    graph[resource].add(imported)
                    graph[imported].add(resource)
            for declaration in current.get_source_binding_index().import_layouts():
                if declaration.module_name is None:
                    names = [name for name, _, _ in declaration.aliases]
                else:
                    provider = declaration.module_name
                    names = [provider] + [
                        (provider + "." if provider else "") + name
                        for name, _, _ in declaration.aliases
                        if name != "*"
                    ]
                for name in names:
                    imported = (
                        project.find_relative_module(
                            name, resource.parent, declaration.level
                        )
                        if declaration.level
                        else project.find_module(name, resource.parent)
                    )
                    if (
                        imported is not None
                        and imported.is_folder()
                        and imported.has_child("__init__.py")
                    ):
                        imported = imported.get_child("__init__.py")
                    if imported in graph:
                        graph[resource].add(imported)
                        graph[imported].add(resource)
        pending = [root]
        reached = set()
        while pending:
            current = pending.pop()
            if current not in reached:
                reached.add(current)
                pending.extend(graph[current] - reached)
        return frozenset(reached)

    def validate_consumers(self, pymodule):
        soa.analyze_module(
            pymodule.pycore,
            pymodule,
            lambda owner: True,
            lambda owner: True,
            sum(
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                for resource in self.resources
                for node in ast.walk(
                    pymodule.pycore.resource_to_pyobject(resource).get_ast()
                )
            ),
            visitor_factory=partial(_SignatureEffects, proof=self),
        )

    def changes(self, pymodule, occurrences):
        source = pymodule.source_code
        index = pymodule.get_source_binding_index()
        calls = {
            index._span(node.func): node
            for node in ast.walk(pymodule.get_ast())
            if isinstance(node, ast.Call)
        }
        words = worder.Worder(source)
        real = simplify.real_code(source)
        fstrings = None
        for occurrence in occurrences:
            start, end = occurrence.get_primary_range()
            node = calls.get((start, end))
            if occurrence.is_in_import_statement():
                if self.required and any(
                    alias is not None
                    and alias != name.rsplit(".", 1)[-1]
                    and first <= occurrence.offset < last
                    for layout in index.import_layouts()
                    for name, alias, (first, last) in layout.aliases
                ):
                    raise rope.base.exceptions.RefactoringError(
                        "Signature consumer escapes through an import alias"
                    )
                continue
            generator = False
            if occurrence.is_defined():
                function = occurrence.get_pyname().get_object()
                self._check_decorators(function, index)
                if isinstance(function, pyobjects.PyClass):
                    continue
                declaration = function.get_ast()
                arguments = declaration.args
                parameter_start = max(
                    (
                        end,
                        *(
                            index._span(item)[1]
                            for item in getattr(declaration, "type_params", ())
                        ),
                    )
                )
                begin, finish = words.get_word_parens_range(parameter_start - 1)
                insertion = finish - 1
                if arguments.kwarg is not None:
                    insertion = real.rfind("**", begin, index._span(arguments.kwarg)[0])
                    if insertion < begin:
                        raise rope.base.exceptions.RefactoringError(
                            "Cannot locate native keyword parameter"
                        )
                existing = {
                    argument.arg: argument
                    for argument in (
                        *arguments.posonlyargs,
                        *arguments.args,
                        *arguments.kwonlyargs,
                        *((arguments.vararg,) if arguments.vararg else ()),
                        *((arguments.kwarg,) if arguments.kwarg else ()),
                    )
                }
                added = []
                for addition in self.additions:
                    argument = existing.get(addition.name)
                    if argument is not None:
                        annotation = (
                            ast.dump(argument.annotation)
                            if argument.annotation
                            else None
                        )
                        expected_annotation = (
                            ast.dump(_keyword_expression(addition.annotation))
                            if addition.annotation is not None
                            else None
                        )
                        if (
                            argument not in arguments.kwonlyargs
                            or annotation != expected_annotation
                        ):
                            raise rope.base.exceptions.RefactoringError(
                                "Conflicting existing keyword parameter: "
                                + addition.name
                            )
                        default = arguments.kw_defaults[
                            arguments.kwonlyargs.index(argument)
                        ]
                        actual = ast.dump(default) if default is not None else None
                        expected_default = (
                            ast.dump(_keyword_expression(addition.default))
                            if addition.default is not None
                            else None
                        )
                        if actual != expected_default:
                            raise rope.base.exceptions.RefactoringError(
                                "Conflicting existing keyword default: " + addition.name
                            )
                        continue
                    added.append(
                        addition.name
                        + (
                            ": " + ast.unparse(_keyword_expression(addition.annotation))
                            if addition.annotation is not None
                            else ""
                        )
                        + (
                            " = " + ast.unparse(_keyword_expression(addition.default))
                            if addition.default is not None
                            else ""
                        )
                    )
                if not added:
                    continue
                if arguments.vararg is None and not arguments.kwonlyargs:
                    added.insert(0, "*")
            elif node is not None or occurrence.is_called():
                selected = [
                    (
                        addition,
                        (
                            addition.value(pymodule, occurrence)
                            if callable(addition.value)
                            else addition.value
                        ),
                    )
                    for addition in self.additions
                ]
                selected = [
                    (addition, requested)
                    for addition, requested in selected
                    if requested is not None or addition.default is None
                ]
                if not selected:
                    continue
                if node is None or any(
                    keyword.arg is None for keyword in node.keywords
                ):
                    raise rope.base.exceptions.RefactoringError(
                        "Ambiguous native keyword call expansion"
                    )
                finish = index._span(node)[1]
                begin = words._find_parens_start(finish - 1)
                insertion = finish - 1
                existing = {keyword.arg: keyword.value for keyword in node.keywords}
                added = []
                if fstrings is None:
                    fstrings = _fstring_quotes(pymodule)
                quote = _enclosing_fstring_quote(fstrings, *index._span(node))
                for addition, requested in selected:
                    expression = _keyword_expression(requested)
                    value = existing.get(addition.name)
                    if value is not None:
                        if ast.dump(value) != ast.dump(expression):
                            raise rope.base.exceptions.RefactoringError(
                                "Conflicting existing keyword argument: "
                                + addition.name
                            )
                        continue
                    added.append(
                        addition.name + "=" + _replacement_field_text(expression, quote)
                    )
                if not added:
                    continue
                generator = (
                    len(node.args) == 1
                    and isinstance(node.args[0], ast.GeneratorExp)
                    and index._span(node.args[0]) == (begin, finish)
                )
                if generator:
                    yield begin + 1, begin + 1, "("
            else:
                if not self.required:
                    continue
                raise rope.base.exceptions.RefactoringError(
                    "Signature consumer escapes as a non-call reference"
                )
            prefix = real[begin + 1 : insertion].rstrip()
            line_start = source.rfind("\n", begin + 1, insertion) + 1
            if line_start > begin and not source[line_start:insertion].strip():
                parameters = (
                    tuple(existing.values())
                    if occurrence.is_defined()
                    else (*node.args, *node.keywords)
                )
                indentation = source[
                    line_start:insertion
                ] + " " * sourceutils.get_indent(pymodule.pycore.project)
                for parameter in sorted(
                    parameters, key=lambda item: index._span(item)[0], reverse=True
                ):
                    parameter_start = index._span(parameter)[0]
                    parameter_line = source.rfind("\n", begin + 1, parameter_start) + 1
                    candidate = source[parameter_line:parameter_start].rstrip("*")
                    if parameter_line > begin and not candidate.strip():
                        indentation = candidate
                        break
                if prefix and not prefix.endswith(","):
                    last = begin + 1 + len(prefix)
                    yield last, last, (")" if generator else "") + ","
                yield line_start, line_start, "".join(
                    indentation + item + ",\n" for item in added
                )
                continue
            separator = (
                ", " if prefix and not prefix.endswith(",") else " " if prefix else ""
            )
            suffix = (
                ", " if occurrence.is_defined() and arguments.kwarg is not None else ""
            )
            yield (
                insertion,
                insertion,
                (")" if generator else "") + separator + ", ".join(added) + suffix,
            )

    @staticmethod
    def _check_decorators(owner, index):
        decorators = owner.get_ast().decorator_list
        if not decorators:
            return
        if (
            isinstance(owner, pyobjects.PyClass)
            or len(decorators) != 1
            or isinstance(decorators[0], ast.Call)
        ):
            raise rope.base.exceptions.RefactoringError(
                "Signature decorator has no proven native behavior"
            )
        binding = index.decorator_bindings(owner.get_scope())[0]
        if binding is None or not (
            getattr(binding.get_object(), "builtin", None)
            in (staticmethod, classmethod)
            or builtins._is_runtime_form(
                binding.get_object(), contextlib.contextmanager
            )
        ):
            raise rope.base.exceptions.RefactoringError(
                "Signature decorator has no proven native behavior"
            )

    def _refuse_opaque_consumer(self, pymodule, node):
        if not isinstance(node, ast.Call):
            return
        scope = pymodule.get_scope().get_inner_scope_for_line(node.lineno)
        callee = evaluate.eval_node(scope, node.func)
        target = callee.get_object() if callee is not None else None
        if (
            target is None
            or target == pyobjects.get_unknown()
            or occurrences.unsure_pyname(callee)
        ):
            raise rope.base.exceptions.RefactoringError(
                "Unresolved callable cannot prove absence of an opaque signature consumer"
            )
        if getattr(target, "builtin", None) in (eval, exec):
            try:
                if (
                    not node.args
                    or not isinstance(node.args[0], ast.Constant)
                    or not isinstance(node.args[0].value, str)
                ):
                    raise ValueError("Dynamic code has no literal source")
                if target.builtin is eval:
                    ast.literal_eval(node.args[0].value)
                else:
                    for statement in ast.parse(node.args[0].value).body:
                        if isinstance(statement, ast.Pass):
                            continue
                        if not isinstance(statement, ast.Expr):
                            raise ValueError("Dynamic statement can change bindings")
                        ast.literal_eval(statement.value)
            except (SyntaxError, ValueError, TypeError) as error:
                raise rope.base.exceptions.RefactoringError(
                    "Dynamic code has no proven signature consumer behavior"
                ) from error
            return
        module = target.get_module() if target is not None else None
        internal = module is not None and module.get_resource() in self.resources
        for argument in (*node.args, *(keyword.value for keyword in node.keywords)):
            for binding in self._argument_bindings(pymodule, argument, set()):
                for value in self._contained_objects(binding.get_object()):
                    self._check_opaque_value(pymodule, value, internal)

    def _check_opaque_value(self, pymodule, value, internal):
        if not internal and (value is None or value == pyobjects.get_unknown()):
            raise rope.base.exceptions.RefactoringError(
                "Unresolved value cannot prove absence of an opaque signature consumer"
            )
        function = classfunctions.canonical_function(value)
        module = function.get_module()
        if isinstance(function, pyobjects.AbstractFunction) and not (
            module is not None
            and module.get_resource() in self.resources
            or isinstance(function, builtins.BuiltinFunction)
            and function.function is not None
            or builtins.has_runtime_call_model(function)
        ):
            raise rope.base.exceptions.RefactoringError(
                "Unproved callable escapes through an opaque signature consumer"
            )
        if internal:
            return
        if not isinstance(value, (pyobjects.AbstractClass, pyobjects.AbstractModule)):
            value = value.get_type()
        members = value.get_attributes()
        if any(
            occurrences.same_pyname(declared_binding, members.get(name))
            for name, declared_binding in self.reflective_targets
        ):
            raise rope.base.exceptions.RefactoringError(
                "Target namespace escapes through an opaque signature consumer"
            )

    def _argument_bindings(self, pymodule, expression, seen):
        identity = (id(pymodule), id(expression))
        if identity in seen:
            return
        seen.add(identity)
        scope = pymodule.get_scope().get_inner_scope_for_line(expression.lineno)
        binding = evaluate.eval_node(scope, expression)
        if binding is not None:
            yield binding
            while isinstance(binding, pynames.ImportedName):
                underlying = binding._get_imported_pyname()
                if id(underlying) in seen:
                    break
                seen.add(id(underlying))
                binding = underlying
            if isinstance(binding, pynames.AssignedName):
                for assignment in binding.assignments:
                    value = assignment.ast_node
                    for level in assignment.levels:
                        if not isinstance(value, (ast.List, ast.Tuple)) or level >= len(
                            value.elts
                        ):
                            value = None
                            break
                        value = value.elts[level]
                    if value is not None:
                        yield from self._argument_bindings(binding.module, value, seen)
        if isinstance(expression, (ast.List, ast.Tuple, ast.Set)):
            children = expression.elts
        elif isinstance(expression, ast.Dict):
            children = [
                item
                for item in (*expression.keys, *expression.values)
                if item is not None
            ]
        elif isinstance(expression, ast.Starred):
            children = [expression.value]
        elif isinstance(expression, ast.Subscript) and isinstance(
            expression.slice, ast.Slice
        ):
            children = [expression.value]
        else:
            children = []
        for child in children:
            yield from self._argument_bindings(pymodule, child, seen)

    def validate_effect(self, pymodule, function, args):
        function = classfunctions.canonical_function(function)
        module = function.get_module()
        internal = module is not None and module.get_resource() in self.resources
        names = (
            function.get_param_names()
            if isinstance(function, pyobjects.AbstractFunction)
            else []
        )
        for binding in args.get_pynames(names):
            if binding is None:
                continue
            for value in self._contained_objects(binding.get_object()):
                self._check_opaque_value(pymodule, value, internal)

    @staticmethod
    def _contained_objects(value):
        pending = [value]
        seen = set()
        while pending:
            value = pending.pop()
            if value is None or id(value) in seen:
                continue
            seen.add(id(value))
            if isinstance(value, pyobjects.SampledValue):
                # A sampled read leaves its container position unproved; the
                # element itself is the value an opaque consumer receives.
                pending.append(value.representative)
                continue
            yield value
            if isinstance(value, builtins.NamespaceItems):
                pending.append(value.receiver.get_object())
                continue
            kind = value.get_type()
            if isinstance(
                kind,
                (
                    builtins.Sequence,
                    builtins.List,
                    builtins.Set,
                    builtins.Iterator,
                    builtins.Generator,
                ),
            ):
                pending.append(kind.holding)
            elif isinstance(kind, builtins.Tuple):
                pending.extend(kind.get_holding_objects())
            elif isinstance(kind, builtins.Dict):
                pending.extend((kind.keys, kind.values))
            if isinstance(value, (pyobjects.PyClass, pyobjects.PyModule)):
                owner = value
            elif isinstance(kind, pyobjects.PyClass):
                owner = kind
            else:
                continue
            pending.extend(
                member.get_object()
                for member in owner.get_attributes().values()
                if not isinstance(member.get_object(), pyobjects.AbstractFunction)
            )


class _SignatureEffects(soa.SOAVisitor):
    def __init__(self, pycore, pydefined, follow_callback=None, *, proof):
        super().__init__(pycore, pydefined, follow_callback)
        self.proof = proof
        self.node = None

    def visit(self, node):
        previous = self.node
        self.node = node
        try:
            return super().visit(node)
        finally:
            self.node = previous

    def _failure(self, operation, error):
        resource = self.pymodule.get_resource()
        raise rope.base.exceptions.RefactoringError(
            f"{resource.path}:{self.node.lineno}: {operation}: {error}"
        ) from error

    def _Call(self, node):
        if self.proof.required:
            try:
                self.proof._refuse_opaque_consumer(self.pymodule, node)
            except rope.base.exceptions.RefactoringError as error:
                self._failure("call " + type(node.func).__name__, error)
        super()._Call(node)

    def _call(self, function, args):
        super()._call(function, args)
        if self.proof.required and not (
            isinstance(self.node, (ast.BinOp, ast.AugAssign, ast.Compare))
            and isinstance(function, builtins.BuiltinFunction)
            and function.parent is builtins.builtins["int"].get_object()
        ):
            try:
                self.proof.validate_effect(self.pymodule, function, args)
            except rope.base.exceptions.RefactoringError as error:
                self._failure("effect " + str(function.get_name()), error)


class _ChangeCallsInModule:
    def __init__(self, project, occurrence_finder, resource, call_changer):
        self.project = project
        self.occurrence_finder = occurrence_finder
        self.resource = resource
        self.call_changer = call_changer

    def get_changed_module(self):
        word_finder = worder.Worder(self.source)
        change_collector = codeanalyze.ChangeCollector(self.source)
        if isinstance(self.call_changer, _KeywordAdditions):
            for start, end, replacement in self.call_changer.changes(
                self.pymodule, self.occurrence_finder.find_occurrences(self.resource)
            ):
                change_collector.add_change(start, end, replacement)
            changed = change_collector.get_changed()
            if changed is not None:
                try:
                    compile(changed, self.resource.path, "exec", dont_inherit=True)
                except SyntaxError as error:
                    raise rope.base.exceptions.RefactoringError(
                        "Keyword addition is invalid in the native source context"
                    ) from error
            return changed
        for occurrence in self.occurrence_finder.find_occurrences(self.resource):
            if not occurrence.is_called() and not occurrence.is_defined():
                continue
            primary, pyname = occurrence.get_primary_and_pyname()
            if pyname is not None:
                pyfunction = pyname.get_object()
                if (
                    isinstance(pyfunction, pyobjects.PyClass)
                    and "__init__" in pyfunction
                ):
                    pyfunction = pyfunction["__init__"].get_object()
                if isinstance(pyfunction, pyobjects.PyFunction):
                    functionutils._check_signature_parameters(pyfunction)
            start, end = occurrence.get_primary_range()
            begin_parens, end_parens = word_finder.get_word_parens_range(end - 1)
            if occurrence.is_called():
                changed_call = self.call_changer.change_call(
                    primary, pyname, self.source[start:end_parens]
                )
            else:
                changed_call = self.call_changer.change_definition(
                    self.source[start:end_parens]
                )
            if changed_call is not None:
                change_collector.add_change(start, end_parens, changed_call)
        return change_collector.get_changed()

    @property
    @utils.saveit
    def pymodule(self):
        return self.project.get_pymodule(self.resource)

    @property
    @utils.saveit
    def source(self):
        if self.resource is not None:
            return self.resource.read()
        else:
            return self.pymodule.source_code

    @property
    @utils.saveit
    def lines(self):
        return self.pymodule.lines


class _MultipleFinders:
    def __init__(self, finders):
        self.finders = finders

    def find_occurrences(self, resource=None, pymodule=None):
        all_occurrences = []
        for finder in self.finders:
            all_occurrences.extend(finder.find_occurrences(resource, pymodule))
        all_occurrences.sort(key=lambda x: x.get_primary_range())
        return all_occurrences
