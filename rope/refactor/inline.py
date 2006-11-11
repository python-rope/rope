import re

import rope.base.exceptions
import rope.base.pynames
import rope.base.pyobjects
from rope.base import codeanalyze
from rope.refactor import sourceutils
from rope.refactor.change import ChangeSet, ChangeContents


class InlineRefactoring(object):
    
    def __init__(self, pycore, resource, offset):
        self.pycore = pycore
        self.pyname = codeanalyze.get_pyname_at(self.pycore, resource, offset)
        self.name = codeanalyze.get_name_at(resource, offset)
        if self.name is None:
            raise rope.base.exceptions.RefactoringException(
                'Inline refactoring should be performed on a method/local variable.')
        if self._is_variable():
            self.performer = _VariableInliner(pycore, self.name, self.pyname)
        elif self._is_method():
            self.performer = _MethodInliner(pycore, self.name, self.pyname)
        else:
            raise rope.base.exceptions.RefactoringException(
                'Inline refactoring should be performed on a method/local variable.')
        self.performer.check_exceptional_conditions()
    
    def get_changes(self):
        return self.performer.get_changes()
    
    def _is_variable(self):
        return isinstance(self.pyname, rope.base.pynames.AssignedName)

    def _is_method(self):
        return isinstance(self.pyname.get_object(), rope.base.pyobjects.PyFunction)


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
        self.occurrence_finder = rope.refactor.occurrences.FilteredOccurrenceFinder(
            self.pycore, self.name, [self.pyname])
        self.definition_generator = _DefinitionGenerator(self.pycore, self.pyfunction)
    
    def _get_scope_range(self):
        scope = self.pyfunction.get_scope()
        lines = self.pymodule.lines
        start_offset = lines.get_line_start(scope.get_start())
        end_offset = min(lines.get_line_end(scope.get_end()) + 1,
                         len(self.pymodule.source_code))
        return (start_offset, end_offset)
    
    def get_changes(self):
        changes = ChangeSet()
        self._change_defining_file(changes)
        self._change_other_files(changes)
        return changes

    def _change_defining_file(self, changes):
        start_offset, end_offset = self._get_scope_range()
        result = _InlineFunctionCallsForModule(
            self.occurrence_finder, self.resource,
            self.definition_generator,
            start_offset, end_offset).get_changed_module()
        changes.add_change(ChangeContents(self.resource, result))
    
    def _change_other_files(self, changes):
        for file in self.pycore.get_python_files():
            if file == self.resource:
                continue
            start, end = self._get_scope_range()
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
        if len(self.pyname.assigned_asts) != 1:
            raise rope.base.exceptions.RefactoringException(
                'Local variable should be assigned once or inlining.')

    def get_changes(self):
        source = self._get_changed_module()
        changes = ChangeSet()
        changes.add_change(ChangeContents(self.resource, source))
        return changes

    def _get_changed_module(self):
        definition_line = self.pyname.assigned_asts[0].lineno
        lines = self.pymodule.lines
        start, end = codeanalyze.LogicalLineFinder(lines).\
                     get_logical_line_in(definition_line)
        definition_lines = []
        for line_number in range(start, end + 1):
            line = lines.get_line(line_number).strip()
            if line.endswith('\\'):
                line = line[:-1]
            definition_lines.append(line)
        definition_with_assignment = ' '.join(definition_lines)
        if self._is_tuple_assignment(definition_with_assignment):
            raise rope.base.exceptions.RefactoringException(
                'Cannot inline tuple assignments.')
        definition = definition_with_assignment[definition_with_assignment.\
                                                index('=') + 1:].strip()

        changed_source = rope.refactor.rename.RenameInModule(
            self.pycore, [self.pyname], self.name, definition,
            replace_primary=True).get_changed_module(pymodule=self.pymodule)
        if changed_source is None:
            changed_source = self.pymodule.source_code
        lines = codeanalyze.SourceLinesAdapter(changed_source)
        source = changed_source[:lines.get_line_start(start)] + \
                 changed_source[lines.get_line_end(end) + 1:]
        return source
    
    def _is_tuple_assignment(self, line):
        try:
            comma = line.index(',')
            assign = line.index('=')
            return comma < assign
        except ValueError:
            return False


