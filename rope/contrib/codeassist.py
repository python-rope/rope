import keyword
import re
import sys

import rope.base.codeanalyze
from rope.base import pyobjects, pynames, taskhandle, builtins, codeanalyze
from rope.base.codeanalyze import (ArrayLinesAdapter, BadIdentifierError,
                                   LogicalLineFinder, ScopeNameFinder,
                                   SourceLinesAdapter, WordRangeFinder)
from rope.refactor import occurrences, functionutils


def code_assist(project, source_code, offset, resource=None, templates={}):
    """Return python code completions as a list of `CodeAssistProposal`\s

    `resource` is a `rope.base.resources.Resource` object.  If
    provided, relative imports are handled.

    `templates` should be a dictionary of template name to `Template`
    objects.  The matches are returned as `TemplateProposal`
    instances.

    """
    assist = _PythonCodeAssist(project, templates=templates)
    return assist.assist(source_code, offset, resource)


def starting_offset(source_code, offset):
    """Return the offset in which the completion should be inserted

    Usually code assist proposals should be inserted like::

        completion = proposal.name # not for templates
        result = (source_code[:starting_offset] +
                  completion + source_code[offset:])

    Where starting_offset is the offset returned by this function.

    """
    word_finder = WordRangeFinder(source_code)
    expression, starting, starting_offset = \
        word_finder.get_splitted_primary_before(offset)
    return starting_offset


def get_doc(project, source_code, offset, resource=None):
    """Get the pydoc"""
    pymodule = _get_pymodule(project.pycore, source_code, resource)
    scope_finder = ScopeNameFinder(pymodule)
    element = scope_finder.get_pyname_at(offset)
    if element is None:
        return None
    pyobject = element.get_object()
    return PyDocExtractor().get_doc(pyobject)


def get_definition_location(project, source_code, offset, resource=None):
    """Return a (`rope.base.resources.Resource`, lineno) tuple"""
    pymodule = project.pycore.get_string_module(source_code, resource)
    scope_finder = ScopeNameFinder(pymodule)
    element = scope_finder.get_pyname_at(offset)
    if element is not None:
        module, lineno = element.get_definition_location()
        if module is not None:
            return module.get_module().get_resource(), lineno
    return (None, None)


def find_occurrences(project, resource, offset, unsure=False,
                     task_handle=taskhandle.NullTaskHandle()):
    """Return a list of `Location`\s

    if `unsure` is `True`, possible matches are returned, too.

    """
    name = rope.base.codeanalyze.get_name_at(resource, offset)
    pyname = rope.base.codeanalyze.get_pyname_at(project.get_pycore(),
                                                 resource, offset)
    def is_match(occurrence):
        return unsure
    finder = occurrences.FilteredFinder(
        project.get_pycore(), name, [pyname], unsure=is_match)
    files = project.get_pycore().get_python_files()
    job_set = task_handle.create_jobset('Finding Occurrences',
                                        count=len(files))
    result = []
    for resource in files:
        job_set.started_job('Working On <%s>' % resource.path)
        for occurrence in finder.find_occurrences(resource):
            location = Location()
            location.resource = resource
            location.offset = occurrence.get_word_range()[0]
            location.unsure = occurrence.is_unsure()
            result.append(location)
        job_set.finished_job()
    return result


class Location(object):

    resource = None
    offset = None
    unsure = False


class CodeAssistProposal(object):
    """The base class for proposals reported by `code_assist`

    The `kind` instance variable shows the kind of the proposal and
    can be 'global', 'local', 'builtin', 'attribute', 'keyword',
    'parameter_keyword' and 'template'.

    """

    def __init__(self, name, kind):
        self.name = name
        self.kind = kind


class CompletionProposal(CodeAssistProposal):
    """A completion proposal

    The `type` instance variable shows the type of the proposal and
    can be 'variable', 'class', 'function', 'imported' , 'paramter'
    and `None`.

    """

    def __init__(self, name, kind, type=None):
        super(CompletionProposal, self).__init__(name, kind)
        self.type = type

    def __str__(self):
        return '%s (%s, %s)' % (self.name, self.kind, self.type)

    def __repr__(self):
        return str(self)


class TemplateProposal(CodeAssistProposal):
    """A template proposal

    The `template` attribute is a `Template` object.
    """

    def __init__(self, name, template):
        super(TemplateProposal, self).__init__(name, 'template')
        self.template = template


