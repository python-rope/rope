import rope.base.pynames
import rope.base.pyobjects
from rope.base import ast, exceptions


class Scope(object):

    def __init__(self, pycore, pyobject, parent_scope):
        self.pycore = pycore
        self.pyobject = pyobject
        self.parent = parent_scope
        self.scopes = None

    def get_names(self):
        """Return the names defined in this scope"""
        return self.pyobject.get_attributes()

    def get_name(self, name):
        """Return name `PyName` defined in this scope"""
        if name not in self.get_names():
            raise exceptions.NameNotFoundError('name %s not found' % name)
        return self.get_names()[name]

    def get_scopes(self):
        """Return the subscopes of this scope.

        The returned scopes should be sorted by the order they appear
        """
        if self.scopes is None:
            self.scopes = self._create_scopes()
        return self.scopes

    def lookup(self, name):
        if name in self.get_names():
            return self.get_names()[name]
        if self.parent is not None:
            return self.parent._propagated_lookup(name)
        return None

    def get_propagated_names(self):
        """Return the names defined in this scope that are visible from
        scopes contained in this scope

        This method returns the same dictionary returned by
        `get_names()` except for `ClassScope` which returns an empty
        dict.

        """
        return self.get_names()

    def _propagated_lookup(self, name):
        if name in self.get_propagated_names():
            return self.get_propagated_names()[name]
        if self.parent is not None:
            return self.parent._propagated_lookup(name)
        return None

    def _create_scopes(self):
        block_objects = [pyname.get_object() for pyname in
                         self.pyobject._get_structural_attributes().values()
                         if isinstance(pyname, rope.base.pynames.DefinedName)]
        def block_compare(x, y):
            return cmp(x.get_ast().lineno, y.get_ast().lineno)
        block_objects.sort(cmp=block_compare)
        return [block.get_scope() for block in block_objects]

    def _get_global_scope(self):
        current = self
        while current.parent is not None:
            current = current.parent
        return current

    def get_start(self):
        return self.pyobject.get_ast().lineno

    def get_end(self):
        global_scope = self._get_global_scope()
        return global_scope._get_scope_finder().find_scope_end(self)

    def get_kind(self):
        pass


class GlobalScope(Scope):

    def __init__(self, pycore, module):
        super(GlobalScope, self).__init__(pycore, module, None)
        self.scope_finder = None
        self.names = module._get_concluded_data()

    def get_start(self):
        return 1

    def get_kind(self):
        return 'Module'

    def get_name(self, name):
        try:
            return self.pyobject.get_attribute(name)
        except exceptions.AttributeNotFoundError:
            if name in self.builtin_names:
                return self.builtin_names[name]
            raise exceptions.NameNotFoundError('name %s not found' % name)

    def get_names(self):
        if self.names.get() is None:
            result = dict(super(GlobalScope, self).get_names())
            result.update(self.builtin_names)
            self.names.set(result)
        return self.names.get()

    def get_inner_scope_for_line(self, lineno, indents=None):
        return self._get_scope_finder().get_holding_scope(self, lineno, indents)

    def get_inner_scope_for_offset(self, offset):
        return self._get_scope_finder().get_holding_scope_for_offset(self, offset)

    def _get_scope_finder(self):
        if self.scope_finder is None:
            self.scope_finder = _HoldingScopeFinder(self.pyobject)
        return self.scope_finder

    def _get_builtin_names(self):
        return rope.base.builtins.builtins

    builtin_names = property(_get_builtin_names)



class FunctionScope(Scope):

    def __init__(self, pycore, pyobject):
        super(FunctionScope, self).__init__(pycore, pyobject,
                                            pyobject.parent.get_scope())
        self.names = None
        self.returned_asts = None
        self.is_generator = None

    def _get_names(self):
        if self.names is None:
            self._visit_function()
        return self.names

    def _visit_function(self):
        if self.names is None:
            new_visitor = rope.base.pyobjects._FunctionVisitor(self.pycore,
                                                               self.pyobject)
            for n in ast.get_child_nodes(self.pyobject.get_ast()):
                ast.walk(n, new_visitor)
            self.names = self.pyobject.get_parameters()
            self.names.update(new_visitor.names)
            self.returned_asts = new_visitor.returned_asts
            self.is_generator = new_visitor.generator

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
        block_objects = [pyname.get_object()
                         for pyname in self._get_names().values()
                         if isinstance(pyname, rope.base.pynames.DefinedName)]
        def block_compare(x, y):
            return cmp(x.get_ast().lineno, y.get_ast().lineno)
        block_objects.sort(cmp=block_compare)
        result = [block.get_scope() for block in block_objects]
        return result

    def get_kind(self):
        return 'Function'

    def invalidate_data(self):
        for pyname in self.get_names().values():
            if isinstance(pyname, (rope.base.pynames.AssignedName,
                                   rope.base.pynames.EvaluatedName)):
                pyname.invalidate()
                

class ClassScope(Scope):

    def __init__(self, pycore, pyobject):
        super(ClassScope, self).__init__(pycore, pyobject,
                                         pyobject.parent.get_scope())

    def get_kind(self):
        return 'Class'

    def get_propagated_names(self):
        return {}


class _HoldingScopeFinder(object):

    def __init__(self, pymodule):
        self.source_code = pymodule.source_code
        self.lines = pymodule.lines

    def get_indents(self, lineno):
        return rope.base.codeanalyze.count_line_indents(
            self.lines.get_line(lineno))

    def get_location(self, offset):
        current_pos = 0
        lineno = 1
        while current_pos + len(self.lines.get_line(lineno)) < offset:
            current_pos += len(self.lines.get_line(lineno)) + 1
            lineno += 1
        return (lineno, offset - current_pos)

    def _get_scope_indents(self, scope):
        return self.get_indents(scope.get_start())

    def get_holding_scope(self, module_scope, lineno, line_indents=None):
        line_indents = line_indents
        if line_indents is None:
            line_indents = self.get_indents(lineno)
        scopes = [module_scope]
        current_scope = module_scope
        while current_scope is not None and \
              (current_scope.get_kind() == 'Module' or
               self._get_scope_indents(current_scope) <= line_indents):
            scopes.append(current_scope)
            if current_scope.get_start() == lineno and \
               current_scope.get_kind() != 'Module':
                return current_scope
            new_scope = None
            for scope in current_scope.get_scopes():
                if scope.get_start() <= lineno:
                    new_scope = scope
                else:
                    break
            current_scope = new_scope
        while len(scopes) > 1 and \
              (line_indents <= self._get_scope_indents(scopes[-1]) and
               not (line_indents == self._get_scope_indents(scopes[-1]) and
                    lineno == scopes[-1].get_start())):
            scopes.pop()
        return scopes[-1]

    def _get_body_indents(self, scope):
        return self.get_indents(scope.pyobject.get_ast().body[0].lineno)

    def get_holding_scope_for_offset(self, scope, offset):
        return self.get_holding_scope(scope, self.lines.get_line_number(offset))

    def find_scope_end(self, scope):
        if not scope.parent:
            return self.lines.length()
        end = scope.pyobject.get_ast().body[-1].lineno
        for l in range(end + 1, self.lines.length() + 1):
            if self.lines.get_line(l).strip() != '' and \
               not self.lines.get_line(l).strip().startswith('#'):
                if self.get_indents(l) <= self._get_scope_indents(scope):
                    return end
                else:
                    end = l
        return end
