# Known Bugs when inlining a function/method
# The values passed to function are inlined using _inlined_variable.
# This may cause two problems, illustrated in the examples below
#
# def foo(var1):
#    var1 = var1*10
#    return var1
#
#  If a call to foo(20) is inlined, the result of inlined function is 20,
#  but it should be 200.
#
# def foo(var1):
#    var2 = var1*10
#    return var2
#
# 2- If a call to foo(10+10) is inlined the result of inlined function is 110
#  but it should be 200.

import re
import sys
from typing import List

import rope.base.builtins  # Use fully qualified names for clarity.
from rope.base import (
    ast,
    codeanalyze,
    evaluate,
    exceptions,
    libutils,
    pynames,
    pyobjects,
    taskhandle,
    utils,
    worder,
)
from rope.base.change import ChangeContents, ChangeSet
from rope.refactor import (
    change_signature,
    functionutils,
    importutils,
    move,
    occurrences,
    patchedast,
    rename,
    sourceutils,
)


def unique_prefix():
    n = 0
    while True:
        yield "__" + str(n) + "__"
        n += 1


def create_inline(project, resource, offset):
    """Create a refactoring object for inlining

    Based on `resource` and `offset` it returns an instance of
    `InlineMethod`, `InlineVariable` or `InlineParameter`.

    """
    pyname = _get_pyname(project, resource, offset)
    message = (
        "Inline refactoring should be performed on "
        "a method, local variable or parameter."
    )
    if pyname is None:
        raise exceptions.RefactoringError(message)
    if isinstance(pyname, pynames.ImportedName):
        pyname = pyname._get_imported_pyname()
    if isinstance(pyname, pynames.AssignedName):
        return InlineVariable(project, resource, offset)
    if isinstance(pyname, pynames.ParameterName):
        return InlineParameter(project, resource, offset)
    if isinstance(pyname.get_object(), pyobjects.PyFunction):
        return InlineMethod(project, resource, offset)
    else:
        raise exceptions.RefactoringError(message)


class _Inliner:
    def __init__(self, project, resource, offset):
        self.project = project
        self.pyname = _get_pyname(project, resource, offset)
        range_finder = worder.Worder(resource.read(), True)
        self.region = range_finder.get_primary_range(offset)
        self.name = range_finder.get_word_at(offset)
        self.offset = offset
        self.original = resource

    def get_changes(self, *args, **kwds):
        pass

    def get_kind(self):
        """Return either 'variable', 'method' or 'parameter'"""


class InlineMethod(_Inliner):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.pyfunction = self.pyname.get_object()
        self.pymodule = self.pyfunction.get_module()
        self.resource = self.pyfunction.get_module().get_resource()
        self.occurrence_finder = occurrences.create_finder(
            self.project, self.name, self.pyname
        )
        self.normal_generator = _DefinitionGenerator(self.project, self.pyfunction)
        self._init_imports()

    def _init_imports(self):
        body = sourceutils.get_body(self.pyfunction)
        body, imports = move.moving_code_with_imports(self.project, self.resource, body)
        self.imports = imports
        self.others_generator = _DefinitionGenerator(
            self.project, self.pyfunction, body=body
        )

    def _get_scope_range(self):
        scope = self.pyfunction.get_scope()
        lines = self.pymodule.lines
        start_line = scope.get_start()
        if self.pyfunction.decorators:
            decorators = self.pyfunction.decorators
            if hasattr(decorators[0], "lineno"):
                start_line = decorators[0].lineno
        start_offset = lines.get_line_start(start_line)
        end_offset = min(
            lines.get_line_end(scope.end) + 1, len(self.pymodule.source_code)
        )
        return (start_offset, end_offset)

    def get_changes(
        self,
        remove=True,
        only_current=False,
        resources=None,
        task_handle=taskhandle.DEFAULT_TASK_HANDLE,
    ):
        """Get the changes this refactoring makes

        If `remove` is `False` the definition will not be removed.  If
        `only_current` is `True`, the the current occurrence will be
        inlined, only.
        """
        changes = ChangeSet("Inline method <%s>" % self.name)
        if resources is None:
            resources = self.project.get_python_files()
        if only_current:
            resources = [self.original]
            if remove:
                resources.append(self.resource)
        job_set = task_handle.create_jobset("Collecting Changes", len(resources))
        for file in resources:
            job_set.started_job(file.path)
            if file == self.resource:
                changes.add_change(
                    self._defining_file_changes(
                        changes, remove=remove, only_current=only_current
                    )
                )
            else:
                aim = None
                if only_current and self.original == file:
                    aim = self.offset
                handle = _InlineFunctionCallsForModuleHandle(
                    self.project, file, self.others_generator, aim
                )
                result = move.ModuleSkipRenamer(
                    self.occurrence_finder, file, handle
                ).get_changed_module()
                if result is not None:
                    result = _add_imports(self.project, result, file, self.imports)
                    if remove:
                        result = _remove_from(self.project, self.pyname, result, file)
                    changes.add_change(ChangeContents(file, result))
            job_set.finished_job()
        return changes

    def _get_removed_range(self):
        scope = self.pyfunction.get_scope()
        lines = self.pymodule.lines
        start, end = self._get_scope_range()
        end_line = scope.get_end()
        for i in range(end_line + 1, lines.length()):
            if lines.get_line(i).strip() == "":
                end_line = i
            else:
                break
        end = min(lines.get_line_end(end_line) + 1, len(self.pymodule.source_code))
        return (start, end)

    def _defining_file_changes(self, changes, remove, only_current):
        start_offset, end_offset = self._get_removed_range()
        aim = None
        if only_current:
            if self.resource == self.original:
                aim = self.offset
            else:
                # we don't want to change any of them
                aim = len(self.resource.read()) + 100
        handle = _InlineFunctionCallsForModuleHandle(
            self.project, self.resource, self.normal_generator, aim_offset=aim
        )
        replacement = None
        if remove:
            replacement = self._get_method_replacement()
        result = move.ModuleSkipRenamer(
            self.occurrence_finder,
            self.resource,
            handle,
            start_offset,
            end_offset,
            replacement,
        ).get_changed_module()
        return ChangeContents(self.resource, result)

    def _get_method_replacement(self):
        if self._is_the_last_method_of_a_class():
            indents = sourceutils.get_indents(
                self.pymodule.lines, self.pyfunction.get_scope().get_start()
            )
            return " " * indents + "pass\n"
        return ""

    def _is_the_last_method_of_a_class(self):
        pyclass = self.pyfunction.parent
        if not isinstance(pyclass, pyobjects.PyClass):
            return False
        class_start, class_end = sourceutils.get_body_region(pyclass)
        source = self.pymodule.source_code
        func_start, func_end = self._get_scope_range()
        return (
            source[class_start:func_start].strip() == ""
            and source[func_end:class_end].strip() == ""
        )

    def get_kind(self):
        return "method"


