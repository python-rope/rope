import compiler
import inspect
import __builtin__

from rope.exceptions import RopeException


class RopeSyntaxError(RopeException):
    pass


class CompletionProposal(object):
    """A completion proposal.
    
    The kind instance variable shows the type of the completion and
    can be global_variable, function, class
    
    """
    def __init__(self, completion, kind):
        self.completion = completion
        self.kind = kind


class CompletionResult(object):
    """A completion result.
    
    Attribute:
    proposals -- A list of CompletionProposals
    start_offset -- completion start offset
    end_offset -- completion end offset
    
    """
    def __init__(self, proposals=[], start_offset=0, end_offset=0):
        self.proposals = proposals
        self.start_offset = start_offset
        self.end_offset = end_offset


class _Scope(object):
    def __init__(self, lineno, var_dict, children):
        self.lineno = lineno
        self.var_dict = var_dict
        self.children = children


class _FunctionScopeVisitor(object):
    def __init__(self, project, starting, start_line):
        self.project = project
        self.starting = starting
        self.scope = _Scope(start_line, {}, [])

    def visitImport(self, node):
        for import_pair in node.names:
            name, alias = import_pair
            imported = name
            if alias is not None:
                imported = alias
            if imported.startswith(self.starting):
                self.scope.var_dict[imported] = CompletionProposal(imported, 'module')

    def visitFrom(self, node):
        global_names = _get_global_names_in_module(self.project, node.modname)
        if node.names[0][0] == '*':
            for (name, kind) in global_names.iteritems():
                if name.startswith(self.starting):
                    self.scope.var_dict[name] = CompletionProposal(name, kind)
            return
        for (name, alias) in node.names:
            imported = name
            if alias is not None:
                imported = alias
            if imported.startswith(self.starting):
                if global_names.has_key(name):
                    self.scope.var_dict[imported] = CompletionProposal(imported, global_names[name])
                else:
                    self.scope.var_dict[imported] = CompletionProposal(imported, 'unknown')

    def visitAssName(self, node):
        if node.name.startswith(self.starting):
            self.scope.var_dict[node.name] = CompletionProposal(node.name, 'local_variable')
        

    def visitFunction(self, node):
        if node.name.startswith(self.starting):
            self.scope.var_dict[node.name] = CompletionProposal(node.name, 'function')
        new_visitor = _FunctionScopeVisitor.walk_function(self.project, self.starting, node)
        self.scope.children.append(new_visitor.scope)

    def visitClass(self, node):
        if node.name.startswith(self.starting):
            self.result[node.name] = CompletionProposal(node.name, 'class')
        new_visitor = _ClassScopeVisitor.walk_class(self.project, self.starting, node)
        self.scope.children.append(new_visitor.scope)

    @staticmethod
    def walk_function(project, starting, function_node):
        new_visitor = _FunctionScopeVisitor(project, starting, function_node.lineno)
        for arg in function_node.argnames:
            if arg.startswith(starting):
                new_visitor.scope.var_dict[arg] = CompletionProposal(arg, 'local_variable')
        for node in function_node.getChildNodes():
            compiler.walk(node, new_visitor)
        return new_visitor


class _ClassScopeVisitor(object):
    def __init__(self, project, starting, start_line):
        self.project = project
        self.starting = starting
        self.scope = _Scope(start_line, {}, [])

    def visitImport(self, node):
        pass

    def visitAssName(self, node):
        pass

    def visitFunction(self, node):
        new_visitor = _FunctionScopeVisitor.walk_function(self.project, self.starting, node)
        self.scope.children.append(new_visitor.scope)

    def visitClass(self, node):
        new_visitor = _ClassScopeVisitor.walk_class(self.project, self.starting, node)
        self.scope.children.append(new_visitor.scope)

    @staticmethod
    def walk_class(project, starting, class_node):
        new_visitor = _ClassScopeVisitor(project, starting, class_node.lineno)
        for node in class_node.getChildNodes():
            compiler.walk(node, new_visitor)
        return new_visitor


