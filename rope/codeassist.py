import compiler
import inspect
import __builtin__
import re

from rope.exceptions import RopeException
from rope.codeanalyze import StatementRangeFinder


class RopeSyntaxError(RopeException):
    pass


class CodeAssistProposal(object):
    """The base class for proposals reported by CodeAssist"""

    def __init__(self, name):
        self.name = name


class CompletionProposal(CodeAssistProposal):
    """A completion proposal
    
    The kind instance variable shows the type of the completion and
    can be global_variable, function, class
    
    """

    def __init__(self, name, kind):
        super(CompletionProposal, self).__init__(name)
        self.kind = kind


class TemplateProposal(CodeAssistProposal):
    """A template proposal

    The template attribute is a Template object.
    """

    def __init__(self, name, template):
        super(TemplateProposal, self).__init__(name)
        self.kind = 'template'
        self.template = template


class Template(object):
    """Templates reported by CodeAssist
    
    Variables in templates are in the format ${variable}. To put
    a dollar sign in the template put $$. To set the place of the
    cursor use ${cursor}.
    """

    def __init__(self, template):
        self.template = template
        self.var_pattern = re.compile(r'((?<=[^\$])|^)\${(?P<variable>[a-zA-Z][\w]*)}')

    def variables(self):
        '''Returns the list of variables sorted by their order of occurence in the template'''
        result = []
        for match in self.var_pattern.finditer(self.template):
            new_var = match.group('variable')
            if new_var not in result and new_var != 'cursor':
                result.append(new_var)
        return result
    
    def _substitute(self, input_string, mapping):
        import string
        single_dollar = re.compile('((?<=[^\$])|^)\$((?=[^{\$])|$)')
        template = single_dollar.sub('$$', input_string)
        t = string.Template(template)
        return t.substitute(mapping, cursor='')

    def substitute(self, mapping):
        return self._substitute(self.template, mapping)

    def get_cursor_location(self, mapping):
        cursor_index = len(self.template)
        for match in self.var_pattern.finditer(self.template):
            new_var = match.group('variable')
            if new_var == 'cursor':
                cursor_index = match.start('variable') - 2
        new_template = self.template[0:cursor_index]
        start = len(self._substitute(new_template, mapping))
        return start


class Proposals(object):
    """A CodeAssist result.
    
    Attribute:
    completions -- A list of CompletionProposals
    templates -- A list of TemplateProposals
    start_offset -- completion start offset
    end_offset -- completion end offset
    
    """

    def __init__(self, completions=[], templates=[], start_offset=0, end_offset=0):
        self.completions = completions
        self.templates = templates
        self.start_offset = start_offset
        self.end_offset = end_offset


class _Scope(object):

    def __init__(self, lineno, var_dict, children):
        self.lineno = lineno
        self.var_dict = var_dict
        self.children = children


def _get_global_names_in_module(module):
    result = {}
    class _GlobalModuleVisitor(object):
        def visitFunction(self, node):
            result[node.name] = 'function'
        def visitClass(self, node):
            result[node.name] =  'class'
        def visitAssName(self, node):
            result[node.name] = 'global_variable'
    ast = compiler.parse(module.read())
    compiler.walk(ast, _GlobalModuleVisitor())
    return result

def _get_package_children(package):
    result = {}
    for resource in package.get_children():
        if resource.is_folder():
            result[resource.get_name()] = 'module'
        elif resource.get_name().endswith('.py'):
            result[resource.get_name()[:-3]] = 'module'
    return result


class _ScopeVisitor(object):

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
        found_modules = self.project.find_module(node.modname)
        global_names = {}
        is_module = True
        if found_modules:
            module = found_modules[0]
            if module.is_folder():
                global_names = _get_package_children(found_modules[0])
                is_module = False
            else:
                global_names = _get_global_names_in_module(found_modules[0])
        if node.names[0][0] == '*' and is_module:
            for (name, kind) in global_names.iteritems():
                if name.startswith(self.starting) and not name.startswith('_'):
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
        pass

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