class InlineVariable(_Inliner):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        if not isinstance(self.pyname, pynames.AssignedName):
            raise exceptions.RefactoringError(
                "Inline variable should be performed on an assigned variable."
            )
        self.pymodule = self.pyname.get_definition_location()[0]
        self.resource = self.pymodule.get_resource()
        self._check_exceptional_conditions()
        self._init_imports()

    def _check_exceptional_conditions(self):
        if any(
            isinstance(assignment.ast_node, ast.pattern)
            for assignment in self.pyname.assignments
        ):
            raise exceptions.RefactoringError(
                "Pattern matching captures cannot be inlined."
            )
        if len(self.pyname.assignments) != 1:
            raise exceptions.RefactoringError(
                "Local variable should be assigned once for inlining."
            )

    def get_changes(
        self,
        remove=True,
        only_current=False,
        resources=None,
        docs=False,
        task_handle=taskhandle.DEFAULT_TASK_HANDLE,
    ):
        if resources is None:
            if rename._is_local(self.pyname):
                resources = [self.resource]
            else:
                resources = self.project.get_python_files()
        if only_current:
            resources = [self.original]
            if remove and self.original != self.resource:
                resources.append(self.resource)
        resources = list(resources)
        check_resources = resources
        if remove and not rename._is_local(self.pyname):
            check_resources = list(
                dict.fromkeys(resources + list(self.project.get_python_files()))
            )
        for resource in check_resources:
            self._check_deferred_annotation_references(resource, remove, only_current)
        if remove and self.resource in resources:
            self._check_initializer_removal(resources, only_current)
        changes = ChangeSet("Inline variable <%s>" % self.name)
        jobset = task_handle.create_jobset("Calculating changes", len(resources))

        for resource in resources:
            jobset.started_job(resource.path)
            if resource == self.resource:
                source = self._change_main_module(remove, only_current, docs)
                changes.add_change(ChangeContents(self.resource, source))
            else:
                result = self._change_module(resource, remove, only_current)
                if result is not None:
                    result = _add_imports(self.project, result, resource, self.imports)
                    changes.add_change(ChangeContents(resource, result))
            jobset.finished_job()
        return changes

    def _check_deferred_annotation_references(self, resource, remove, only_current):
        pymodule = self.project.get_pymodule(resource)
        tree = pymodule.get_ast()
        future_annotations = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
            and any(alias.name == "annotations" for alias in node.names)
            for node in tree.body
        )
        if not future_annotations and sys.version_info < (3, 12):
            return
        annotations = []
        type_parameters = []

        def collect(node, scope=None):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                parameters = getattr(node, "type_params", [])
                if parameters:
                    namespace = (
                        pymodule.get_scope()
                        .get_inner_scope_for_line(node.lineno)
                        .parent
                    )
                    names = {parameter.name for parameter in parameters}
                    for parameter in parameters:
                        for attr in ("bound", "default_value"):
                            expression = getattr(parameter, attr, None)
                            if expression is not None:
                                type_parameters.append((expression, namespace, names))
            if isinstance(node, ast.arg):
                annotations.append(node.annotation)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                annotations.append(node.returns)
                scope = "function"
            elif isinstance(node, ast.Lambda):
                scope = "function"
            elif isinstance(node, ast.ClassDef):
                scope = "class"
            elif (
                isinstance(node, ast.AnnAssign) and node.simple and scope != "function"
            ):
                annotations.append(node.annotation)
            for child in ast.iter_child_nodes(node):
                collect(child, scope)

        collect(tree)
        if not future_annotations and sys.version_info < (3, 14):
            annotations = []
        lines = codeanalyze.ASTLinesAdapter(pymodule.source_code)
        regions = [lines[node] for node in annotations if node is not None]
        parameter_regions = [lines[item[0]] for item in type_parameters]
        if not regions and not parameter_regions:
            return

        def parameter_reference(node, namespace, names):
            inner_namespace = namespace
            inner_names = set(names)
            while inner_namespace.get_kind() == "Class":
                inner_names.update(
                    parameter.name
                    for parameter in getattr(
                        inner_namespace.pyobject.get_ast(), "type_params", []
                    )
                )
                inner_namespace = inner_namespace.parent
            if isinstance(node, ast.Lambda):
                arguments = node.args
                defaults = arguments.defaults + [
                    default for default in arguments.kw_defaults if default is not None
                ]
                bound_names = inner_names | {
                    argument.arg
                    for argument in (
                        arguments.posonlyargs
                        + arguments.args
                        + arguments.kwonlyargs
                        + [arguments.vararg, arguments.kwarg]
                    )
                    if argument is not None
                }
                return any(
                    parameter_reference(default, namespace, names)
                    for default in defaults
                ) or parameter_reference(node.body, inner_namespace, bound_names)
            if isinstance(
                node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
            ):
                bound_names = set(names)
                for index, generator in enumerate(node.generators):
                    iterable_namespace = namespace if index == 0 else inner_namespace
                    if parameter_reference(
                        generator.iter, iterable_namespace, bound_names
                    ):
                        return True
                    bound_names.update(inner_names)
                    bound_names.update(
                        name.id
                        for name in ast.walk(generator.target)
                        if isinstance(name, ast.Name)
                        and isinstance(name.ctx, ast.Store)
                    )
                    if parameter_reference(
                        generator.target, inner_namespace, bound_names
                    ):
                        return True
                    if any(
                        parameter_reference(condition, inner_namespace, bound_names)
                        for condition in generator.ifs
                    ):
                        return True
                values = (
                    [node.key, node.value]
                    if isinstance(node, ast.DictComp)
                    else [node.elt]
                )
                return any(
                    parameter_reference(value, inner_namespace, bound_names)
                    for value in values
                )
            if isinstance(node, (ast.Name, ast.Attribute)):
                primary = node
                while isinstance(primary, ast.Attribute):
                    primary = primary.value
                if not (isinstance(primary, ast.Name) and primary.id in names):
                    if isinstance(primary, ast.Name):
                        outer_scope = namespace
                        while outer_scope is not None:
                            if (
                                outer_scope.get_kind() != "Class"
                                or outer_scope is namespace
                            ) and primary.id in outer_scope.get_names():
                                break
                            if any(
                                parameter.name == primary.id
                                for parameter in getattr(
                                    outer_scope.pyobject.get_ast(), "type_params", []
                                )
                            ):
                                return False
                            outer_scope = outer_scope.parent
                    if occurrences.same_pyname(
                        self.pyname, evaluate.eval_node(namespace, node)
                    ):
                        return True
            return any(
                parameter_reference(child, namespace, names)
                for child in ast.iter_child_nodes(node)
            )

        if remove and any(
            parameter_reference(expression, namespace, names)
            for expression, namespace, names in type_parameters
        ):
            # Type parameter expressions use the enclosing annotation scope,
            # not the function's parameters/locals or the new class's body.
            raise exceptions.RefactoringError(
                "Cannot inline a variable referenced in a deferred annotation."
            )
        module_names = pymodule.get_scope().get_names()

        def runtime_annotation_eval(node):
            """Resolve a deferred annotation expression the way Python does.

            ``typing.get_type_hints`` evaluates class annotations with the
            module globals ahead of class and function locals (it swaps the
            two namespaces for classes), while the source binding index
            resolves the annotation in its own annotation environment.  A
            module-level binding therefore wins over shadowing names in the
            class or function header, and only names without a module-level
            binding fall back to the annotation environment.
            """
            if isinstance(node, ast.Attribute):
                base = runtime_annotation_eval(node.value)
                if base is None:
                    return None
                pyobject = base.get_object()
                if pyobject == pyobjects.get_unknown():
                    return None
                try:
                    return pyobject[node.attr]
                except exceptions.AttributeNotFoundError:
                    return None
            if isinstance(node, ast.Name):
                if node.id in module_names:
                    return module_names[node.id]
                return evaluate.eval_node(pymodule.get_scope(), node)
            return None

        if (
            future_annotations
            and remove
            and any(
                isinstance(node, (ast.Name, ast.Attribute))
                and occurrences.same_pyname(self.pyname, runtime_annotation_eval(node))
                for annotation in annotations
                if annotation is not None
                for node in ast.walk(annotation)
            )
        ):
            # Stringified annotations may resolve module globals even when
            # static name lookup finds a class member or function parameter.
            raise exceptions.RefactoringError(
                "Cannot inline a variable referenced in a deferred annotation."
            )
        finder = occurrences.create_finder(
            self.project, self.name, self.pyname, imports=False
        )
        for occurrence in finder.find_occurrences(pymodule=pymodule):
            current = True
            if only_current:
                start, end = occurrence.get_primary_range()
                current = resource == self.original and start <= self.offset <= end
                if not remove and not current:
                    continue
            start, _ = occurrence.get_word_range()
            if any(begin <= start < end for begin, end in regions) or (
                current
                and any(begin <= start < end for begin, end in parameter_regions)
            ):
                # Substituting the initializer can change when an annotation
                # evaluates it and which bindings it observes.
                raise exceptions.RefactoringError(
                    "Cannot inline a variable referenced in a deferred annotation."
                )

    def _check_initializer_removal(self, resources, only_current):
        initializer = self.pyname.assignments[0].ast_node
        statement = next(
            (
                node
                for node in ast.walk(self.pymodule.get_ast())
                if isinstance(node, (ast.Assign, ast.AnnAssign))
                and node.value is initializer
            ),
            None,
        )
        statement_region = (
            codeanalyze.ASTLinesAdapter(self.pymodule.source_code)[statement]
            if statement is not None
            else None
        )
        local_annotation = isinstance(statement, ast.AnnAssign) and (
            isinstance(statement.target, ast.Name)
            and self.pymodule.get_scope()
            .get_inner_scope_for_line(statement.lineno)
            .get_kind()
            == "Function"
        )
        if isinstance(statement, ast.AnnAssign) and not local_annotation:
            raise exceptions.RefactoringError(
                "Cannot discard a variable annotation while inlining."
            )
        bound_name = isinstance(initializer, ast.Name) and _is_bound_initializer_name(
            self.pymodule, statement, initializer
        )
        if isinstance(initializer, ast.Name) and not bound_name:
            raise exceptions.RefactoringError(
                "Cannot discard an initializer name that may be unbound."
            )
        finder = occurrences.create_finder(
            self.project, self.name, self.pyname, imports=False
        )
        has_reads = False
        for resource in self.project.get_python_files():
            for occurrence in finder.find_occurrences(resource=resource):
                start, _ = occurrence.get_primary_range()
                if (
                    resource == self.resource
                    and statement_region is not None
                    and (statement_region[0] <= start < statement_region[1])
                ):
                    continue
                if occurrence.is_written() or occurrence.is_a_fixed_primary():
                    continue
                has_reads = True
                if resource not in resources or (
                    only_current
                    and resource == self.original
                    and not self.region[0] <= start < self.region[1]
                ):
                    raise exceptions.RefactoringError(
                        "Cannot remove a variable referenced outside the selected occurrences."
                    )
        if has_reads:
            return
        plain_assignment = (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
        )
        if not (plain_assignment or local_annotation) or not (
            bound_name or _is_pure_unused_initializer(initializer)
        ):
            raise exceptions.RefactoringError(
                "Cannot discard an unused variable initializer while inlining."
            )

    def _change_main_module(self, remove, only_current, docs):
        region = None
        if only_current and self.original == self.resource:
            region = self.region
        return _inline_variable(
            self.project,
            self.pymodule,
            self.pyname,
            self.name,
            remove=remove,
            region=region,
            docs=docs,
            check_lambda=True,
        )

    def _init_imports(self):
        vardef = _getvardef(self.pymodule, self.pyname)
        self.imported, self.imports = move.moving_code_with_imports(
            self.project, self.resource, vardef
        )

    def _change_module(self, resource, remove, only_current):
        filters = [occurrences.NoImportsFilter(), occurrences.PyNameFilter(self.pyname)]
        if only_current and resource == self.original:

            def check_aim(occurrence):
                start, end = occurrence.get_primary_range()
                if self.offset < start or end < self.offset:
                    return False

            filters.insert(0, check_aim)
        finder = occurrences.Finder(self.project, self.name, filters=filters)
        _check_lambda_occurrences(finder, self.project.get_pymodule(resource))
        changed = rename.rename_in_module(
            finder, self.imported, resource=resource, replace_primary=True
        )
        if remove:
            # An importing module without value reads still needs its import
            # cleaned up once the definition is discarded.
            changed = _remove_from(self.project, self.pyname, changed, resource)
        return changed

    def get_kind(self):
        return "variable"


