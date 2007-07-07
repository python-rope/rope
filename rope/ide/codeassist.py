import __builtin__
import re

import rope.base.codeanalyze
from rope.base import pyobjects, pynames, taskhandle
from rope.base.codeanalyze import (StatementRangeFinder, ArrayLinesAdapter,
                                   WordRangeFinder, ScopeNameFinder,
                                   SourceLinesAdapter, BadIdentifierError)
from rope.base.exceptions import RopeError
from rope.ide import pydoc
from rope.refactor import occurrences, functionutils


class RopeSyntaxError(RopeError):
    pass


class CodeAssistProposal(object):
    """The base class for proposals reported by CodeAssist"""

    def __init__(self, name):
        self.name = name


class CompletionProposal(CodeAssistProposal):
    """A completion proposal

    The `kind` instance variable shows the kind of the proposal and
    can be ``global``, ``local``, ``builtin``, ``attribute``,
    ``keyword``, ``parameter_keyword``, and ``template``.

    The `type` instance variable shows the type of the proposal and
    can be ``variable``, ``class``, ``function``, ``imported`` ,
    ``paramter`` and `None`.

    """

    def __init__(self, name, kind, type=None):
        super(CompletionProposal, self).__init__(name)
        self.kind = kind
        self.type = type

    def __str__(self):
        return '%s (%s, %s)' % (self.name, self.kind, self.type)

    def __repr__(self):
        return str(self)


class TemplateProposal(CodeAssistProposal):
    """A template proposal

    The template attribute is a Template object.
    """

    def __init__(self, name, template):
        super(TemplateProposal, self).__init__(name)
        self.template = template


class Template(object):
    """Templates reported by CodeAssist

    Variables in templates are in the format ${variable}. To put
    a dollar sign in the template put $$. To set the place of the
    cursor use ${cursor}.
    """

    def __init__(self, template):
        self.template = template

    var_pattern = re.compile(r'((?<=[^\$])|^)\${(?P<variable>[a-zA-Z][\w]*)}')

    def variables(self):
        """Returns the list of variables sorted by their order
        of occurence in the template
        """
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


