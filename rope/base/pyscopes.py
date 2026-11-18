from rope.base import ast, codeanalyze, exceptions, pynames, utils


class Scope:
    def __init__(self, pycore, pyobject, parent_scope):
        self.pycore = pycore
        self.pyobject = pyobject
        self.parent = parent_scope

    def get_names(self):
        """Return the names defined or imported in this scope"""
        return self.pyobject.get_attributes()

    def get_defined_names(self):
        """Return the names defined in this scope"""
        return self.pyobject._get_structural_attributes()

    def get_name(self, name):
        """Return name `PyName` defined in this scope"""
        if name not in self.get_names():
            raise exceptions.NameNotFoundError("name %s not found" % name)
        return self.get_names()[name]

    def __getitem__(self, key):
        """The same as ``get_name(key)``"""
        return self.get_name(key)

    def __contains__(self, key):
        """The same as ``key in self.get_names()``"""
        return key in self.get_names()

    def get_scopes(self):
        """Return the subscopes of this scope

        The returned scopes should be sorted by the order they appear.
        """
        scopes = getattr(self, "_scopes", None)
        if scopes is None:
            scopes = self._create_scopes()
            # While the owner is being created, the recursion guard in
            # _get_structural_attributes returns a temporary empty set; caching
            # that answer (saveit) would leave a permanent empty list for
            # structural references. The cache is only stored once the owner's
            # defined objects exist.
            if getattr(self.pyobject, "defineds", None) is not None:
                self._scopes = scopes
        return scopes

    def lookup(self, name):
        if name in self.get_names():
            return self.get_names()[name]
        if self.parent is not None:
            return self.parent._propagated_lookup(name)
        return None

    def get_binding_scopes(self):
        module = self._get_global_scope().pyobject
        return module.get_source_binding_index().children_of(self)

    def get_propagated_names(self):
        """Return the visible names of this scope

        Return the names defined in this scope that are visible from
        scopes containing this scope.  This method returns the same
        dictionary returned by `get_names()` except for `ClassScope`
        which returns an empty dict.
        """
        return self.get_names()

    def _propagated_lookup(self, name):
        if name in self.get_propagated_names():
            return self.get_propagated_names()[name]
        if self.parent is not None:
            return self.parent._propagated_lookup(name)
        return None

    def _create_scopes(self):
        return [
            pydefined.get_scope() for pydefined in self.pyobject._get_defined_objects()
        ]

    def _get_global_scope(self):
        current = self
        while current.parent is not None:
            current = current.parent
        return current

    def get_start(self):
        return self.pyobject.get_ast().lineno

    def get_body_start(self):
        body = self.pyobject.get_ast().body
        if body:
            return body[0].lineno
        return self.get_start()

    @utils.saveit
    def get_end(self):
        pymodule = self._get_global_scope().pyobject
        return pymodule.logical_lines.logical_line_in(self.logical_end)[1]

    @utils.saveit
    def get_logical_end(self):
        global_scope = self._get_global_scope()
        return global_scope._scope_finder.find_scope_end(self)

    start = property(get_start)
    end = property(get_end)
    logical_end = property(get_logical_end)

    def get_kind(self):
        pass

    @utils.saveit
    def get_region(self):
        global_scope = self._get_global_scope()
        node = self.pyobject.get_ast()
        if isinstance(node, ast.Module):
            return (0, len(global_scope._get_source()))
        start, end = global_scope._ast_lines[node]
        if start is None or end is None:
            raise exceptions.RopeError("Scope AST has no complete source positions")
        decorators = getattr(node, "decorator_list", ())
        if decorators:
            decorator_start, _ = global_scope._ast_lines[decorators[0]]
            if decorator_start is None:
                raise exceptions.RopeError("Decorator AST has no source positions")
            start = global_scope._region_source.rfind_token("@", 0, decorator_start)
            if start is None:
                raise exceptions.RopeError("Scope decorator has no source marker")
        return (start, end)

    def in_region(self, offset):
        """Checks if offset is in scope region"""

        region = self.get_region()
        return region[0] < offset < region[1]