class Template(object):
    """Templates that are used in code assists

    Variables in templates are in ``${variable}`` format. To put a
    dollar sign in the template put $$.  To specify cursor position
    use ${cursor}.

    """

    def __init__(self, template):
        self.template = template

    var_pattern = re.compile(r'((?<=[^\$])|^)\${(?P<variable>\w+)}')

    def variables(self):
        """Get template variables

        Return the list of variables sorted by their order of
        occurence in the template.

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


def sorted_proposals(proposals, kindpref=None, typepref=None):
    """Sort a list of proposals

    Return a sorted list of the given `CodeAssistProposal`\s.

    `typepref` can be a list of proposal kinds.  Defaults to ``['local',
    'parameter_keyword', 'global', 'attribute', 'template', 'builtin',
    'keyword']``.

    `typepref` can be a list of proposal types.  Defaults to
    ``['class', 'function', 'variable', 'parameter', 'imported',
    None]``.  (`None` stands for completions with no type like
    keywords.)

    """
    sorter = _ProposalSorter(proposals, kindpref, typepref)
    return sorter.get_sorted_proposal_list()


def default_templates():
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
    return templates


class _PythonCodeAssist(object):

    def __init__(self, project, templates={}):
        self.project = project
        self.keywords = keyword.kwlist
        self.templates = templates

    def _find_starting_offset(self, source_code, offset):
        current_offset = offset - 1
        while current_offset >= 0 and (source_code[current_offset].isalnum() or
                                       source_code[current_offset] in '_'):
            current_offset -= 1;
        return current_offset + 1

    def _get_matching_keywords(self, starting):
        result = []
        for kw in self.keywords:
            if kw.startswith(starting):
                result.append(CompletionProposal(kw, 'keyword'))
        return result

    def add_template(self, name, definition):
        self.templates.append(TemplateProposal(name, Template(definition)))

    def _get_template_proposals(self, starting):
        result = []
        for name, template in self.templates.items():
            if name.startswith(starting):
                result.append(TemplateProposal(name, template))
        return result

    def _get_code_completions(self, source_code, offset,
                              expression, starting, resource):
        collector = _CodeCompletionCollector(self.project, source_code, offset,
                                             expression, starting, resource)
        return collector.get_code_completions()

    def assist(self, source_code, offset, resource=None):
        if offset > len(source_code):
            return []
        word_finder = WordRangeFinder(source_code)
        expression, starting, starting_offset = \
            word_finder.get_splitted_primary_before(offset)
        completions = list(
            self._get_code_completions(source_code, offset, expression,
                                       starting, resource).values())
        if expression.strip() == '' and starting.strip() != '':
            completions.extend(self._get_matching_keywords(starting))
            completions.extend(self._get_template_proposals(starting))
        return completions


class _ProposalSorter(object):
    """Sort a list of code assist proposals"""

    def __init__(self, code_assist_proposals, kindpref=None, typepref=None):
        self.proposals = code_assist_proposals
        if kindpref is None:
            kindpref = ['local', 'parameter_keyword', 'global', 'attribute',
                        'template', 'builtin', 'keyword']
        self.kindpref = kindpref
        if typepref is None:
            typepref = ['class', 'function', 'variable',
                        'parameter', 'imported', None]
        self.typerank = dict((type, index)
                              for index, type in enumerate(typepref))

    def get_sorted_proposal_list(self):
        """Return a list of `CodeAssistProposal`"""
        proposals = {}
        for proposal in self.proposals:
            proposals.setdefault(proposal.kind, []).append(proposal)
        result = []
        for kind in self.kindpref:
            kind_proposals = proposals.get(kind, [])
            if kind != 'template':
                kind_proposals = [proposal for proposal in kind_proposals
                                  if proposal.type in self.typerank]
            kind_proposals.sort(self._proposal_cmp)
            result.extend(kind_proposals)
        return result

    def _proposal_cmp(self, proposal1, proposal2):
        if 'template' not in (proposal1.kind, proposal2.kind) and \
           proposal1.type != proposal2.type:
            return cmp(self.typerank.get(proposal1.type, 100),
                       self.typerank.get(proposal2.type, 100))
        return self._compare_underlined_names(proposal1.name,
                                              proposal2.name)

    def _compare_underlined_names(self, name1, name2):
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


class _CodeCompletionCollector(object):

    def __init__(self, project, source_code,
                 offset, expression, starting, resource):
        self.project = project
        self.expression = expression
        self.starting = starting
        self.offset = offset
        self.pycore = self.project.get_pycore()
        self.source_code = source_code
        self.resource = resource

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
                if isinstance(pyname, builtins.BuiltinName):
                    kind = 'builtin'
                elif scope.get_kind() == 'Module':
                    kind = 'global'
                result[name] = CompletionProposal(
                    name, kind, self._get_pyname_type(pyname))

    def _get_pyname_type(self, pyname):
        if isinstance(pyname, (pynames.AssignedName, pynames.UnboundName)):
            return 'variable'
        if isinstance(pyname, pynames.ImportedName) or \
           isinstance(pyname, pynames.ImportedModule):
            return 'imported'
        if isinstance(pyname, pynames.ParameterName):
            return 'parameter'
        if isinstance(pyname, builtins.BuiltinName) or \
           isinstance(pyname, pynames.DefinedName):
            pyobject = pyname.get_object()
            if isinstance(pyobject, pyobjects.AbstractFunction):
                return 'function'
            if isinstance(pyobject, pyobjects.AbstractClass):
                return 'class'

    def get_code_completions(self):
        lines = self.source_code.split('\n')
        lineno = self.source_code.count('\n', 0, self.offset) + 1
        commenter = _Commenter(lines)
        commenter.comment(lineno)
        lines = commenter.lines
        source_code = '\n'.join(lines)
        module_scope = _get_pymodule(self.pycore, source_code,
                                    self.resource).get_scope()
        result = {}
        current_indents = _get_line_indents(lines[lineno - 1])
        inner_scope = module_scope.get_inner_scope_for_line(lineno,
                                                            current_indents)
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
        word_finder = WordRangeFinder(self.source_code)
        lines = SourceLinesAdapter(self.source_code)
        lineno = lines.get_line_number(offset)
        stop_line = LogicalLineFinder(lines).get_logical_line_in(lineno)[0]
        stop = lines.get_line_start(stop_line)
        if word_finder.is_on_function_call_keyword(offset - 1, stop):
            name_finder = ScopeNameFinder(pymodule)
            function_parens = word_finder.find_parens_start_from_inside(offset - 1, stop)
            primary = word_finder.get_primary_at(function_parens - 1)
            try:
                function_pyname = ScopeNameFinder.get_pyname_in_scope(scope,
                                                                      primary)
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
                    param_names.extend(
                        pyobject.get_param_names(special_args=False))
                    result = {}
                    for name in param_names:
                        if name.startswith(self.starting):
                            result[name + '='] = CompletionProposal(
                                name + '=', 'parameter_keyword')
                    return result
        return {}


class _Commenter(object):

    def __init__(self, lines):
        self.lines = lines

    def comment(self, lineno):
        logical_finder = LogicalLineFinder(ArrayLinesAdapter(self.lines))
        start = logical_finder.get_logical_line_in(lineno)[0] - 1
        end = self._get_block_end(start)
        last_indents = _get_line_indents(self.lines[start])
        self.lines[start] = ' ' * last_indents + 'pass'
        for line in range(start + 1, end + 1):
            #self.lines[line] = '#' # + lines[line]
            self.lines[line] = self.lines[start]
        self.lines.append('\n')
        self._fix_incomplete_try_blocks(lineno)

    def _get_block_end(self, lineno):
        end_line = lineno
        base_indents = _get_line_indents(self.lines[lineno])
        for i in range(lineno + 1, len(self.lines)):
            if _get_line_indents(self.lines[i]) >= base_indents:
                end_line = i
            else:
                break
        return end_line

    def _fix_incomplete_try_blocks(self, lineno):
        block_start = lineno
        last_indents = current_indents = _get_line_indents(
            self.lines[lineno - 1])
        while block_start > 0:
            block_start = rope.base.codeanalyze.get_block_start(
                ArrayLinesAdapter(self.lines), block_start) - 1
            if self.lines[block_start].strip().startswith('try:'):
                indents = _get_line_indents(self.lines[block_start])
                if indents > last_indents:
                    continue
                last_indents = indents
                block_end = self._find_matching_deindent(block_start)
                if not self.lines[block_end].strip().startswith('finally:') and \
                   not self.lines[block_end].strip().startswith('except '):
                    self.lines.insert(block_end, ' ' * indents + 'finally:')
                    self.lines.insert(block_end + 1, ' ' * indents + '    pass')

    def _find_matching_deindent(self, line_number):
        indents = _get_line_indents(self.lines[line_number])
        current_line = line_number + 1
        while current_line < len(self.lines):
            line = self.lines[current_line]
            if not line.strip().startswith('#') and not line.strip() == '':
                # HACK: We should have used logical lines here
                if _get_line_indents(self.lines[current_line]) <= indents:
                    return current_line
            current_line += 1
        return len(self.lines) - 1


def _get_pymodule(pycore, source_code, resource):
    if resource and resource.exists() and source_code == resource.read():
        return pycore.resource_to_pyobject(resource)
    return pycore.get_string_module(source_code, resource=resource)


def _get_line_indents(line):
    return rope.base.codeanalyze.count_line_indents(line)


class PyDocExtractor(object):

    def get_doc(self, pyobject):
        if isinstance(pyobject, pyobjects.AbstractFunction):
            return self._get_function_docstring(pyobject)
        elif isinstance(pyobject, pyobjects.AbstractClass):
            return self._get_class_docstring(pyobject)
        elif isinstance(pyobject, pyobjects.AbstractModule):
            return self._trim_docstring(pyobject.get_doc())
        return None

    def _get_class_docstring(self, pyclass):
        contents = self._trim_docstring(pyclass.get_doc(), 2)
        supers = [super.get_name() for super in pyclass.get_superclasses()]
        doc = 'class %s(%s):\n\n' % (pyclass.get_name(), ', '.join(supers)) + contents

        if '__init__' in pyclass.get_attributes():
            init = pyclass.get_attribute('__init__').get_object()
            if isinstance(init, pyobjects.AbstractFunction):
                doc += '\n\n' + self._get_single_function_docstring(init)
        return doc

    def _get_function_docstring(self, pyfunction):
        functions = [pyfunction]
        if self._is_method(pyfunction):
            functions.extend(self._get_super_methods(pyfunction.parent,
                                                     pyfunction.get_name()))
        return '\n\n'.join([self._get_single_function_docstring(function)
                            for function in functions])

    def _is_method(self, pyfunction):
        return isinstance(pyfunction, pyobjects.PyFunction) and \
               isinstance(pyfunction.parent, pyobjects.PyClass)

    def _get_single_function_docstring(self, pyfunction):
        signature = self._get_function_signature(pyfunction)
        if self._is_method(pyfunction):
            signature = pyfunction.parent.get_name() + '.' + signature
            self._get_super_methods(pyfunction.parent, pyfunction.get_name())
        return signature + ':\n\n' + self._trim_docstring(pyfunction.get_doc(),
                                                         indents=2)

    def _get_super_methods(self, pyclass, name):
        result = []
        for super_class in pyclass.get_superclasses():
            if name in super_class.get_attributes():
                function = super_class.get_attribute(name).get_object()
                if isinstance(function, pyobjects.AbstractFunction):
                    result.append(function)
            result.extend(self._get_super_methods(super_class, name))
        return result

    def _get_function_signature(self, pyfunction):
        if isinstance(pyfunction, pyobjects.PyFunction):
            info = functionutils.DefinitionInfo.read(pyfunction)
            return info.to_string()
        else:
            return '%s(%s)' % (pyfunction.get_name(),
                               ', '.join(pyfunction.get_param_names()))

    def _trim_docstring(self, docstring, indents=0):
        """The sample code from :PEP:`257`"""
        if not docstring:
            return ''
        # Convert tabs to spaces (following normal Python rules)
        # and split into a list of lines:
        lines = docstring.expandtabs().splitlines()
        # Determine minimum indentation (first line doesn't count):
        indent = sys.maxint
        for line in lines[1:]:
            stripped = line.lstrip()
            if stripped:
                indent = min(indent, len(line) - len(stripped))
        # Remove indentation (first line is special):
        trimmed = [lines[0].strip()]
        if indent < sys.maxint:
            for line in lines[1:]:
                trimmed.append(line[indent:].rstrip())
        # Strip off trailing and leading blank lines:
        while trimmed and not trimmed[-1]:
            trimmed.pop()
        while trimmed and not trimmed[0]:
            trimmed.pop(0)
        # Return a single string:
        return '\n'.join((' ' * indents + line for line in trimmed))