class InlineParameter(_Inliner):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        if not isinstance(self.pyname, pynames.ParameterName):
            raise exceptions.RefactoringError(
                "Inline parameter should be performed on a parameter."
            )
        pyfunction = self.pyname.pyfunction
        functionutils._check_signature_parameters(pyfunction)
        if self.name not in [
            argument.arg for argument in pyfunction.get_ast().args.args
        ]:
            raise exceptions.RefactoringError(
                "Cannot inline the default of a list or keyword argument."
            )
        definition_info = functionutils.DefinitionInfo.read(pyfunction)
        indices = [
            index
            for index, (name, default) in enumerate(definition_info.args_with_defaults)
            if name == self.name
        ]
        if len(indices) != 1:
            raise exceptions.RefactoringError("Cannot resolve the parameter default.")
        resource, offset = self._function_location()
        index = indices[0]
        self.changers = [change_signature.ArgumentDefaultInliner(index)]
        self.signature = change_signature.ChangeSignature(
            self.project, resource, offset
        )

    def _function_location(self):
        pymodule, lineno = self.pyname.get_definition_location()
        resource = pymodule.get_resource()
        start = pymodule.lines.get_line_start(lineno)
        word_finder = worder.Worder(pymodule.source_code)
        offset = word_finder.find_function_offset(start)
        return resource, offset

    def get_changes(self, **kwds):
        """Get the changes needed by this refactoring

        See `rope.refactor.change_signature.ChangeSignature.get_changes()`
        for arguments.
        """
        return self.signature.get_changes(self.changers, **kwds)

    def get_kind(self):
        return "parameter"