class GlobalScope(Scope):
    def __init__(self, pycore, module):
        super().__init__(pycore, module, None)
        self.names = module._get_concluded_data()
        self._inner_scopes_for_lines = {}

    def get_start(self):
        return 1

    def get_kind(self):
        return "Module"

    def get_name(self, name):
        try:
            return self.pyobject[name]
        except exceptions.AttributeNotFoundError:
            if name in self.builtin_names:
                return self.builtin_names[name]
            raise exceptions.NameNotFoundError("name %s not found" % name)

    @property
    @utils.saveit
    def _ast_lines(self):
        return codeanalyze.ASTLinesAdapter(self._get_source())

    @property
    @utils.saveit
    def _region_source(self):
        # Deferred import: rope.refactor's package init pulls the analysis
        # stack, which reaches evaluate; evaluate subclasses this module's
        # TemporaryScope at import time, so a module-level import here is
        # circular when pyscopes loads first.
        from rope.refactor import patchedast

        return patchedast._Source(self._get_source())

    def _get_source(self):
        return self.pyobject.source_code

    def get_names(self):
        if self.names.get() is None:
            result = dict(self.builtin_names)
            result.update(super().get_names())
            self.names.set(result)
        return self.names.get()

    def get_inner_scope_for_line(self, lineno, indents=None):
        # The holding scope for a (line, indents) pair is a structural
        # property of the module: inference follows thousands of name paths
        # through the same lines, so the tree walk runs once per pair for the
        # lifetime of this module scope (rebuilt with its pymodule).
        key = (lineno, indents)
        cached = self._inner_scopes_for_lines.get(key)
        if cached is None:
            cached = self._scope_finder.get_holding_scope(self, lineno, indents)
            self._inner_scopes_for_lines[key] = cached
        return cached

    def get_inner_scope_for_offset(self, offset):
        return self._scope_finder.get_holding_scope_for_offset(self, offset)

    def get_structural_scope_for_offset(self, offset):
        return self._scope_finder.get_holding_scope_for_offset(self, offset)

    @property
    @utils.saveit
    def _scope_finder(self):
        return _HoldingScopeFinder(self.pyobject)

    @property
    def builtin_names(self):
        # Deferred import: builtins imports evaluate, whose SourceValueScope
        # subclasses this module's TemporaryScope at import time; a module-level
        # import here re-enters a half-initialized pyscopes (circular).
        import rope.base.builtins  # Use full qualification for clarity.

        return rope.base.builtins.builtins.get_attributes()


class BuiltinModuleScope(Scope):
    """Module scope over a C/builtin module.

    Builtin modules carry no source, concluded data, or child scopes; their
    names are the live attribute mapping of the native module.
    """

    def __init__(self, pyobject):
        super().__init__(getattr(pyobject, "pycore", None), pyobject, None)
        self.names = pyobject.attributes

    def get_start(self):
        return 1

    def get_kind(self):
        return "Module"


class ComprehensionScope(Scope):
    def __init__(self, pycore, pyobject, visitor):
        super().__init__(pycore, pyobject, pyobject.parent.get_scope())
        self.names = None
        self.returned_asts = None
        self.defineds = None
        self.visitor = visitor

    def _get_names(self):
        if self.names is None:
            self._visit_comprehension()
        return self.names

    def get_names(self):
        return self._get_names()

    def _visit_comprehension(self):
        if self.names is None:
            new_visitor = self.visitor(self.pycore, self.pyobject)
            for node in ast.iter_child_nodes(self.pyobject.get_ast()):
                new_visitor.visit(node)
            self.names = dict(self.parent.get_names())
            self.names.update(new_visitor.names)
            self.defineds = new_visitor.defineds

    def get_logical_end(self):
        return self.get_start()

    logical_end = property(get_logical_end)

    def get_body_start(self):
        return self.get_start()


