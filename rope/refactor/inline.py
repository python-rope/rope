import re

import rope.base.exceptions
import rope.refactor.functionutils
from rope.base import pynames, pyobjects, codeanalyze
from rope.base.change import ChangeSet, ChangeContents
from rope.refactor import occurrences, rename, sourceutils


class Inline(object):

    def __init__(self, project, resource, offset):
        self.pycore = project.pycore
        self.pyname = codeanalyze.get_pyname_at(self.pycore, resource, offset)
        self.name = codeanalyze.get_name_at(resource, offset)
        if self.pyname is None:
            raise rope.base.exceptions.RefactoringError(
                'Inline refactoring should be performed on a method/local variable.')
        if self._is_variable():
            self.performer = _VariableInliner(self.pycore, self.name,
                                              self.pyname)
        elif self._is_function():
            self.performer = _MethodInliner(self.pycore, self.name,
                                            self.pyname)
        else:
            raise rope.base.exceptions.RefactoringError(
                'Inline refactoring should be performed on a method/local variable.')
        self.performer.check_exceptional_conditions()

    def get_changes(self):
        return self.performer.get_changes()

    def _is_variable(self):
        return isinstance(self.pyname, pynames.AssignedName)

    def _is_function(self):
        return isinstance(self.pyname.get_object(), pyobjects.PyFunction)


class _Inliner(object):

    def __init__(self, pycore, name, pyname):
        self.pycore = pycore
        self.name = name
        self.pyname = pyname

    def check_exceptional_conditions(self):
        pass

    def get_changes(self):
        pass


class _MethodInliner(_Inliner):

    def __init__(self, *args, **kwds):
        super(_MethodInliner, self).__init__(*args, **kwds)
        self.pyfunction = self.pyname.get_object()
        self.pymodule = self.pyfunction.get_module()
        self.resource = self.pyfunction.get_module().get_resource()
        self.occurrence_finder = rope.refactor.occurrences.FilteredFinder(
            self.pycore, self.name, [self.pyname])
        self.definition_generator = _DefinitionGenerator(self.pycore, self.pyfunction)

    def _get_scope_range(self):
        scope = self.pyfunction.get_scope()
        lines = self.pymodule.lines
        start_line = scope.get_start()
        if self.pyfunction.get_ast().decorators is not None:
            decorators = self.pyfunction.get_ast().decorators
            if hasattr(decorators.nodes[0], 'lineno'):
                start_line = decorators.nodes[0].lineno
        start_offset = lines.get_line_start(start_line)
        end_offset = min(lines.get_line_end(scope.get_end()) + 1,
                         len(self.pymodule.source_code))
        return (start_offset, end_offset)

    def get_changes(self):
        changes = ChangeSet('Inline method <%s>' % self.name)
        self._change_defining_file(changes)
        self._change_other_files(changes)
        return changes

    def _change_defining_file(self, changes):
        start_offset, end_offset = self._get_scope_range()
        result = _InlineFunctionCallsForModule(
            self.occurrence_finder, self.resource,
            self.definition_generator,
            start_offset, end_offset,
            self._get_method_replacement()).get_changed_module()
        changes.add_change(ChangeContents(self.resource, result))

    def _get_method_replacement(self):
        if self._is_the_last_method_of_a_class():
            indents = sourceutils.get_indents(
                self.pymodule.lines, self.pyfunction.get_scope().get_start())
            return ' ' * indents + 'pass\n'
        return ''

    def _is_the_last_method_of_a_class(self):
        pyclass = self.pyfunction.parent
        if not isinstance(pyclass, pyobjects.PyClass):
            return False
        class_start, class_end = sourceutils.get_body_region(pyclass)
        source = self.pymodule.source_code
        lines = self.pymodule.lines
        func_start, func_end = self._get_scope_range()
        if source[class_start:func_start].strip() == '' and \
           source[func_end:class_end].strip() == '':
            return True
        return False

    def _change_other_files(self, changes):
        for file in self.pycore.get_python_files():
            if file == self.resource:
                continue
            result = _InlineFunctionCallsForModule(
                self.occurrence_finder, file,
                self.definition_generator).get_changed_module()
            if result is not None:
                changes.add_change(ChangeContents(file, result))