def _get_global_names_in_module(project, modname):
    found_modules = project.find_module(modname)
    if not found_modules:
        return {}
    
    result = {}
    class _GlobalModuleVisitor(object):
        def visitFunction(self, node):
            result[node.name] = 'function'
        def visitClass(self, node):
            result[node.name] =  'class'
        def visitAssName(self, node):
            result[node.name] = 'global_variable'
    ast = compiler.parse(found_modules[0].read())
    compiler.walk(ast, _GlobalModuleVisitor())
    return result
    

class _GlobalScopeVisitor(object):
    
    def __init__(self, project, starting):
        self.project = project
        self.starting = starting
        self.scope = _Scope(0, {}, [])

    def visitImport(self, node):
        for import_pair in node.names:
            name, alias = import_pair
            imported = name
            if alias is not None:
                imported = alias
            if imported.startswith(self.starting):
                self.scope.var_dict[imported] = CompletionProposal(imported, 'module')

    def visitFrom(self, node):
        global_names = _get_global_names_in_module(self.project, node.modname)
        if node.names[0][0] == '*':
            for (name, kind) in global_names.iteritems():
                if name.startswith(self.starting):
                    self.scope.var_dict[name] = CompletionProposal(name, kind)
            return
        for (name, alias) in node.names:
            imported = name
            if alias is not None:
                imported = alias
            if imported.startswith(self.starting):
                if global_names.has_key(name):
                    self.scope.var_dict[imported] = CompletionProposal(imported, global_names[name])
                else:
                    self.scope.var_dict[imported] = CompletionProposal(imported, 'unknown')

    def visitAssName(self, node):
        if node.name.startswith(self.starting):
            self.scope.var_dict[node.name] = CompletionProposal(node.name, 'global_variable')
        

    def visitFunction(self, node):
        if node.name.startswith(self.starting):
            self.scope.var_dict[node.name] = CompletionProposal(node.name, 'function')
        new_visitor = _FunctionScopeVisitor.walk_function(self.project, self.starting, node)
        self.scope.children.append(new_visitor.scope)

    def visitClass(self, node):
        if node.name.startswith(self.starting):
            self.scope.var_dict[node.name] = CompletionProposal(node.name, 'class')
        new_visitor = _ClassScopeVisitor.walk_class(self.project, self.starting, node)
        self.scope.children.append(new_visitor.scope)


class ICodeAssist(object):
    def complete_code(self, source, offset):
        pass


class NoAssist(ICodeAssist):
    def complete_code(self, source_code, offset):
        return CompletionResult()


class _CurrentStatementRangeFinder(object):
    """A method object for finding the range of current statement"""

    def __init__(self, lines, lineno):
        self.lines = lines
        self.lineno = lineno
        self.in_string = ''
        self.open_parens = 0
        self.explicit_continuation = False

    def _analyze_line(self, current_line):
        for i in range(len(current_line)):
            char = current_line[i]
            if char in '\'"':
                if self.in_string == '':
                    self.in_string = char
                    if char * 3 == current_line[i:i + 3]:
                        self.in_string = char * 3
                elif self.in_string == current_line[i:i + len(self.in_string)] and \
                     not (i > 0 and current_line[i - 1] == '\\' and
                          not (i > 1 and current_line[i - 2:i] == '\\\\')):
                    self.in_string = ''
            if self.in_string != '':
                continue
            if char == '#':
                break
            if char in '([{':
                self.open_parens += 1
            if char in ')]}':
                self.open_parens -= 1
        if current_line.rstrip().endswith('\\'):
            self.explicit_continuation = True
        else:
            self.explicit_continuation = False


    def get_range(self):
        last_statement = 0
        for current_line_number in range(0, self.lineno + 1):
            if not self.explicit_continuation and self.open_parens == 0 and self.in_string == '':
                last_statement = current_line_number
            current_line = self.lines[current_line_number]
            self._analyze_line(current_line)
        last_indents = self.get_line_indents(last_statement)
        end_line = self.lineno
        if True or self.lines[self.lineno].rstrip().endswith(':'):
            for i in range(self.lineno + 1, len(self.lines)):
                if self.get_line_indents(i) >= last_indents:
                    end_line = i
                else:
                    break
        return (last_statement, end_line)

    def get_line_indents(self, line_number):
        indents = 0
        for char in self.lines[line_number]:
            if char == ' ':
                indents += 1
            else:
                break
        return indents