class _CodeCompletionCollector(object):

    def __init__(self, project, source_code,
                 offset, expression, starting, resource):
        self.project = project
        self.expression = expression
        self.starting = starting
        self.offset = offset
        self.pycore = self.project.get_pycore()
        self.unchanged_source = source_code
        self.lines = source_code.split('\n')
        self.source_code = source_code
        self.resource = resource
        source_lines = SourceLinesAdapter(source_code)
        self.lineno = source_lines.get_line_number(offset)
        self.current_indents = self._get_line_indents(
            source_lines.get_line(self.lineno))
        self._comment_current_statement()
        self.source_code = '\n'.join(self.lines)

    def _get_line_indents(self, line):
        return rope.base.codeanalyze.count_line_indents(line)

    def _comment_current_statement(self):
        range_finder = StatementRangeFinder(ArrayLinesAdapter(self.lines),
                                            self.lineno)
        start = range_finder.get_statement_start() - 1
        end = range_finder.get_block_end() - 1
        last_indents = self._get_line_indents(self.lines[start])
        self.lines[start] = ' ' * last_indents + 'pass'
        for line in range(start + 1, end + 1):
            #self.lines[line] = '#' # + lines[line]
            self.lines[line] = self.lines[start]
        self.lines.append('\n')
        self._fix_uncomplete_try_blocks()

    def _fix_uncomplete_try_blocks(self):
        block_start = self.lineno
        last_indents = self.current_indents
        while block_start > 0:
            block_start = rope.base.codeanalyze.get_block_start(
                ArrayLinesAdapter(self.lines), block_start) - 1
            if self.lines[block_start].strip().startswith('try:'):
                indents = self._get_line_indents(self.lines[block_start])
                if indents > last_indents:
                    continue
                last_indents = indents
                block_end = self._find_matching_deindent(block_start)
                if not self.lines[block_end].strip().startswith('finally:') and \
                   not self.lines[block_end].strip().startswith('except '):
                    self.lines.insert(block_end, ' ' * indents + 'finally:')
                    self.lines.insert(block_end + 1, ' ' * indents + '    pass')

    def _find_matching_deindent(self, line_number):
        indents = self._get_line_indents(self.lines[line_number])
        current_line = line_number + 1
        while current_line < len(self.lines):
            line = self.lines[current_line]
            if not line.strip().startswith('#') and not line.strip() == '':
                # HACK: We should have used logical lines here
                if self._get_line_indents(self.lines[current_line]) <= indents:
                    return current_line
            current_line += 1
        return len(self.lines) - 1

    def _get_dotted_completions(self, module_scope, holding_scope):
        result = {}
        pyname_finder = ScopeNameFinder(module_scope.pyobject)
        found_pyname = pyname_finder.get_pyname_in_scope(holding_scope,
                                                         self.expression)
        if found_pyname is not None:
            element = found_pyname.get_object()
            for name, pyname in element.get_attributes().items():
                if name.startswith(self.starting) or self.starting == '':
                    result[name] = CompletionProposal(
                        name, 'attribute', self._get_pyname_type(pyname))
        return result

    def _get_undotted_completions(self, scope, result, propagated=False):
        if scope.parent != None:
            self._get_undotted_completions(scope.parent, result,
                                           propagated=True)
        if propagated:
            names = scope.get_propagated_names()
        else:
            names = scope.get_names()
        for name, pyname in names.items():
            if name.startswith(self.starting):
                kind = 'local'
                if scope.get_kind() == 'Module':
                    kind = 'global'
                result[name] = CompletionProposal(
                    name, kind, self._get_pyname_type(pyname))

    def _get_pyname_type(self, pyname):
        if isinstance(pyname, (pynames.AssignedName, pynames.UnboundName)):
            return 'variable'
        if isinstance(pyname, pynames.DefinedName):
            pyobject = pyname.get_object()
            if isinstance(pyobject, pyobjects.AbstractFunction):
                return 'function'
            else:
                return 'class'
        if isinstance(pyname, pynames.ImportedName) or \
           isinstance(pyname, pynames.ImportedModule):
            return 'imported'
        if isinstance(pyname, pynames.ParameterName):
            return 'parameter'

    def get_code_completions(self):
        try:
            module_scope = get_pymodule(self.pycore, self.source_code,
                                        self.resource).get_scope()
        except SyntaxError, e:
            raise RopeSyntaxError(e)
        result = {}
        inner_scope = module_scope.get_inner_scope_for_line(self.lineno,
                                                            self.current_indents)
        if self.expression.strip() != '':
            result.update(self._get_dotted_completions(module_scope,
                                                       inner_scope))
        else:
            result.update(self._get_keyword_parameters(module_scope.pyobject,
                                                       inner_scope))
            self._get_undotted_completions(inner_scope, result)
        return result

    def _get_keyword_parameters(self, pymodule, scope):
        offset = self.offset
        if offset == 0:
            return {}
        word_finder = WordRangeFinder(self.unchanged_source)
        lines = SourceLinesAdapter(self.unchanged_source)
        lineno = lines.get_line_number(offset)
        stop_line = StatementRangeFinder(lines, lineno).get_statement_start()
        stop = lines.get_line_start(stop_line)
        if word_finder.is_on_function_call_keyword(offset - 1, stop):
            name_finder = ScopeNameFinder(pymodule)
            function_parens = word_finder.find_parens_start_from_inside(offset - 1, stop)
            primary = word_finder.get_primary_at(function_parens - 1)
            try:
                function_pyname = ScopeNameFinder.get_pyname_in_scope(scope, primary)
            except BadIdentifierError, e:
                return {}
            if function_pyname is not None:
                pyobject = function_pyname.get_object()
                if isinstance(pyobject, pyobjects.AbstractFunction):
                    pass
                elif isinstance(pyobject, pyobjects.AbstractClass) and \
                     '__init__' in pyobject.get_attributes():
                    pyobject = pyobject.get_attribute('__init__').get_object()
                elif '__call__' in pyobject.get_attributes():
                    pyobject = pyobject.get_attribute('__call__').get_object()
                if isinstance(pyobject, pyobjects.AbstractFunction):
                    param_names = []
                    if isinstance(pyobject, pyobjects.PyFunction):
                        function_info = functionutils.DefinitionInfo.read(pyobject)
                        param_names.extend([name for name, default
                                            in function_info.args_with_defaults])
                    else:
                        param_names = pyobject.get_param_names()
                    result = {}
                    for name in param_names:
                        if name.startswith(self.starting):
                            result[name + '='] = CompletionProposal(
                                name + '=', 'parameter_keyword')
                    return result
        return {}


