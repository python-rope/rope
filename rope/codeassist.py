import compiler
import inspect
import __builtin__
import re

from rope.exceptions import RopeException
from rope.codeanalyze import StatementRangeFinder, ArrayLinesAdapter

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

    def __init__(self, completions=[], templates=[], start_offset=0,
                 end_offset=0):
        self.completions = completions
        self.templates = templates
        self.start_offset = start_offset
        self.end_offset = end_offset


class CodeAssist(object):

    def assist(self, source, offset):
        pass

    def add_template(self, name, template):
        pass


class NoAssist(CodeAssist):

    def assist(self, source_code, offset):
        return Proposals()


class _CodeCompletionCollector(object):

    def __init__(self, project, source_code, offset, starting):
        self.project = project
        self.starting = starting
        self.pycore = self.project.get_pycore()
        self.lines = source_code.split('\n')
        current_pos = 0
        lineno = 0
        while current_pos + len(self.lines[lineno]) < offset:
            current_pos += len(self.lines[lineno]) + 1
            lineno += 1
        self.lineno = lineno
        self.current_indents = self._get_line_indents(lineno)
        self._comment_current_statement()

    def _get_line_indents(self, line_number):
        indents = 0
        for char in self.lines[line_number]:
            if char == ' ':
                indents += 1
            else:
                break
        return indents

    def _comment_current_statement(self):
        range_finder = StatementRangeFinder(ArrayLinesAdapter(self.lines), self.lineno + 1)
        range_finder.analyze()
        start = range_finder.get_statement_start() - 1
        end = range_finder.get_scope_end() - 1
        last_indents = self._get_line_indents(start)
        self.lines[start] = last_indents * ' ' + 'pass'
        for line in range(start + 1, end + 1):
            self.lines[line] = '#' # + lines[line]
        self.lines.append('\n')

    def _find_inner_holding_scope(self, base_scope):
        current_scope = base_scope
        inner_scope = current_scope
        while current_scope is not None and \
              (current_scope.get_kind() == 'Module' or
               self._get_line_indents(current_scope.get_lineno() - 1) < self.current_indents):
            inner_scope = current_scope
            new_scope = None
            for scope in current_scope.get_scopes():
                if scope.get_lineno() - 1 <= self.lineno:
                    new_scope = scope
                else:
                    break
            current_scope = new_scope
        return inner_scope

    def _get_dotted_completions(self, scope):
        result = {}
        if '.' in self.starting:
            tokens = self.starting.split('.')
            element = scope.lookup(tokens[0])
            if element is not None:
                consistent = True
                for token in tokens[1:-1]:
                    if token in element.get_attributes():
                        element = element.get_attributes()[token]
                    else:
                        consistent = False
                        break
                if consistent:
                    for name, pyname in element.get_attributes().iteritems():
                        if name.startswith(tokens[-1]) or tokens[-1] == '':
                            complete_name = '.'.join(tokens[:-1]) + '.' + name
                            result[complete_name] = CompletionProposal(complete_name, 'attribute')
        return result

    def _get_undotted_completions(self, scope, result):
        if scope.parent != None:
            self._get_undotted_completions(scope.parent, result)
        for name, pyname in scope.get_names().iteritems():
            if name.startswith(self.starting):
                from rope.pycore import PyObject
                kind = 'local'
                if scope.get_kind() == 'Module':
                    kind = 'global'
                result[name] = CompletionProposal(name, kind)

    def get_code_completions(self):
        try:
            module_scope = self.pycore.get_string_scope('\n'.join(self.lines))
        except SyntaxError, e:
            raise RopeSyntaxError(e)
        current_scope = module_scope
        result = {}
        inner_scope = self._find_inner_holding_scope(module_scope)
        if '.' in self.starting:
            result.update(self._get_dotted_completions(inner_scope))
        else:
            self._get_undotted_completions(inner_scope, result)
        return result


class PythonCodeAssist(CodeAssist):

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
        test_case_template = "import unittest\n\nclass ${class}(unittest.TestCase):\n\n" + \
                             "    def setUp(self):\n        super(${class}, self).setUp()\n\n" + \
                             "    def tearDown(self):\n        super(${class}, self).tearDown()\n\n" + \
                             "    def test_${aspect1}(self):\n        pass${cursor}\n\n\n" + \
                             "if __name__ == '__main__':\n    unittest.main()\n"
        result.append(TemplateProposal('test_case', Template(test_case_template)))
        result.append(TemplateProposal('hash', Template('\n    def __hash__(self):\n' + \
                                                        '        return 1${cursor}\n')))
        result.append(TemplateProposal('eq', Template('\n    def __eq__(self, obj):\n' + \
                                                        '        ${cursor}return obj is self\n')))
        result.append(TemplateProposal('super', Template('super(${class}, self)')))
        return result

    def _find_starting_offset(self, source_code, offset):
        current_offset = offset - 1
        while current_offset >= 0 and (source_code[current_offset].isalnum() or
                                       source_code[current_offset] in '_.'):
            current_offset -= 1;
        return current_offset + 1

    def _get_matching_builtins(self, starting):
        result = {}
        for builtin in self.builtins:
            if builtin.startswith(starting):
                result[builtin] = CompletionProposal(builtin, 'builtin')
        return result

    def _get_matching_keywords(self, starting):
        result = {}
        for kw in self.keywords:
            if kw.startswith(starting):
                result[kw] = CompletionProposal(kw, 'keyword')
        return result

    def add_template(self, name, definition):
        self.templates.append(TemplateProposal(name, Template(definition)))

    def _get_template_proposals(self, starting):
        result = []
        for template in self.templates:
            if template.name.startswith(starting):
                result.append(template)
        return result

    def _get_code_completions(self, source_code, offset, starting):
        collector = _CodeCompletionCollector(self.project, source_code, offset, starting)
        return collector.get_code_completions()

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
        return Proposals(completions.values(), templates,
                         starting_offset, offset)