def _join_lines(lines: List[str]) -> str:
    return "\n".join(lines)


class _ComplexExpressionVisitor:
    def __init__(self):
        self.is_complex_expression = False

    def _Set(self, node):
        self.is_complex_expression = True

    def _List(self, node):
        self.is_complex_expression = True

    def _Tuple(self, node):
        self.is_complex_expression = True

    def _Dict(self, node):
        self.is_complex_expression = True


class _DefinitionGenerator:
    unique_prefix = unique_prefix()

    def __init__(self, project, pyfunction, body=None):
        self.project = project
        self.pyfunction = pyfunction
        self.pymodule = pyfunction.get_module()
        self.resource = self.pymodule.get_resource()
        self.definition_info = self._get_definition_info()
        self.definition_params = self._get_definition_params()
        self._calculated_definitions = {}
        if body is not None:
            self.body = body
        else:
            self.body = sourceutils.get_body(self.pyfunction)

    def _get_definition_info(self):
        arguments = self.pyfunction.get_ast().args
        if arguments.kwonlyargs or arguments.vararg or arguments.kwarg:
            raise exceptions.RefactoringError(
                "Cannot inline functions with list and keyword arguments."
            )
        return functionutils.DefinitionInfo.read(self.pyfunction)

    def _get_definition_params(self):
        definition_info = self.definition_info
        paramdict = dict([pair for pair in definition_info.args_with_defaults])
        if (
            definition_info.args_arg is not None
            or definition_info.keywords_arg is not None
        ):
            raise exceptions.RefactoringError(
                "Cannot inline functions with list and keyword arguments."
            )
        if self.pyfunction.get_kind() == "classmethod":
            paramdict[definition_info.args_with_defaults[0][0]] = (
                self.pyfunction.parent.get_name()
            )
        return paramdict

    def get_function_name(self):
        return self.pyfunction.get_name()

    def get_definition(self, primary, pyname, call, host_vars=None, returns=False):
        # caching already calculated definitions
        if host_vars is None:
            host_vars = []
        return self._calculate_definition(primary, pyname, call, host_vars, returns)

    def _calculate_header(self, primary, pyname, call):
        # A header is created which initializes parameters
        # to the values passed to the function.
        call_info = functionutils.CallInfo.read(
            primary, pyname, self.definition_info, call
        )
        positional_only = {
            argument.arg for argument in self.pyfunction.get_ast().args.posonlyargs
        }
        if any(name in positional_only for name, value in call_info.keywords):
            raise exceptions.RefactoringError(
                "Cannot inline a positional-only parameter passed as a keyword."
            )
        paramdict = self.definition_params
        mapping = functionutils.ArgumentMapping(self.definition_info, call_info)
        for param_name, value in mapping.param_dict.items():
            paramdict[param_name] = value
        header = ""
        to_be_inlined = []
        for name, value in paramdict.items():
            if name != value and value is not None:
                header += name + " = " + value.replace("\n", " ") + "\n"
                to_be_inlined.append(name)
        return header, to_be_inlined

    def _calculate_definition(self, primary, pyname, call, host_vars, returns):
        header, to_be_inlined = self._calculate_header(primary, pyname, call)

        source = header + self.body
        mod = libutils.get_string_module(self.project, source)
        name_dict = mod.get_scope().get_names()
        all_names = [
            x
            for x in name_dict
            if not isinstance(name_dict[x], rope.base.builtins.BuiltinName)
        ]

        # If there is a name conflict, all variable names
        # inside the inlined function are renamed
        if set(all_names).intersection(set(host_vars)):
            prefix = next(_DefinitionGenerator.unique_prefix)
            guest = libutils.get_string_module(self.project, source, self.resource)

            to_be_inlined = [prefix + item for item in to_be_inlined]
            for item in all_names:
                pyname = guest[item]
                occurrence_finder = occurrences.create_finder(
                    self.project, item, pyname
                )
                source = rename.rename_in_module(
                    occurrence_finder, prefix + item, pymodule=guest
                )
                guest = libutils.get_string_module(self.project, source, self.resource)

        # parameters not reassigned inside the functions are now inlined.
        for name in to_be_inlined:
            pymodule = libutils.get_string_module(self.project, source, self.resource)
            pyname = pymodule[name]
            source = _inline_variable(self.project, pymodule, pyname, name)

        return self._replace_returns_with(source, returns)

    def _replace_returns_with(self, source, returns):
        result = []
        returned = None
        last_changed = 0
        for match in _DefinitionGenerator._get_return_pattern().finditer(source):
            for key, value in match.groupdict().items():
                if value and key == "return":
                    result.append(source[last_changed : match.start("return")])
                    if returns:
                        self._check_nothing_after_return(source, match.end("return"))
                        beg_idx = match.end("return")
                        returned = _join_lines(
                            source[beg_idx : len(source)].lstrip().splitlines(),
                        )
                        last_changed = len(source)
                    else:
                        current = match.end("return")
                        while current < len(source) and source[current] in " \t":
                            current += 1
                        last_changed = current
                        if current == len(source) or source[current] == "\n":
                            result.append("pass")
        result.append(source[last_changed:])
        return "".join(result), returned

    def _check_nothing_after_return(self, source, offset):
        lines = codeanalyze.SourceLinesAdapter(source)
        lineno = lines.get_line_number(offset)
        logical_lines = codeanalyze.LogicalLineFinder(lines)
        lineno = logical_lines.logical_line_in(lineno)[1]
        if source[lines.get_line_end(lineno) : len(source)].strip() != "":
            raise exceptions.RefactoringError(
                "Cannot inline functions with statements " + "after return statement."
            )

    @classmethod
    def _get_return_pattern(cls):
        if not hasattr(cls, "_return_pattern"):

            def named_pattern(name, list_):
                return "(?P<%s>" % name + "|".join(list_) + ")"

            comment_pattern = named_pattern("comment", [r"#[^\n]*"])
            string_pattern = named_pattern("string", [codeanalyze.get_string_pattern()])
            return_pattern = r"\b(?P<return>return)\b"
            cls._return_pattern = re.compile(
                comment_pattern + "|" + string_pattern + "|" + return_pattern
            )
        return cls._return_pattern