class PythonCodeAssist(object):

    def __init__(self, project):
        self.project = project
        import keyword
        self.keywords = keyword.kwlist
        self.templates = []
        self.templates.extend(PythonCodeAssist._get_default_templates())

    builtins = [str(name) for name in dir(__builtin__)
                if not name.startswith('_')]

    @staticmethod
    def _get_default_templates():
        templates = {}
        templates['main'] = Template("if __name__ == '__main__':\n    ${cursor}\n")
        test_case_template = \
            ('import unittest\n\n\n'
             'class ${TestClass}(unittest.TestCase):\n\n'
             '    def setUp(self):\n        super(${TestClass}, self).setUp()\n\n'
             '    def tearDown(self):\n        super(${TestClass}, self).tearDown()\n\n'
             '    def test_trivial_case${cursor}(self):\n        pass\n\n\n'
             'if __name__ == \'__main__\':\n'
             '    unittest.main()\n')
        templates['testcase'] = Template(test_case_template)
        templates['hash'] = Template('\n    def __hash__(self):\n' +
                                     '        return 1${cursor}\n')
        templates['eq'] = Template('\n    def __eq__(self, obj):\n' +
                                   '        ${cursor}return obj is self\n')
        templates['super'] = Template('super(${class}, self)')
        templates.update(PythonCodeAssist.default_templates)
        result = []
        for name, template in templates.items():
            result.append(TemplateProposal(name, template))
        return result

    default_templates = {}

    @staticmethod
    def add_default_template(name, definition):
        PythonCodeAssist.default_templates[name] = Template(definition)

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

    def _get_code_completions(self, source_code, offset,
                              expression, starting, resource):
        collector = _CodeCompletionCollector(self.project, source_code, offset,
                                             expression, starting, resource)
        return collector.get_code_completions()

    def assist(self, source_code, offset, resource=None):
        if offset > len(source_code):
            return Proposals()
        word_finder = WordRangeFinder(source_code)
        expression, starting, starting_offset = \
            word_finder.get_splitted_primary_before(offset)
        completions = self._get_code_completions(
            source_code, offset, expression, starting, resource)
        templates = []
        if expression.strip() == '' and starting.strip() != '':
            completions.update(self._get_matching_builtins(starting))
            completions.update(self._get_matching_keywords(starting))
            templates = self._get_template_proposals(starting)
        return Proposals(completions.values(), templates,
                         starting_offset)

    def get_definition_location(self, source_code, offset, resource=None):
        return _GetDefinitionLocation(self.project, source_code,
                                      offset, resource).get_definition_location()

    def get_doc(self, source_code, offset, resource=None):
        pymodule = get_pymodule(self.project.pycore, source_code, resource)
        scope_finder = ScopeNameFinder(pymodule)
        element = scope_finder.get_pyname_at(offset)
        if element is None:
            return None
        pyobject = element.get_object()
        return pydoc.get_doc(pyobject)

    def find_occurrences(self, resource, offset, unsure=False,
                         task_handle=taskhandle.NullTaskHandle()):
        name = rope.base.codeanalyze.get_name_at(resource, offset)
        pyname = rope.base.codeanalyze.get_pyname_at(self.project.get_pycore(),
                                                     resource, offset)
        finder = occurrences.FilteredFinder(
            self.project.get_pycore(), name, [pyname], unsure=unsure)
        files = self.project.get_pycore().get_python_files()
        job_set = task_handle.create_job_set('Finding Occurrences',
                                             count=len(files))
        result = []
        for resource in files:
            job_set.started_job('Working On <%s>' % resource.path)
            for occurrence in finder.find_occurrences(resource):
                result.append((resource, occurrence.get_word_range()[0]))
            job_set.finished_job()
        return result


def get_pymodule(pycore, source_code, resource):
    if resource and resource.exists() and source_code == resource.read():
        return pycore.resource_to_pyobject(resource)
    return pycore.get_string_module(source_code, resource=resource)


class _GetDefinitionLocation(object):

    def __init__(self, project, source_code, offset, resource):
        self.project = project
        self.offset = offset
        self.source_code = source_code
        self.resource = resource

    def get_definition_location(self):
        pymodule = self.project.pycore.get_string_module(self.source_code,
                                                         self.resource)
        scope_finder = ScopeNameFinder(pymodule)
        element = scope_finder.get_pyname_at(self.offset)
        if element is not None:
            module, lineno = element.get_definition_location()
            if module is not None:
                return module.get_module().get_resource(), lineno
        return (None, None)


class ProposalSorter(object):

    def __init__(self, code_assist_proposals):
        self.proposals = code_assist_proposals

    def get_sorted_proposal_list(self):
        local_proposals = []
        parameter_keyword_proposals = []
        global_proposals = []
        attribute_proposals = []
        others = []
        for proposal in self.proposals.completions:
            if proposal.kind == 'global':
                global_proposals.append(proposal)
            elif proposal.kind == 'local':
                local_proposals.append(proposal)
            elif proposal.kind == 'attribute':
                attribute_proposals.append(proposal)
            elif proposal.kind == 'parameter_keyword':
                parameter_keyword_proposals.append(proposal)
            else:
                others.append(proposal)
        template_proposals = self.proposals.templates
        local_proposals.sort(self._pyname_proposal_cmp)
        parameter_keyword_proposals.sort(self._pyname_proposal_cmp)
        global_proposals.sort(self._pyname_proposal_cmp)
        attribute_proposals.sort(self._pyname_proposal_cmp)
        result = []
        result.extend(local_proposals)
        result.extend(parameter_keyword_proposals)
        result.extend(global_proposals)
        result.extend(attribute_proposals)
        result.extend(template_proposals)
        result.extend(others)
        return result

    def _pyname_proposal_cmp(self, proposal1, proposal2):
        preference = ['class', 'function', 'variable',
                      'parameter', 'imported', None]
        if proposal1.type != proposal2.type:
            return cmp(preference.index(proposal1.type),
                       preference.index(proposal2.type))
        return self._compare_names_with_under_lines(proposal1.name,
                                                    proposal2.name)

    def _compare_names_with_under_lines(self, name1, name2):
        def underline_count(name):
            result = 0
            while result < len(name) and name[result] == '_':
                result += 1
            return result
        underline_count1 = underline_count(name1)
        underline_count2 = underline_count(name2)
        if underline_count1 != underline_count2:
            return cmp(underline_count1, underline_count2)
        return cmp(name1, name2)
