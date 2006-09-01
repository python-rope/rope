import compiler

import rope.codeanalyze
import rope.pyobjects

class Scope(object):

    def __init__(self, pycore, pyobject, parent_scope):
        self.pycore = pycore
        self.pyobject = pyobject
        self.parent = parent_scope
        self.scopes = None
    
    def get_names(self):
        """Returns the names defined in this scope"""
        return self.pyobject.get_attributes()

    def get_scopes(self):
        """Returns the subscopes of this scope.
        
        The returned scopes should be sorted by the order they appear
        """
        if self.scopes == None:
            self.scopes = self._create_scopes()
        return self.scopes

    def _create_scopes(self):
        block_objects = [pyname.object for pyname in
                         self.pyobject.get_attributes().values()
                         if pyname.has_block()]
        def block_compare(x, y):
            return cmp(x._get_ast().lineno, y._get_ast().lineno)
        block_objects.sort(cmp=block_compare)
        result = [block.get_scope() for block in block_objects]
        return result
    
    def _get_global_scope(self):
        current = self
        while current.parent is not None:
            current = current.parent
        return current

    def get_start(self):
        return self.pyobject._get_ast().lineno
    
    def get_end(self):
        global_scope = self._get_global_scope()
        return _HoldingScopeFinder(global_scope.pyobject.source_code).find_scope_end(self)

    def get_kind(self):
        pass
    
    def lookup(self, name):
        if name in self.get_names():
            return self.get_names()[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        return None


class GlobalScope(Scope):

    def __init__(self, pycore, module):
        super(GlobalScope, self).__init__(pycore, module, None)

    def get_start(self):
        return 1

    def get_kind(self):
        return 'Module'
    
    def get_inner_scope_for_line(self, lineno, indents=None):
        return _HoldingScopeFinder(self.pyobject.source_code).\
               get_holding_scope(self, lineno, indents)


class FunctionScope(Scope):
    
    def __init__(self, pycore, pyobject):
        super(FunctionScope, self).__init__(pycore, pyobject,
                                            pyobject.parent.get_scope())
        self.names = None
        self.returned_asts = None
    
    def _get_names(self):
        if self.names == None:
            self._visit_function()
        return self.names
    
    def _visit_function(self):
        if self.names == None:
            new_visitor = rope.pyobjects._FunctionVisitor(self.pycore,
                                                          self.pyobject)
            for n in self.pyobject._get_ast().getChildNodes():
                compiler.walk(n, new_visitor)
            self.names = self.pyobject._get_parameters()
            self.names.update(new_visitor.names)
            self.returned_asts = new_visitor.returned_asts
    
    def _get_returned_asts(self):
        if self.names == None:
            self._visit_function()
        return self.returned_asts
    
    def get_names(self):
        return self._get_names()

    def _create_scopes(self):
        block_objects = [pyname.object for pyname in self._get_names().values()
                         if pyname.has_block()]
        def block_compare(x, y):
            return cmp(x._get_ast().lineno, y._get_ast().lineno)
        block_objects.sort(cmp=block_compare)
        result = [block.get_scope() for block in block_objects]
        return result

    def get_kind(self):
        return 'Function'


class ClassScope(Scope):

    def __init__(self, pycore, pyobject):
        super(ClassScope, self).__init__(pycore, pyobject,
                                         pyobject.parent.get_scope())
    
    def get_names(self):
        return {}

    def get_kind(self):
        return 'Class'


class _HoldingScopeFinder(object):

    def __init__(self, source_code):
        self.source_code = source_code
        self.lines = rope.codeanalyze.SourceLinesAdapter(source_code)
    
    def get_indents(self, lineno):
        indents = 0
        for char in self.lines.get_line(lineno):
            if char == ' ':
                indents += 1
            else:
                break
        return indents
    
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
            if current_scope.get_start() == lineno and current_scope.get_kind() != 'Module':
                return current_scope
            new_scope = None
            for scope in current_scope.get_scopes():
                if scope.get_start() <= lineno:
                    new_scope = scope
                else:
                    break
            current_scope = new_scope
        min_indents = line_indents
        for l in range(scopes[-1].get_start() + 1, lineno):
            if self.lines.get_line(l).strip() != '' and \
               not self.lines.get_line(l).strip().startswith('#'):
                min_indents = min(min_indents, self.get_indents(l))
        while len(scopes) > 1 and \
              (min_indents <= self._get_scope_indents(scopes[-1]) and
               not (min_indents == self._get_scope_indents(scopes[-1]) and
                    lineno == scopes[-1].get_start())):
            scopes.pop()
        return scopes[-1]
    
    def find_scope_end(self, scope):
        if not scope.parent:
            return self.lines.length()
        end = scope.get_start()
        for l in range(scope.get_start() + 1, self.lines.length()):
            if self.lines.get_line(l).strip() != '' and \
               not self.lines.get_line(l).strip().startswith('#'):
                if self.get_indents(l) <= self._get_scope_indents(scope):
                    return end
                else:
                    end = l
        return self.lines.length()