class FunctionScope(Scope):
    def __init__(self, pycore, pyobject, visitor):
        super().__init__(pycore, pyobject, pyobject.parent.get_scope())
        self.names = None
        self.returned_asts = None
        self.is_generator = None
        self.defineds = None
        self.visitor = visitor

    def _get_names(self):
        if self.names is None:
            self._visit_function()
        module = self.pyobject.get_module()
        if module.requires_header_bindings():
            module._get_source_binding_index().prepare_header_bindings(self)
        return self.names

    def _visit_function(self):
        if self.names is None:
            new_visitor = self.visitor(self.pycore, self.pyobject)
            for n in self.pyobject.get_ast().body:
                new_visitor.visit(n)
            self.names = new_visitor.names
            parameters = self.pyobject.get_parameters()
            for name, parameter in parameters.items():
                assigned = self.names.get(name)
                if isinstance(assigned, pynames.AssignedName):
                    assigned.initial_binding = parameter
                    parameter.assigned_value = assigned
            self.names.update(parameters)
            self.returned_asts = new_visitor.returned_asts
            self.is_generator = new_visitor.generator
            self.defineds = new_visitor.defineds

    def _get_returned_asts(self):
        if self.names is None:
            self._visit_function()
        return self.returned_asts

    def _is_generator(self):
        if self.is_generator is None:
            self._get_returned_asts()
        return self.is_generator

    def get_names(self):
        return self._get_names()

    def _create_scopes(self):
        if self.defineds is None:
            self._visit_function()
        return [pydefined.get_scope() for pydefined in self.defineds]

    def get_kind(self):
        return "Function"

    def invalidate_data(self):
        for pyname in self.get_names().values():
            if isinstance(pyname, (pynames.AssignedName, pynames.EvaluatedName)):
                pyname.invalidate()


class ClassScope(Scope):
    def __init__(self, pycore, pyobject):
        super().__init__(pycore, pyobject, pyobject.parent.get_scope())

    def get_kind(self):
        return "Class"

    def get_propagated_names(self):
        return {}


class _HoldingScopeFinder:
    def __init__(self, pymodule):
        self.pymodule = pymodule

    def get_indents(self, lineno):
        return codeanalyze.count_line_indents(self.lines.get_line(lineno))

    def _get_scope_indents(self, scope):
        return self.get_indents(scope.get_start())

    def get_holding_scope(self, module_scope, lineno, line_indents=None):
        if line_indents is None:
            line_indents = self.get_indents(lineno)
        current_scope = module_scope
        new_scope = current_scope
        while new_scope is not None and (
            new_scope.get_kind() == "Module"
            or self._get_scope_indents(new_scope) <= line_indents
        ):
            current_scope = new_scope
            if (
                current_scope.get_start() == lineno
                and current_scope.get_kind() != "Module"
            ):
                return current_scope
            new_scope = None
            for scope in current_scope.get_scopes():
                if scope.get_start() <= lineno:
                    if lineno <= scope.get_end():
                        new_scope = scope
                        break
                else:
                    break
        return current_scope

    def _is_empty_line(self, lineno):
        line = self.lines.get_line(lineno)
        return line.strip() == "" or line.lstrip().startswith("#")

    def _get_body_indents(self, scope):
        return self.get_indents(scope.get_body_start())

    @staticmethod
    def get_holding_scope_for_offset(scope, offset):
        for inner_scope in scope.get_scopes():
            if inner_scope.in_region(offset):
                return _HoldingScopeFinder.get_holding_scope_for_offset(
                    inner_scope, offset
                )
        return scope

    def find_scope_end(self, scope):
        if not scope.parent:
            return self.lines.length()
        end = scope.pyobject.get_ast().body[-1].lineno
        scope_start = self.pymodule.logical_lines.logical_line_in(scope.start)
        if scope_start[1] >= end:
            # handling one-liners
            body_indents = self._get_scope_indents(scope) + 4
        else:
            body_indents = self._get_body_indents(scope)
        for line_start in self.logical_lines.generate_starts(
            min(end + 1, self.lines.length()), self.lines.length() + 1
        ):
            if not self._is_empty_line(line_start):
                if self.get_indents(line_start) < body_indents:
                    return end
                else:
                    end = line_start
        return end

    @property
    def lines(self):
        return self.pymodule.lines

    @property
    def code(self):
        return self.pymodule.source_code

    @property
    def logical_lines(self):
        return self.pymodule.logical_lines


class TemporaryScope(Scope):
    """Currently used for list comprehensions and generator expressions

    These scopes do not appear in the `get_scopes()` method of their
    parent scopes.
    """

    def __init__(self, pycore, parent_scope, names):
        super().__init__(pycore, parent_scope.pyobject, parent_scope)
        self.names = names

    def get_names(self):
        return self.names

    def get_defined_names(self):
        return self.names

    def _create_scopes(self):
        return []

    def get_kind(self):
        return "Temporary"