class _FunctionScopeVisitor(_ScopeVisitor):

    def __init__(self, project, starting, start_line):
        super(_FunctionScopeVisitor, self).__init__(project, starting, start_line)

    def visitAssName(self, node):
        if node.name.startswith(self.starting):
            self.scope.var_dict[node.name] = CompletionProposal(node.name, 'local_variable')
        

    @staticmethod
    def walk_function(project, starting, function_node):
        new_visitor = _FunctionScopeVisitor(project, starting, function_node.lineno)
        for arg in function_node.argnames:
            if arg.startswith(starting):
                new_visitor.scope.var_dict[arg] = CompletionProposal(arg, 'local_variable')
        for node in function_node.getChildNodes():
            compiler.walk(node, new_visitor)
        return new_visitor


class _ClassScopeVisitor(_ScopeVisitor):

    def __init__(self, project, starting, start_line):
        super(_ClassScopeVisitor, self).__init__(project, starting, start_line)

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


class _GlobalScopeVisitor(_ScopeVisitor):
    
    def __init__(self, project, starting):
        super(_GlobalScopeVisitor, self).__init__(project, starting, 1)

    def visitAssName(self, node):
        if node.name.startswith(self.starting):
            self.scope.var_dict[node.name] = CompletionProposal(node.name, 'global_variable')
        

class ICodeAssist(object):

    def assist(self, source, offset):
        pass

    def add_template(self, name, template):
        pass


class NoAssist(ICodeAssist):

    def assist(self, source_code, offset):
        return Proposals()



class CodeAssist(ICodeAssist):
    def __init__(self, project):
        self.project = project
        self.builtins = [str(name) for name in dir(__builtin__)
                         if not name.startswith('_')]
        import keyword
        self.keywords = keyword.kwlist
        self.templates = []
        self.templates.extend(self._get_default_templates())

    def _get_default_templates(self):
        result = []
        result.append(TemplateProposal('main', Template("if __name__ == '__main__':\n    ${cursor}\n")))
        test_case_template = "import unittest\n\nclass ${class}Test(unittest.TestCase):\n\n" + \
                             "    def setUp(self):\n        super(${class}Test, self).setUp()\n\n" + \
                             "    def tearDown(self):\n        super(${class}Test, self).tearDown()\n\n" + \
                             "    def test_${aspect1}(self):\n        pass${cursor}\n\n\n" + \
                             "if __name__ == '__main__':\n    unittest.main()\n"
        result.append(TemplateProposal('test_case', Template(test_case_template)))
        return result

    def _find_starting_offset(self, source_code, offset):
        current_offset = offset - 1
        while current_offset >= 0 and (source_code[current_offset].isalnum() or
                                       source_code[current_offset] in '_.'):
            current_offset -= 1;
        return current_offset + 1

    def _comment_current_statement(self, lines, lineno):
        range_finder = StatementRangeFinder(lines, lineno)
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


    def _get_code_completions(self, source_code, offset, starting):
        lines = source_code.split('\n')
        current_pos = 0
        lineno = 0
        while current_pos + len(lines[lineno]) < offset:
            current_pos += len(lines[lineno]) + 1
            lineno += 1
        current_indents = self._get_line_indents(lines, lineno)
        self._comment_current_statement(lines, lineno)
        source_code = '\n'.join(lines)
        try:
            code_ast = compiler.parse(source_code)
        except SyntaxError, e:
            raise RopeSyntaxError(e)
        visitor = _GlobalScopeVisitor(self.project, starting)
        compiler.walk(code_ast, visitor)
        result = {}
        current_scope = visitor.scope
        while current_scope is not None and \
              (current_scope == visitor.scope or
               self._get_line_indents(lines, current_scope.lineno - 1) < current_indents):
            result.update(current_scope.var_dict)
            new_scope = None
            for scope in current_scope.children:
                if scope.lineno - 1 <= lineno:
                    new_scope = scope
                else:
                    break
            current_scope = new_scope
        return result

    def add_template(self, name, definition):
        self.templates.append(TemplateProposal(name, Template(definition)))

    def _get_template_proposals(self, starting):
        result = []
        for template in self.templates:
            if template.name.startswith(starting):
                result.append(template)
        return result

    def assist(self, source_code, offset):
        if offset > len(source_code):
            return Proposals([], [], 0, 0)
        starting_offset = self._find_starting_offset(source_code, offset)
        starting = source_code[starting_offset:offset]
        completions = self._get_code_completions(source_code, offset, starting)
        templates = []
        if len(starting) > 0:
            completions.update(self._get_matching_builtins(starting))
            completions.update(self._get_matching_keywords(starting))
            templates = self._get_template_proposals(starting)
        return Proposals(completions.values(), templates, starting_offset, offset)