class _VariableInliner(_Inliner):

    def __init__(self, *args, **kwds):
        super(_VariableInliner, self).__init__(*args, **kwds)
        self.pymodule = self.pyname.get_definition_location()[0]
        self.resource = self.pymodule.get_resource()

    def check_exceptional_conditions(self):
        if len(self.pyname.assignments) != 1:
            raise rope.base.exceptions.RefactoringError(
                'Local variable should be assigned once for inlining.')

    def get_changes(self):
        source = self._get_changed_module()
        changes = ChangeSet('Inline variable <%s>' % self.name)
        changes.add_change(ChangeContents(self.resource, source))
        return changes

    def _get_changed_module(self):
        assignment = self.pyname.assignments[0]
        definition_line = assignment.ast_node.lineno
        lines = self.pymodule.lines
        start, end = codeanalyze.LogicalLineFinder(lines).\
                     get_logical_line_in(definition_line)
        definition_with_assignment = _join_lines(
            [lines.get_line(n) for n in range(start, end + 1)])
        if assignment.levels:
            raise rope.base.exceptions.RefactoringError(
                'Cannot inline tuple assignments.')
        definition = definition_with_assignment[definition_with_assignment.\
                                                index('=') + 1:].strip()

        occurrence_finder = occurrences.FilteredFinder(
            self.pycore, self.name, [self.pyname])
        changed_source = rename.rename_in_module(
            occurrence_finder, definition, pymodule=self.pymodule, replace_primary=True)
        if changed_source is None:
            changed_source = self.pymodule.source_code
        lines = codeanalyze.SourceLinesAdapter(changed_source)
        source = changed_source[:lines.get_line_start(start)] + \
                 changed_source[lines.get_line_end(end) + 1:]
        return source


def _join_lines(lines):
    definition_lines = []
    for unchanged_line in lines:
        line = unchanged_line.strip()
        if line.endswith('\\'):
            line = line[:-1].strip()
        definition_lines.append(line)
    joined = ' '.join(definition_lines)
    return joined


class _InlineFunctionCallsForModule(object):

    def __init__(self, occurrence_finder, resource, definition_generator,
                 skip_start=0, skip_end=0, replacement=''):
        self.pycore = occurrence_finder.pycore
        self.occurrence_finder = occurrence_finder
        self.generator = definition_generator
        self.resource = resource
        self._pymodule = None
        self._lines = None
        self._source = None
        self.skip_start = skip_start
        self.skip_end = skip_end
        self.replacement = replacement

    def get_changed_module(self):
        change_collector = sourceutils.ChangeCollector(self.source)
        change_collector.add_change(self.skip_start, self.skip_end,
                                    self.replacement)
        for occurrence in self.occurrence_finder.find_occurrences(self.resource):
            start, end = occurrence.get_primary_range()
            if self.skip_start <= start < self.skip_end:
                if occurrence.is_defined():
                    continue
                else:
                    raise rope.base.exceptions.RefactoringError(
                        'Cannot inline functions that reference themselves')
            if not occurrence.is_called():
                raise rope.base.exceptions.RefactoringError(
                    'Reference to inlining function other than function call'
                    ' in <file: %s, offset: %d>' % (self.resource.path, start))
            end_parens = self._find_end_parens(self.source,
                                               self.source.index('(', end))
            lineno = self.lines.get_line_number(start)
            start_line, end_line = codeanalyze.LogicalLineFinder(self.lines).\
                                   get_logical_line_in(lineno)
            line_start = self.lines.get_line_start(start_line)
            line_end = self.lines.get_line_end(end_line)
            returns = self.source[line_start:start].strip() != '' or \
                      self.source[end_parens:line_end].strip() != ''
            indents = sourceutils.get_indents(self.lines, start_line)
            primary, pyname = occurrence.get_primary_and_pyname()
            definition = self.generator.get_definition(
                primary, pyname, self.source[start:end_parens], returns=returns)
            end = min(line_end + 1, len(self.source))
            change_collector.add_change(
                line_start, end, sourceutils.fix_indentation(definition, indents))
            if returns:
                name = self.generator.get_returned()
                if name is None:
                    name = 'None'
                change_collector.add_change(
                    line_end, end, self.source[line_start:start] + name +
                    self.source[end_parens:end])
        result = change_collector.get_changed()
        if result is not None and result != self.source:
            return result

    def _get_pymodule(self):
        if self._pymodule is None:
            self._pymodule = self.pycore.resource_to_pyobject(self.resource)
        return self._pymodule

    def _get_source(self):
        if self._source is None:
            if self.resource is not None:
                self._source = self.resource.read()
            else:
                self._source = self.pymodule.source_code
        return self._source

    def _get_lines(self):
        if self._lines is None:
            self._lines = self.pymodule.lines
        return self._lines

    def _find_end_parens(self, source, start):
        index = start
        open_count = 0
        while index < len(source):
            if source[index] == '(':
                open_count += 1
            if source[index] == ')':
                open_count -= 1
            if open_count == 0:
                return index + 1
            index += 1
        return index

    source = property(_get_source)
    lines = property(_get_lines)
    pymodule = property(_get_pymodule)