class _InlineFunctionCallsForModuleHandle:
    def __init__(self, project, resource, definition_generator, aim_offset=None):
        """Inlines occurrences

        If `aim` is not `None` only the occurrences that intersect
        `aim` offset will be inlined.

        """
        self.project = project
        self.generator = definition_generator
        self.resource = resource
        self.aim = aim_offset

    def occurred_inside_skip(self, change_collector, occurrence):
        if not occurrence.is_defined():
            raise exceptions.RefactoringError(
                "Cannot inline functions that reference themselves"
            )

    def occurred_outside_skip(self, change_collector, occurrence):
        start, end = occurrence.get_primary_range()
        # we remove out of date imports later
        if occurrence.is_in_import_statement():
            return
        # the function is referenced outside an import statement
        if not occurrence.is_called():
            raise exceptions.RefactoringError(
                "Reference to inlining function other than function call"
                " in <file: %s, offset: %d>" % (self.resource.path, start)
            )
        if self.aim is not None and (self.aim < start or self.aim > end):
            return
        end_parens = self._find_end_parens(self.source, end - 1)
        lineno = self.lines.get_line_number(start)
        start_line, end_line = self.pymodule.logical_lines.logical_line_in(lineno)
        line_start = self.lines.get_line_start(start_line)
        line_end = self.lines.get_line_end(end_line)

        returns = (
            self.source[line_start:start].strip() != ""
            or self.source[end_parens:line_end].strip() != ""
        )
        indents = sourceutils.get_indents(self.lines, start_line)
        primary, pyname = occurrence.get_primary_and_pyname()

        host = self.pymodule
        scope = host.scope.get_inner_scope_for_line(lineno)
        definition, returned = self.generator.get_definition(
            primary,
            pyname,
            self.source[start:end_parens],
            scope.get_names(),
            returns=returns,
        )

        end = min(line_end + 1, len(self.source))
        change_collector.add_change(
            line_start, end, sourceutils.fix_indentation(definition, indents)
        )
        if returns:
            name = returned
            if name is None:
                name = "None"
            change_collector.add_change(
                line_end,
                end,
                self.source[line_start:start] + name + self.source[end_parens:end],
            )

    def _find_end_parens(self, source, offset):
        finder = worder.Worder(source)
        return finder.get_word_parens_range(offset)[1]

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


