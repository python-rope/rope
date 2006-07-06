import compiler
import inspect
import __builtin__
import re

from rope.exceptions import RopeException
from rope.codeanalyze import (StatementRangeFinder, ArrayLinesAdapter,
                              HoldingScopeFinder, WordRangeFinder, ScopeNameFinder)

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

    def __init__(self, project, source_code, offset, starting):
        self.project = project
        self.starting = starting
        self.pycore = self.project.get_pycore()
        self.lines = source_code.split('\n')
        scope_finder = HoldingScopeFinder(self.lines)
        self.lineno = scope_finder.get_location(offset)[0]
        self.current_indents = scope_finder.get_indents(self.lineno)
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
        range_finder = StatementRangeFinder(ArrayLinesAdapter(self.lines), self.lineno)
        range_finder.analyze()
        start = range_finder.get_statement_start() - 1
        end = range_finder.get_scope_end() - 1
        last_indents = self._get_line_indents(start)
        self.lines[start] = last_indents * ' ' + 'pass'
        for line in range(start + 1, end + 1):
            self.lines[line] = '#' # + lines[line]
        self.lines.append('\n')

    def _find_inner_holding_scope(self, base_scope):
        scope_finder = HoldingScopeFinder(self.lines)
        return scope_finder.get_holding_scope(base_scope, self.lineno, self.current_indents)

    def _get_dotted_completions(self, scope):
        result = {}
        if len(self.starting) > 1:
            element = scope.lookup(self.starting[0])
            if element is not None:
                consistent = True
                for token in self.starting[1:-1]:
                    if token in element.get_attributes():
                        element = element.get_attributes()[token]
                    else:
                        consistent = False
                        break
                if consistent:
                    for name, pyname in element.get_attributes().iteritems():
                        if name.startswith(self.starting[-1]) or self.starting[-1] == '':
                            result[name] = CompletionProposal(name, 'attribute')
        return result

    def _get_undotted_completions(self, scope, result):
        if scope.parent != None:
            self._get_undotted_completions(scope.parent, result)
        for name, pyname in scope.get_names().iteritems():
            if name.startswith(self.starting[0]):
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
        if len(self.starting) > 1:
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

    def _get_code_completions(self, source_code, offset, starting):
        collector = _CodeCompletionCollector(self.project, source_code, offset, starting)
        return collector.get_code_completions()

    def assist(self, source_code, offset):
        if offset > len(source_code):
            return Proposals()
        word_finder = WordRangeFinder(source_code)
        starting_offset = word_finder.find_word_start(offset)
        starting = word_finder.get_name_list_before(offset)
        completions = self._get_code_completions(source_code, offset, starting)
        templates = []
        if len(starting) == 1 and len(starting[0]) > 0:
            completions.update(self._get_matching_builtins(starting[0]))
            completions.update(self._get_matching_keywords(starting[0]))
            templates = self._get_template_proposals(starting[0])
        return Proposals(completions.values(), templates,
                         starting_offset)

    def get_definition_location(self, source_code, offset):
        return _GetDefinitionLocation(self.project, source_code,
                                      offset).get_definition_location()


class _GetDefinitionLocation(object):

    def __init__(self, project, source_code, offset):
        self.project = project
        self.offset = offset
        self.scope_finder = HoldingScopeFinder(source_code.split('\n'))
        self.lineno = self.scope_finder.get_location(offset)[0]
        word_finder = WordRangeFinder(source_code)
        self.name_list = word_finder.get_name_list_at(offset)
        self.source_code = source_code

    def get_definition_location(self):
        module_scope = self.project.pycore.get_string_scope(self.source_code)
#        scope_finder = ScopeNameFinder(self.source_code, module_scope)
#        element = scope_finder.get_pyname_at(self.offset)
#        element_resource = None
#        if element != None:
#            current_element = element
#            while current_element != None:
#                if current_element.get_definition_location()[0] is not None:
#                    element_resource = current_element.get_definition_location()[0].get_resource()
#                    break
#                current_element = current_element.get_object().parent
#        if element is not None:
#            return (element_resource, element.get_definition_location()[1])
#        else:
#            return (None, None)

        holding_scope = self.scope_finder.get_holding_scope(module_scope, self.lineno)
        element = holding_scope.lookup(self.name_list[0])
        element_resource = None
        if element is not None and \
           element.get_definition_location()[0] is not None:
            element_resource = element.get_definition_location()[0].get_resource()
        if element is not None and len(self.name_list) > 1:
            for token in self.name_list[1:]:
                if token in element.get_attributes():
                    element = element.get_attributes()[token]
                    if element.get_definition_location()[0] is not None:
                        element_resource = element.get_definition_location()[0].get_resource()
                else:
                    element = None
                    break

        if element is not None:
            return (element_resource, element.get_definition_location()[1])
        else:
            return (None, None)