class _DefinitionGenerator(object):

    def __init__(self, pycore, pyfunction):
        self.pycore = pycore
        self.pyfunction = pyfunction
        self.pymodule = pyfunction.get_module()
        self.resource = self.pymodule.get_resource()
        self.definition_info = self._get_definition_info()
        self.definition_params = self._get_definition_params()
        self._calculated_definitions = {}
        self.returned = None

    def _get_definition_info(self):
        return rope.refactor.functionutils.DefinitionInfo.read(self.pyfunction)

    def _get_definition_params(self):
        definition_info = self.definition_info
        paramdict = dict([pair for pair in definition_info.args_with_defaults])
        if definition_info.args_arg is not None or \
           definition_info.keywords_arg is not None:
            raise rope.base.exceptions.RefactoringError(
                'Cannot inline functions with list and keyword arguements.')
        return paramdict

    def get_function_name(self):
        return self.pyfunction.get_name()

    def get_definition(self, primary, pyname, call, returns=False):
        # caching already calculated definitions
        key = (call, returns)
        if key not in self._calculated_definitions:
            self._calculated_definitions[key] = self._calculate_definition(
                primary, pyname, call, returns)
        return self._calculated_definitions[key]

    def _calculate_definition(self, primary, pyname, call, returns):
        call_info = rope.refactor.functionutils.CallInfo.read(
            primary, pyname, self.definition_info, call)
        paramdict = self.definition_params
        mapping = rope.refactor.functionutils.ArgumentMapping(self.definition_info,
                                                              call_info)
        for param_name, value in mapping.param_dict.iteritems():
            paramdict[param_name] = value
        header = ""
        to_be_inlined = []
        for name, value in paramdict.iteritems():
            if name != value:
                header += name + ' = ' + value + '\n'
                to_be_inlined.append(name)
        source = header + sourceutils.get_body(self.pyfunction)
        for name in to_be_inlined:
            pymodule = self.pycore.get_string_module(source, self.resource)
            pyname = pymodule.get_attribute(name)
            inliner = _VariableInliner(self.pycore, name, pyname)
            source = inliner._get_changed_module()
        return self._replace_returns_with(source, returns)

    def get_returned(self):
        return self.returned

    def _replace_returns_with(self, source, returns):
        result = []
        last_changed = 0
        for match in _DefinitionGenerator._get_return_pattern().finditer(source):
            for key, value in match.groupdict().items():
                if value and key == 'return':
                    result.append(source[last_changed:match.start('return')])
                    if returns:
                        self._check_nothing_after_return(source,
                                                         match.end('return'))
                        self.returned = _join_lines(
                            source[match.end('return'): len(source)].splitlines())
                        last_changed = len(source)
                    else:
                        current = match.end('return')
                        while current < len(source) and source[current] in ' \t':
                            current += 1
                        last_changed = current
                        if current == len(source) or source[current] == '\n':
                            result.append('pass')
        result.append(source[last_changed:])
        return ''.join(result)

    def _check_nothing_after_return(self, source, offset):
        lines = codeanalyze.SourceLinesAdapter(source)
        lineno = lines.get_line_number(offset)
        logical_lines = codeanalyze.LogicalLineFinder(lines)
        lineno = logical_lines.get_logical_line_in(lineno)[1]
        if source[lines.get_line_end(lineno):len(source)].strip() != '':
            raise rope.base.exceptions.RefactoringError(
                'Cannot inline functions with statements after return statement.')

    @classmethod
    def _get_return_pattern(cls):
        if not hasattr(cls, '_return_pattern'):
            def named_pattern(name, list_):
                return "(?P<%s>" % name + "|".join(list_) + ")"
            comment_pattern = named_pattern('comment', [r'#[^\n]*'])
            sqstring = r"(\b[rR])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
            dqstring = r'(\b[rR])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
            sq3string = r"(\b[rR])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?"
            dq3string = r'(\b[rR])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?'
            string_pattern = named_pattern('string', [sq3string, dq3string, sqstring, dqstring])
            return_pattern = r'\b(?P<return>return)\b'
            cls._return_pattern = re.compile(comment_pattern + "|" +
                                             string_pattern + "|" +
                                             return_pattern)
        return cls._return_pattern