class CodeAssist(ICodeAssist):
    def __init__(self, project):
        self.project = project
        self.builtins = [str(name) for name in dir(__builtin__)
                         if not name.startswith('_')]
        import keyword
        self.keywords = keyword.kwlist

    def _find_starting_offset(self, source_code, offset):
        current_offset = offset - 1
        while current_offset >= 0 and (source_code[current_offset].isalnum() or
                                       source_code[current_offset] in '_.'):
            current_offset -= 1;
        return current_offset + 1

    def _comment_current_statement(self, lines, lineno):
        range_finder = _CurrentStatementRangeFinder(lines, lineno)
        start, end = range_finder.get_range()
        last_indents = range_finder.get_line_indents(start)
        lines[start] = last_indents * ' ' + 'pass'
        for line in range(start + 1, end + 1):
            lines[line] = '#' # + lines[line]
        lines.append('\n')

    def _get_matching_builtins(self, starting):
        result = {}
        for builtin in self.builtins:
            if builtin.startswith(starting):
                obj = getattr(__builtin__, builtin)
                kind = 'unknown'
                if inspect.isclass(obj):
                    kind = 'class'
                if inspect.isbuiltin(obj):
                    kind = 'builtin_function'
                if inspect.ismodule(obj):
                    kind = 'module'
                if inspect.ismethod(obj):
                    kind = 'method'
                if inspect.isfunction(obj):
                    kind = 'function'
                result[builtin] = CompletionProposal(builtin, kind)
        return result

    def _get_matching_keywords(self, starting):
        result = {}
        for kw in self.keywords:
            if kw.startswith(starting):
                result[kw] = CompletionProposal(kw, 'keyword')
        return result

    def _get_line_indents(self, lines, line_number):
        indents = 0
        for char in lines[line_number]:
            if char == ' ':
                indents += 1
            else:
                break
        return indents


    def _get_all_completions(self, global_scope, lines, lineno):
        result = {}
        current_scope = global_scope
        current_indents = self._get_line_indents(lines, lineno)
        while current_scope is not None and \
              self._get_line_indents(lines, current_scope.lineno) <= current_indents:
            result.update(current_scope.var_dict)
            new_scope = None
            for scope in current_scope.children:
                if scope.lineno < lineno:
                    new_scope = scope
                else:
                    break
            current_scope = new_scope
        return result

    def _get_line_number(self, source_code, offset):
        return source_code[:offset].count('\n') + 1

    def _count_line_indents(self, source_code, offset):
        last_non_space = offset - 1
        current_pos = offset - 1
        while current_pos >= 0 and source_code[current_pos] != '\n':
            if source_code[current_pos] != ' ':
                last_non_space = current_pos
            current_pos -= 1
        return (last_non_space - current_pos - 1) / self.indentation_length

    def complete_code(self, source_code, offset):
        if offset > len(source_code):
            return []
        starting_offset = self._find_starting_offset(source_code, offset)
        starting = source_code[starting_offset:offset]
        lines = source_code.split('\n')
        current_pos = 0
        lineno = 0
        while current_pos + len(lines[lineno]) < offset:
            current_pos += len(lines[lineno]) + 1
            lineno += 1
        self._comment_current_statement(lines, lineno)
        commented_source_code = '\n'.join(lines)
        try:
            code_ast = compiler.parse(commented_source_code)
        except SyntaxError, e:
            raise RopeSyntaxError(e)
        visitor = _GlobalScopeVisitor(self.project, starting)
        compiler.walk(code_ast, visitor)
        result = self._get_all_completions(visitor.scope, lines, lineno)
        if len(starting) > 0:
            result.update(self._get_matching_builtins(starting))
            result.update(self._get_matching_keywords(starting))
        return CompletionResult(result.values(), starting_offset, offset)