class _InlineFunctionCallsForModule(object):
    
    def __init__(self, occurrence_finder, resource, definition_generator,
                 skip_start=0, skip_end=0):
        self.pycore = occurrence_finder.pycore
        self.occurrence_finder = occurrence_finder
        self.generator = definition_generator
        self.resource = resource
        self._pymodule = None
        self._lines = None
        self._source = None
        self.skip_start = skip_start
        self.skip_end = skip_end

    def get_changed_module(self):
        result = []
        last_changed = 0
        for occurrence in self.occurrence_finder.find_occurrences(self.resource):
            start, end = occurrence.get_primary_range()
            if self.skip_start <= start < self.skip_end:
                if occurrence.is_defined():
                    continue
                else:
                    raise rope.base.exceptions.RefactoringException(
                        'Cannot inline functions that reference themselves')
            if not occurrence.is_called():
                    raise rope.base.exceptions.RefactoringException(
                        'Reference to inlining function other than function call'
                        ' in <file: %s, offset: %d>' % (self.resource.get_path(),
                                                        start))
            end_parens = self._find_end_parens(self.source,
                                               self.source.index('(', end))
            lineno = self.lines.get_line_number(start)
            start_line, end_line = codeanalyze.LogicalLineFinder(self.lines).\
                                   get_logical_line_in(lineno)
            line_start = self.lines.get_line_start(start_line)
            line_end = self.lines.get_line_end(end_line)
            returns = self.source[line_start:start].strip() != '' or \
                      self.source[end_parens:line_end].strip() != ''
            if last_changed <= self.skip_start and 0 < self.skip_end <= start:
                result.append(self.source[last_changed:self.skip_start])
                last_changed = self.skip_end
            result.append(self.source[last_changed:line_start])
            indents = sourceutils.get_indents(self.lines, start_line)
            definition = self.generator.get_definition(self.source[start:end_parens],
                                                       returns=returns)
            result.append(sourceutils.fix_indentation(definition, indents))
            if returns:
                name = self.generator.get_function_name() + '_result'
                end = min(line_end + 1, len(self.source))
                result.append(self.source[line_start:start] + name +
                              self.source[end_parens:end])
            last_changed = line_end + 1
        
        if result or self.skip_end > 0:
            if last_changed <= self.skip_start and self.skip_end > 0:
                result.append(self.source[last_changed:self.skip_start])
                last_changed = self.skip_end
            result.append(self.source[max(last_changed, self.skip_end):])
            return ''.join(result)
    
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
        self._definition_param = None
        self._calculated_definitions = {}
    
    def _get_function_body(self):
        scope = self.pyfunction.get_scope()
        source = self.pymodule.source_code
        lines = self.pymodule.lines
        start_line = codeanalyze.LogicalLineFinder(lines).\
                     get_logical_line_in(scope.get_start())[1] + 1
        start_offset = lines.get_line_start(start_line)
        end_offset = min(lines.get_line_end(scope.get_end()) + 1, len(source))
        body = source[start_offset:end_offset]
        return sourceutils.indent_lines(body, -sourceutils.find_minimum_indents(body))
    
    def _get_function_header_without_def_and_colon(self):
        scope = self.pyfunction.get_scope()
        source = self.pymodule.source_code
        lines = self.pymodule.lines
        start_line, end_line = codeanalyze.LogicalLineFinder(lines).\
                               get_logical_line_in(scope.get_start())
        start_offset = lines.get_line_start(start_line)
        end_offset = lines.get_line_end(end_line)
        header = source[start_offset:end_offset]
        def_index = header.index('def')
        colon_index = header.rindex(':')
        return header[def_index + 4:colon_index]
    
    def _get_definition_params(self):
        if self._definition_param is None:
            header = self._get_function_header_without_def_and_colon()
            call_analyzer = _CallAnalyzer(self.pyfunction, header)
            paramdict = call_analyzer.get_passed_parameters()
            for value in paramdict.values():
                if value.startswith('*'):
                    raise rope.base.exceptions.RefactoringException(
                        'Cannot functions with list and keyword arguements.')
            self._definition_param = paramdict
        return self._definition_param
    
    def get_function_name(self):
        return self.pyfunction._get_ast().name
    
    def get_definition(self, call, returns=False):
        # caching already calculated definitions
        key = (call, returns)
        if key not in self._calculated_definitions:
            self._calculated_definitions[key] = self._calculate_definition(call, returns)
        return self._calculated_definitions[key]
    
    def _calculate_definition(self, call, returns):
        call_analyzer = _CallAnalyzer(self.pyfunction, call)
        paramdict = self._get_definition_params()
        for param_name, value in call_analyzer.get_passed_parameters().iteritems():
            paramdict[param_name] = value
        header = ""
        to_be_inlined = []
        for name, value in paramdict.iteritems():
            if name != value:
                header += name + ' = ' + value + '\n'
                to_be_inlined.append(name)
        source = header + self._get_function_body()
        for name in to_be_inlined:
            pymodule = self.pycore.get_string_module(source, self.resource)
            pyname = pymodule.get_attribute(name)
            inliner = _VariableInliner(self.pycore, name, pyname)
            source = inliner._get_changed_module()
        if returns:
            return_replacement = self.get_function_name() + '_result' + ' ='
        else:
            return_replacement = None
        return self._replace_returns_with(source, return_replacement)
    
    def _replace_returns_with(self, source, replacement):
        result = []
        last_changed = 0
        for match in _DefinitionGenerator._get_return_pattern().finditer(source):
            for key, value in match.groupdict().items():
                if value and key == 'return':
                    result.append(source[last_changed:match.start('return')])
                    if replacement is not None:
                        result.append(replacement)
                        last_changed = match.end('return')
                        current = last_changed
                        while current < len(source) and source[current] != '\n':
                            current += 1
                        if current != len(source) and source[current:].strip() != '':
                            raise rope.base.exceptions.RefactoringException(
                                'Cannot inline functions with statements after return statement.')
                    else:
                        current = match.end('return')
                        while current < len(source) and source[current] in ' \t':
                            current += 1
                        last_changed = current
                        if current == len(source) or source[current] == '\n':
                            result.append('pass')
        result.append(source[last_changed:])
        return ''.join(result)
    
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


