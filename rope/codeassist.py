import compiler
import inspect
import __builtin__
import re

from rope.exceptions import RopeException
from rope.codeanalyze import (StatementRangeFinder, ArrayLinesAdapter,
                              HoldingScopeFinder, WordRangeFinder, ScopeNameFinder,
                              SourceLinesAdapter)

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
    
    """

    def __init__(self, completions=[], templates=[], start_offset=0):
        self.completions = completions
        self.templates = templates
        self.start_offset = start_offset


class CodeAssist(object):

    def assist(self, source, offset):
        pass

    def add_template(self, name, template):
        pass
    
    def get_definition_location(self, source_code, offset):
        pass


class NoAssist(CodeAssist):

    def assist(self, source_code, offset):
        return Proposals()

    def get_definition_location(self, source_code, offset):
        return (None, None)


class _CodeCompletionCollector(object):

    def __init__(self, project, source_code, offset, expression, starting):
        self.project = project
        self.expression = expression
        self.starting = starting
        self.pycore = self.project.get_pycore()
        self.lines = source_code.split('\n')
        self.source_code = source_code
        source_lines = SourceLinesAdapter(source_code)
        self.lineno = source_lines.get_line_number(offset)
        self.current_indents = self._get_line_indents(source_lines.get_line(self.lineno))
        self._comment_current_statement()
        self.source_code = '\n'.join(self.lines)

    def _get_line_indents(self, line):
        indents = 0
        for char in line:
            if char == ' ':
                indents += 1
            else:
                break
        return indents

    def _comment_current_statement(self):
        range_finder = StatementRangeFinder(ArrayLinesAdapter(self.lines),
                                            self.lineno)
        range_finder.analyze()
        start = range_finder.get_statement_start() - 1
        end = range_finder.get_scope_end() - 1
        last_indents = self._get_line_indents(self.lines[start])
        self.lines[start] = last_indents * ' ' + 'pass'
        for line in range(start + 1, end + 1):
            self.lines[line] = '#' # + lines[line]
        self.lines.append('\n')

    def _find_inner_holding_scope(self, base_scope):
        scope_finder = HoldingScopeFinder(self.source_code)
        return scope_finder.get_holding_scope(base_scope, self.lineno,
                                              self.current_indents)

    def _get_dotted_completions(self, module_scope, holding_scope):
        result = {}
        pyname_finder = ScopeNameFinder(self.source_code, module_scope)
        element = pyname_finder.get_pyname_in_scope(holding_scope, self.expression)
        if element is not None:
            for name, pyname in element.get_attributes().iteritems():
                if name.startswith(self.starting) or self.starting == '':
                    result[name] = CompletionProposal(name, 'attribute')
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
            module_scope = self.pycore.get_string_scope(self.source_code)
        except SyntaxError, e:
            raise RopeSyntaxError(e)
        current_scope = module_scope
        result = {}
        inner_scope = self._find_inner_holding_scope(module_scope)
        if self.expression.strip() != '':
            result.update(self._get_dotted_completions(module_scope, inner_scope))
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
        test_case_template = "import unittest\n\n"+ \
                             "class ${class}(unittest.TestCase):\n\n" + \
                             "    def setUp(self):\n        super(${class}, self).setUp()\n\n" + \
                             "    def tearDown(self):\n        super(${class}, self).tearDown()\n\n" + \
                             "    def test_${aspect1}(self):\n        pass${cursor}\n\n\n" + \
                             "if __name__ == '__main__':\n" + \
                             "    unittest.main()\n"
        result.append(TemplateProposal('testcase', Template(test_case_template)))
        result.append(TemplateProposal('hash', Template('\n    def __hash__(self):\n' + \
                                                        '        return 1${cursor}\n')))
        result.append(TemplateProposal('eq', Template('\n    def __eq__(self, obj):\n' + \
                                                      '        ${cursor}return obj is self\n')))
        result.append(TemplateProposal('super', Template('super(${class}, self)')))
        return result

    def _find_starting_offset(self, source_code, offset):
        current_offset = offset - 1
        while current_offset >= 0 and (source_code[current_offset].isalnum() or
                                       source_code[current_offset] in '_'):
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

    def _get_code_completions(self, source_code, offset, expression, starting):
        collector = _CodeCompletionCollector(self.project, source_code,
                                             offset, expression, starting)
        return collector.get_code_completions()

    def assist(self, source_code, offset):
        if offset > len(source_code):
            return Proposals()
        word_finder = WordRangeFinder(source_code)
        expression, starting, starting_offset = word_finder.get_splitted_statement_before(offset)
        completions = self._get_code_completions(source_code, offset, expression, starting)
        templates = []
        if expression.strip() == '' and starting.strip() != '':
            completions.update(self._get_matching_builtins(starting))
            completions.update(self._get_matching_keywords(starting))
            templates = self._get_template_proposals(starting)
        return Proposals(completions.values(), templates,
                         starting_offset)

    def get_definition_location(self, source_code, offset):
        return _GetDefinitionLocation(self.project, source_code,
                                      offset).get_definition_location()


class _GetDefinitionLocation(object):

    def __init__(self, project, source_code, offset):
        self.project = project
        self.offset = offset
        self.source_code = source_code

    def get_definition_location(self):
        module_scope = self.project.pycore.get_string_scope(self.source_code)
        scope_finder = ScopeNameFinder(self.source_code, module_scope)
        element = scope_finder.get_pyname_at(self.offset)
        if element is not None:
            return element.get_definition_location()
        else:
            return (None, None)


class ProposalSorter(object):

    def __init__(self, code_assist_proposals):
        self.proposals = code_assist_proposals
    
    def get_sorted_proposal_list(self):
        local_proposals = []
        global_proposals = []
        others = []
        for proposal in self.proposals.completions:
            if proposal.kind == 'global':
                global_proposals.append(proposal)
            elif proposal.kind == 'local':
                local_proposals.append(proposal)
            else:
                others.append(proposal)
        template_proposals = self.proposals.templates
        result = []
        result.extend(local_proposals)
        result.extend(global_proposals)
        result.extend(template_proposals)
        result.extend(others)
        return result