def _inline_variable(
    project,
    pymodule,
    pyname,
    name,
    remove=True,
    region=None,
    docs=False,
    check_lambda=False,
):
    definition = _getvardef(pymodule, pyname)
    start, end = _assigned_lineno(pymodule, pyname)
    assignment_node = _find_assignment_node(pymodule, pyname.assignments[0].ast_node)

    occurrence_finder = occurrences.create_finder(project, name, pyname, docs=docs)
    if check_lambda:
        _check_lambda_occurrences(
            occurrence_finder, pymodule, region=region, writes=False
        )
    if remove:
        removal = _get_assignment_removal(
            pymodule.source_code,
            assignment_node,
            name,
            start,
            end,
            occurrence_finder,
            pymodule,
        )
        return _rename_and_remove_assignment(
            occurrence_finder, definition, pymodule, removal, region
        )

    changed_source = rename.rename_in_module(
        occurrence_finder,
        definition,
        pymodule=pymodule,
        replace_primary=True,
        writes=False,
        region=region,
    )
    return changed_source if changed_source is not None else pymodule.source_code


def _is_bound_initializer_name(pymodule, statement, initializer):
    if statement is None:
        return False
    scope = pymodule.get_scope().get_inner_scope_for_line(statement.lineno)
    if scope.get_kind() == "Class":
        # Class-body aliasing stays conservative, but a builtin initializer
        # name is always bound wherever it is substituted.
        return isinstance(
            evaluate.eval_node(scope, initializer), rope.base.builtins.BuiltinName
        )
    pyname = evaluate.eval_node(scope, initializer)
    if any(
        isinstance(node, ast.Name)
        and node.id == initializer.id
        and isinstance(node.ctx, ast.Del)
        and evaluate.eval_node(
            pymodule.get_scope().get_inner_scope_for_line(node.lineno), node
        )
        is pyname
        for node in ast.walk(pymodule.get_ast())
    ):
        return False
    if isinstance(pyname, rope.base.builtins.BuiltinName):
        return True
    if isinstance(pyname, pynames.ParameterName):
        return True
    parents = {
        child: node
        for node in ast.walk(pymodule.get_ast())
        for child in ast.iter_child_nodes(node)
    }
    anchor = statement
    while anchor in parents:
        owner = parents[anchor]
        for _, block in ast.iter_fields(owner):
            if not isinstance(block, list) or anchor not in block:
                continue
            for previous in reversed(block[: block.index(anchor)]):
                binding_scope = pymodule.get_scope().get_inner_scope_for_line(
                    previous.lineno
                )
                if (
                    isinstance(previous, ast.Assign)
                    and len(previous.targets) == 1
                    and isinstance(previous.targets[0], ast.Name)
                ):
                    if previous.targets[0].id == initializer.id:
                        if (
                            evaluate.eval_node(binding_scope, previous.targets[0])
                            is pyname
                        ):
                            return True
                        break
                    if _is_pure_unused_initializer(previous.value):
                        continue
                if isinstance(
                    previous, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    if (
                        previous.name == initializer.id
                        and pyname is not None
                        and pyname.get_definition_location()
                        == (pymodule, previous.lineno)
                    ):
                        return True
                    if isinstance(previous, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        arguments = previous.args
                        parameters = (
                            arguments.posonlyargs
                            + arguments.args
                            + arguments.kwonlyargs
                            + [arguments.vararg, arguments.kwarg]
                        )
                        if not (
                            previous.decorator_list
                            or arguments.defaults
                            or any(arguments.kw_defaults)
                            or previous.returns
                            or any(
                                parameter.annotation
                                for parameter in parameters
                                if parameter is not None
                            )
                            or getattr(previous, "type_params", ())
                        ):
                            continue
                    break
                if isinstance(previous, (ast.Import, ast.ImportFrom)):
                    matching = any(
                        (alias.asname or alias.name.split(".")[0]) == initializer.id
                        for alias in previous.names
                    )
                    if (
                        matching
                        and evaluate.eval_node(binding_scope, initializer) is pyname
                    ):
                        return True
                    break
                if isinstance(previous, ast.Pass):
                    continue
                break
        anchor = owner
    return False


def _is_pure_unused_initializer(node):
    # literal_eval accepts set(); even that name may be rebound to user code.
    if any(isinstance(child, ast.Call) for child in ast.walk(node)):
        return False
    try:
        ast.literal_eval(node)
    except (TypeError, ValueError):
        return False
    return True


def _getvardef(pymodule, pyname):
    assignment = pyname.assignments[0]
    if assignment.levels:
        raise exceptions.RefactoringError("Cannot inline tuple assignments.")

    assignment_node = _find_assignment_node(pymodule, assignment.ast_node)
    if assignment_node is not None:
        source = pymodule.source_code
        node_start, node_end = patchedast.node_region(assignment_node)
        value_start, _ = patchedast.node_region(assignment.ast_node)
        separator = source.rfind("=", node_start, value_start)
        if separator != -1:
            return source[separator + 1 : node_end].strip()

    lines = pymodule.lines
    start, end = _assigned_lineno(pymodule, pyname)
    definition_with_assignment = _join_lines(
        [lines.get_line(n) for n in range(start, end + 1)],
    )
    definition = definition_with_assignment[
        definition_with_assignment.index("=") + 1 :
    ].strip()
    return definition


def _find_assignment_node(pymodule, value_node):
    if value_node is None:
        return None
    module_ast = pymodule.get_ast()
    patchedast.patch_ast(module_ast, pymodule.source_code)
    for node in ast.walk(module_ast):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is value_node:
            return node


def _rename_and_remove_assignment(finder, definition, pymodule, removal, region):
    source = pymodule.source_code
    remove_start, remove_end, replacement = removal
    change_collector = codeanalyze.ChangeCollector(source)
    for occurrence in finder.find_occurrences(pymodule=pymodule):
        if occurrence.is_a_fixed_primary() or occurrence.is_written():
            continue
        occurrence_start, occurrence_end = occurrence.get_primary_range()
        if occurrence_start < remove_end and occurrence_end > remove_start:
            continue
        if region is None or region[0] <= occurrence_start < region[1]:
            change_collector.add_change(occurrence_start, occurrence_end, definition)
    change_collector.add_change(remove_start, remove_end, replacement)
    changed_source = change_collector.get_changed()
    return changed_source if changed_source is not None else source


def _get_assignment_removal(
    source, assignment_node, name, start, end, finder, pymodule
):
    if assignment_node is None:
        return _get_logical_line_removal(source, start, end)

    targets = (
        assignment_node.targets
        if isinstance(assignment_node, ast.Assign)
        else [assignment_node.target]
    )
    target_index = _find_assignment_target_index(targets, name, finder, pymodule)
    if target_index is None:
        return _get_logical_line_removal(source, start, end)

    if len(targets) > 1:
        following_nodes = [*targets[1:], assignment_node.value]
        segment_ends = []
        for target, following in zip(targets, following_nodes):
            _, target_end = patchedast.node_region(target)
            following_start, _ = patchedast.node_region(following)
            separator = source.find("=", target_end, following_start)
            if separator == -1:
                return _get_logical_line_removal(source, start, end)
            segment_ends.append(
                _skip_assignment_gap(source, separator + 1, following_start)
            )

        node_start, _ = patchedast.node_region(assignment_node)
        segment_starts = [node_start, *segment_ends[:-1]]
        return segment_starts[target_index], segment_ends[target_index], ""

    node_start, node_end = patchedast.node_region(assignment_node)
    lines = codeanalyze.SourceLinesAdapter(source)
    line_start = lines.get_line_start(assignment_node.lineno)
    line_end = lines.get_line_end(assignment_node.end_lineno)

    remove_end = node_end
    while remove_end < line_end and source[remove_end] in " \t":
        remove_end += 1
    if remove_end < line_end and source[remove_end] == ";":
        remove_end += 1
        while remove_end < line_end and source[remove_end] in " \t":
            remove_end += 1
        return node_start, remove_end, ""

    remove_start = node_start
    while remove_start > line_start and source[remove_start - 1] in " \t":
        remove_start -= 1
    if remove_start > line_start and source[remove_start - 1] == ";":
        remove_start -= 1
        while remove_start > line_start and source[remove_start - 1] in " \t":
            remove_start -= 1
        return remove_start, node_end, ""

    return _get_logical_line_removal(source, start, end)


def _target_matches_name(target, name):
    return (isinstance(target, ast.Name) and target.id == name) or (
        isinstance(target, ast.Attribute) and target.attr == name
    )


def _find_assignment_target_index(targets, name, finder, pymodule):
    for occurrence in finder.find_occurrences(pymodule=pymodule):
        occurrence_start, occurrence_end = occurrence.get_word_range()
        for index, target in enumerate(targets):
            target_start, target_end = patchedast.node_region(target)
            if target_start <= occurrence_start and occurrence_end <= target_end:
                return index

    matching_indexes = [
        index
        for index, target in enumerate(targets)
        if _target_matches_name(target, name)
    ]
    if len(matching_indexes) == 1:
        return matching_indexes[0]


def _skip_assignment_gap(source, offset, limit):
    while offset < limit:
        if source[offset] in " \t\r\n":
            offset += 1
        elif source.startswith("\\\r\n", offset):
            offset += 3
        elif source.startswith("\\\n", offset):
            offset += 2
        else:
            break
    return offset


def _get_logical_line_removal(source, start, end):
    lines = codeanalyze.SourceLinesAdapter(source)
    return lines.get_line_start(start), lines.get_line_end(end) + 1, ""


def _assigned_lineno(pymodule, pyname):
    definition_line = pyname.assignments[0].ast_node.lineno
    return pymodule.logical_lines.logical_line_in(definition_line)


def _add_imports(project, source, resource, imports):
    if not imports:
        return source
    pymodule = libutils.get_string_module(project, source, resource)
    module_import = importutils.get_module_imports(project, pymodule)
    for import_info in imports:
        module_import.add_import(import_info)
    source = module_import.get_changed_source()
    pymodule = libutils.get_string_module(project, source, resource)
    import_tools = importutils.ImportTools(project)
    return import_tools.organize_imports(pymodule, unused=False, sort=False)


def _get_pyname(project, resource, offset):
    pymodule = project.get_pymodule(resource)
    word_range = worder.Worder(pymodule.source_code, True).get_word_range(offset)
    if word_range in _lambda_owned_name_ranges(pymodule):
        raise exceptions.RefactoringError(
            "Inlining lambda-local bindings is not supported."
        )
    pyname = evaluate.eval_location(pymodule, offset)
    if isinstance(pyname, pynames.ImportedName):
        pyname = pyname._get_imported_pyname()
    return pyname


def _check_lambda_occurrences(finder, pymodule, region=None, writes=True):
    owned = _lambda_owned_name_ranges(pymodule)
    if not owned:
        return
    for occurrence in finder.find_occurrences(pymodule=pymodule):
        if occurrence.is_a_fixed_primary():
            continue
        if not writes and occurrence.is_written():
            continue
        start, _ = occurrence.get_primary_range()
        if region is not None and not region[0] <= start < region[1]:
            continue
        if occurrence.get_word_range() in owned:
            raise exceptions.RefactoringError(
                "Cannot inline a variable into lambda-local bindings."
            )


def _lambda_owned_name_ranges(pymodule):
    """Find lambda-local tokens and attribute lookups that depend on them."""
    ranges = set()
    lines = pymodule.lines
    words = worder.Worder(pymodule.source_code, True)

    def offset(lineno, column):
        # AST columns count UTF-8 bytes; Rope offsets count source characters.
        prefix = lines.get_line(lineno).encode("utf-8")[:column]
        return lines.get_line_start(lineno) + len(prefix.decode("utf-8"))

    def node_range(node):
        return (
            offset(node.lineno, node.col_offset),
            offset(node.end_lineno, node.end_col_offset),
        )

    def record(node):
        ranges.add(node_range(node))

    def defaults(node):
        return [*node.args.defaults, *filter(None, node.args.kw_defaults)]

    def uses_local_name(node):
        if isinstance(node, ast.Name):
            return node_range(node) in ranges
        # Creating a lambda does not evaluate its body or bind its parameters.
        children = (
            defaults(node)
            if isinstance(node, ast.Lambda)
            else list(ast.iter_child_nodes(node))
        )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Lambda):
            children.append(node.func.body)
        return any(uses_local_name(child) for child in children)

    def assigned_names(node):
        names = set()
        if isinstance(node, ast.NamedExpr):
            names.add(node.target.id)
        children = (
            defaults(node)
            if isinstance(node, ast.Lambda)
            else ast.iter_child_nodes(node)
        )
        for child in children:
            names.update(assigned_names(child))
        return names

    def visit(node, bound):
        if isinstance(node, ast.Lambda):
            arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            arguments.extend(arg for arg in (node.args.vararg, node.args.kwarg) if arg)
            for arg in arguments:
                record(arg)
            for default in defaults(node):
                visit(default, bound)
            local = bound | {arg.arg for arg in arguments} | assigned_names(node.body)
            visit(node.body, local)
        elif isinstance(
            node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
        ):
            # The first iterable is outside the comprehension's local bindings.
            visit(node.generators[0].iter, bound)
            names = {
                child.id
                for generator in node.generators
                for child in ast.walk(generator.target)
                if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store)
            }
            local = bound - names
            for index, generator in enumerate(node.generators):
                visit(generator.target, local)
                if index:
                    visit(generator.iter, local)
                for condition in generator.ifs:
                    visit(condition, local)
            values = (
                [node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]
            )
            for value in values:
                visit(value, local)
        else:
            if isinstance(node, ast.Name) and node.id in bound:
                record(node)
            for child in ast.iter_child_nodes(node):
                visit(child, bound)
            if isinstance(node, ast.Attribute) and uses_local_name(node.value):
                # The attr token resolves through the receiver, not its spelling.
                end = offset(node.end_lineno, node.end_col_offset)
                ranges.add(words.get_word_range(end - 1))

    visit(pymodule.get_ast(), set())
    return ranges


def _remove_from(project, pyname, source, resource):
    pymodule = libutils.get_string_module(
        project, source if source is not None else resource.read(), resource
    )
    module_import = importutils.get_module_imports(project, pymodule)
    if module_import.remove_pyname(pyname):
        source = module_import.get_changed_source()
    return source