class _CallAnalyzer(object):
    
    def __init__(self, pyfunction, call):
        self.pyfunction = pyfunction
        self.call = call
    
    def get_passed_parameters(self):
        word_finder = codeanalyze.WordRangeFinder(self.call)
        last_parens = self.call.rindex(')')
        first_parens = word_finder._find_parens_start(last_parens)
        result = {}
        params = []
        current = last_parens - 1
        current = word_finder._find_last_non_space_char(current)
        while current > first_parens:
            primary_start = current
            while current != first_parens and self.call[current] not in '=,':
                current = word_finder._find_last_non_space_char(current - 1)
            primary = self.call[current + 1:primary_start + 1].strip()
            if self.call[current] == '=':
                primary_start = current - 1
                current -= 1
                while current != first_parens and self.call[current] not in ',':
                    current = word_finder._find_last_non_space_char(current - 1)
                param_name = self.call[current + 1:primary_start + 1].strip()
                result[param_name] = primary
            else:
                params.append(primary)
            current = word_finder._find_last_non_space_char(current - 1)
        parameter_names = self.pyfunction.parameters
        if self._is_called_as_a_method() and '.' in self.call[:first_parens]:
            params.append(word_finder.get_primary_at(
                          self.call.rindex('.', 0, first_parens) - 1))
        params.reverse()
        for index, name in enumerate(parameter_names):
            if index < len(params):
                result[name] = params[index]
        return result

    def _is_called_as_a_method(self):
        scope = self.pyfunction.get_scope()
        parent = scope.parent
        parameter_names = self.pyfunction.parameters
        return len(parameter_names) > 0 and \
               (parent.pyobject == self.pyfunction.
                get_parameters()[parameter_names[0]].get_object().get_type()) and \
               parent is not None and \
               parent.pyobject.get_type() == \
               rope.base.pyobjects.PyObject.get_base_type('Type')
