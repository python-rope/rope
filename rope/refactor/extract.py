import compiler
import re

import rope.base.pyobjects
from rope.base import codeanalyze
from rope.base.change import ChangeSet, ChangeContents
from rope.base.exceptions import RefactoringError
from rope.refactor import sourceutils


class _ExtractRefactoring(object):

    def __init__(self, project, resource, start_offset, end_offset,
                 variable=False):
        self.project = project
        self.pycore = project.pycore
        self.resource = resource
        self.start_offset = self._fix_start(resource.read(), start_offset)
        self.end_offset = self._fix_end(resource.read(), end_offset)
        self.variable = variable

    def _fix_start(self, source, offset):
        while offset < len(source) and source[offset].isspace():
            offset += 1
        return offset

    def _fix_end(self, source, offset):
        while offset > 0 and source[offset - 1].isspace():
            offset -= 1
        return offset

    def get_changes(self, extracted_name):
        info = _ExtractInfo(
            self.project, self.resource, self.start_offset,
            self.end_offset, extracted_name, variable=self.variable)
        new_contents = _ExtractPerformer(info).extract()
        changes = ChangeSet('Extract %s <%s>' % (self._get_name(),
                                                 extracted_name))
        changes.add_change(ChangeContents(self.resource, new_contents))
        return changes

    def _get_name(self):
        if self.variable:
            return 'variable'
        return 'method'
            

class ExtractMethod(_ExtractRefactoring):

    def __init__(self, *args, **kwds):
        super(ExtractMethod, self).__init__(*args, **kwds)


class ExtractVariable(_ExtractRefactoring):

    def __init__(self, *args, **kwds):
        kwds = dict(kwds)
        kwds['variable'] = True
        super(ExtractVariable, self).__init__(*args, **kwds)


class _ExtractInfo(object):

    def __init__(self, project, resource, start, end, new_name, variable=False):
        self.pycore = project.pycore
        self.resource = resource
        self.pymodule = self.pycore.resource_to_pyobject(resource)
        self.global_scope = self.pymodule.get_scope()
        self.source = self.pymodule.source_code
        self.lines = self.pymodule.lines
        self.new_name = new_name
        self.variable = variable
        self._init_parts(start, end)
        self._init_scope()

    def _init_parts(self, start, end):
        self.line_finder = codeanalyze.LogicalLineFinder(self.lines)

        self.region = (self._choose_closest_line_end(start),
                       self._choose_closest_line_end(end, end=True))

        self.region_lines = (
            self.line_finder.get_logical_line_in(self.lines.get_line_number(self.region[0]))[0],
            self.line_finder.get_logical_line_in(self.lines.get_line_number(self.region[1]))[1])

        self.lines_region = (self.lines.get_line_start(self.region_lines[0]),
                             self.lines.get_line_end(self.region_lines[1]))


    def _init_scope(self):
        start_line = self.region_lines[0]
        scope = self.global_scope.get_inner_scope_for_line(start_line)
        if scope.get_kind() != 'Module' and \
           scope.get_start() == start_line:
            scope = scope.parent
        self.scope = scope
        self.scope_region = (self.lines.get_line_start(self.scope.get_start()),
                             self.lines.get_line_end(self.scope.get_end()) + 1)

    def _choose_closest_line_end(self, offset, end=False):
        lineno = self.lines.get_line_number(offset)
        line_start = self.lines.get_line_start(lineno)
        line_end = self.lines.get_line_end(lineno)
        if self.source[line_start:offset].strip() == '':
            if end:
                return line_start - 1
            else:
                return line_start
        elif self.source[offset:line_end].strip() == '':
            return min(line_end, len(self.source))
        return offset

    def _is_one_line(self):
        return self.region != self.lines_region and \
               (self.line_finder.get_logical_line_in(self.region_lines[0]) ==
                self.line_finder.get_logical_line_in(self.region_lines[1]))

    def _is_global(self):
        return self.scope.parent is None

    def _is_method(self):
        return self.scope.parent is not None and \
               self.scope.parent.get_kind() == 'Class'

    one_line = property(_is_one_line)
    global_ = property(_is_global)
    method = property(_is_method)

    def _get_indents(self):
        return sourceutils.get_indents(self.pymodule.lines,
                                       self.region_lines[0])

    def _get_scope_indents(self):
        if self.global_:
            return 0
        return sourceutils.get_indents(self.pymodule.lines,
                                       self.scope.get_start())

    def _get_extracted(self):
        return self.source[self.region[0]:self.region[1]]

    indents = property(_get_indents)
    scope_indents = property(_get_scope_indents)
    extracted = property(_get_extracted)


class _ExceptionalConditionChecker(object):

    def __call__(self, info):
        self.base_conditions(info)
        if info.one_line:
            self.one_line_conditions(info)
        else:
            self.multi_line_conditions(info)

    def base_conditions(self, info):
        if info.scope.get_kind() == 'Class':
            raise RefactoringError('Can not extract methods in class body')
        if info.region[1] > info.scope_region[1]:
            raise RefactoringError('Bad range selected for extract method')
        end_line = info.region_lines[1]
        end_scope = info.global_scope.get_inner_scope_for_line(end_line)
        if end_scope != info.scope and end_scope.get_end() != end_line:
            raise RefactoringError('Bad range selected for extract method')
        try:
            if _ReturnOrYieldFinder.does_it_return(
                info.source[info.region[0]:info.region[1]]):
                raise RefactoringError('Extracted piece should not contain return statements.')
            if _UnmatchedBreakOrContinueFinder.has_errors(
                info.source[info.region[0]:info.region[1]]):
                raise RefactoringError(
                    'A break/continue without matching having a for/while loop.')
        except SyntaxError:
            raise RefactoringError('Extracted piece should contain complete statements.')

    def one_line_conditions(self, info):
        if self._is_region_on_a_word(info):
            raise RefactoringError('Should extract complete statements.')
        if info.variable and not info.one_line:
            raise RefactoringError('Extract variable should not span multiple lines.')

    def multi_line_conditions(self, info):
        if info.region != info.lines_region:
            raise RefactoringError('Extracted piece should contain complete statements.')

    def _is_region_on_a_word(self, info):
        if info.region[0] > 0 and self._is_on_a_word(info, info.region[0] - 1) or \
           self._is_on_a_word(info, info.region[1] - 1):
            return True

    def _is_on_a_word(self, info, offset):
        prev = info.source[offset]
        next = info.source[offset + 1]
        return (prev.isalnum() or prev == '_') and (next.isalnum() or next == '_')


class _ExtractPerformer(object):
    """Perform extract method/variable refactoring

    We devide program source code into these parts::

      [...]
        scope_start
            [before_line]
        start_line
          start
            [call]
          end
        end_line
        scope_end
            [after_scope]
      [...]

    For extract function the new method is inserted in start_line,
    while in extract method it is inserted in scope_end.

    Note that start and end are in the same line for one line
    extractions, so start_line and end_line are in the same line,
    too.

    The before_line, call, and after_scope placeholders can be
    set by using `_ExtractMethodParts` or `_ExtractVariableParts`.

    """

    def __init__(self, info):
        self.info = info

        self.extract_info = self._create_parts()

        _ExceptionalConditionChecker()(self.info)

    def _create_parts(self):
        if self.info.variable:
            return _ExtractVariableParts(self.info)
        else:
            return _ExtractMethodParts(self.info)

    def extract(self):
        result = []
        source = self.info.source
        result.append(source[:self.info.lines_region[0]])
        result.append(self.extract_info.get_before_line())
        if self.info.lines_region[0] != self.info.region[0]:
            result.append(source[self.info.lines_region[0]:self.info.region[0]])
        else:
            result.append(' ' * self.info.indents)
        result.append(self.extract_info.get_call())
        result.append(source[self.info.region[1]:self.info.lines_region[1]])
        result.append(source[self.info.lines_region[1]:self.info.scope_region[1]])
        result.append(self.extract_info.get_after_scope())
        result.append(source[self.info.scope_region[1]:])
        return ''.join(result)


class _ExtractMethodParts(object):

    def __init__(self, info):
        self.info = info
        self.info_collector = self._create_info_collector()

    def get_before_line(self):
        if self.info.global_:
            return '\n%s\n' % self._get_function_definition()
        return ''

    def get_call(self):
        return self._get_call()

    def get_after_scope(self):
        if not self.info.global_:
            return '\n%s' % self._get_function_definition()
        return ''

    def _create_info_collector(self):
        zero = self.info.scope.get_start() - 1
        start_line = self.info.region_lines[0] - zero
        end_line = self.info.region_lines[1] - zero
        info_collector = _FunctionInformationCollector(start_line, end_line,
                                                       self.info.global_)
        indented_body = self.info.source[self.info.scope_region[0]:
                                         self.info.scope_region[1]]
        body = sourceutils.fix_indentation(indented_body, 0)
        ast = _parse_text(body)
        compiler.walk(ast, info_collector)
        return info_collector

    def _get_function_indents(self):
        if self.info.global_:
            return self.info.indents
        else:
            return self.info.scope_indents

    def _get_function_definition(self):
        args = self._find_function_arguments()
        returns = self._find_function_returns()
        function_indents = self._get_function_indents()
        result = []
        result.append('%sdef %s:\n' %
                      (' ' * function_indents,
                       self._get_function_signature(args)))
        unindented_body = self._get_unindented_function_body(returns)
        indents = function_indents + sourceutils.get_indent(self.info.pycore)
        function_body = sourceutils.indent_lines(unindented_body, indents)
        result.append(function_body)
        definition = ''.join(result)

        return definition + '\n'

    def _get_function_signature(self, args):
        args = list(args)
        if self.info.method:
            if 'self' in args:
                args.remove('self')
            args.insert(0, 'self')
        return self.info.new_name + '(%s)' % self._get_comma_form(args)

    def _get_function_call(self, args):
        prefix = ''
        if self.info.method:
            if  'self' in args:
                args.remove('self')
            prefix = 'self.'
        return prefix + '%s(%s)' % (self.info.new_name, self._get_comma_form(args))

    def _get_comma_form(self, names):
        result = ''
        if names:
            result += names[0]
            for name in names[1:]:
                result += ', ' + name
        return result

    def _get_call(self):
        if self.info.one_line:
            args = self._find_function_arguments()
            return self._get_function_call(args)
        args = self._find_function_arguments()
        returns = self._find_function_returns()
        call_prefix = ''
        if returns:
            call_prefix = self._get_comma_form(returns) + ' = '
        return call_prefix + self._get_function_call(args)

    def _find_function_arguments(self):
        if not self.info.one_line:
            return list(self.info_collector.prewritten.
                        intersection(self.info_collector.read))
        start = self.info.region[0]
        if start == self.info.lines_region[0]:
            start = start + re.search('\S', self.info.extracted).start()
        function_definition = self.info.source[start:self.info.region[1]]
        read = _VariableReadsAndWritesFinder.find_reads_for_one_liners(
            function_definition)
        return list(self.info_collector.prewritten.intersection(read))

    def _find_function_returns(self):
        if self.info.one_line:
            return []
        return list(self.info_collector.written.intersection(self.info_collector.postread))

    def _get_unindented_function_body(self, returns):
        if self.info.one_line:
            return 'return ' + _join_lines(self.info.extracted)
        extracted_body = self.info.extracted
        unindented_body = sourceutils.indent_lines(
            extracted_body, -sourceutils.find_minimum_indents(extracted_body))
        if returns:
            unindented_body += '\nreturn %s' % self._get_comma_form(returns)
        return unindented_body


class _ExtractVariableParts(object):

    def __init__(self, info):
        self.info = info

    def get_before_line(self):
        result = ' ' * self.info.indents + \
                 self.info.new_name + ' = ' + \
                 _join_lines(self.info.extracted) + '\n'
        return result

    def get_call(self):
        return self.info.new_name

    def get_after_scope(self):
        return ''


class _FunctionInformationCollector(object):

    def __init__(self, start, end, is_global):
        self.start = start
        self.end = end
        self.is_global = is_global
        self.prewritten = set()
        self.written = set()
        self.read = set()
        self.postread = set()
        self.postwritten = set()
        self.host_function = True

    def _read_variable(self, name, lineno):
        if self.start <= lineno <= self.end:
            if name not in self.written:
                self.read.add(name)
        if self.end < lineno:
            if name not in self.postwritten:
                self.postread.add(name)

    def _written_variable(self, name, lineno):
        if self.start <= lineno <= self.end:
            self.written.add(name)
        if self.start > lineno:
            self.prewritten.add(name)
        if self.end < lineno:
            self.postwritten.add(name)

    def visitFunction(self, node):
        if not self.is_global and self.host_function:
            self.host_function = False
            for name in node.argnames:
                self._written_variable(name, node.lineno)
            compiler.walk(node.code, self)
        else:
            self._written_variable(node.name, node.lineno)
            visitor = _VariableReadsAndWritesFinder()
            compiler.walk(node.code, visitor)
            for name in visitor.read - visitor.written:
                self._read_variable(name, node.lineno)

    def visitAssName(self, node):
        self._written_variable(node.name, node.lineno)

    def visitAssign(self, node):
        compiler.walk(node.expr, self)
        for child in node.nodes:
            compiler.walk(child, self)

    def visitName(self, node):
        self._read_variable(node.name, node.lineno)

    def visitClass(self, node):
        self._written_variable(node.name, node.lineno)


class _VariableReadsAndWritesFinder(object):

    def __init__(self):
        self.written = set()
        self.read = set()

    def visitAssName(self, node):
        self.written.add(node.name)

    def visitName(self, node):
        if node.name not in self.written:
            self.read.add(node.name)

    def visitFunction(self, node):
        self.written.add(node.name)
        visitor = _VariableReadsAndWritesFinder()
        compiler.walk(node.code, visitor)
        self.read.update(visitor.read - visitor.written)

    def visitClass(self, node):
        self.written.add(node.name)

    @staticmethod
    def find_reads_and_writes(code):
        if code.strip() == '':
            return set(), set()
        min_indents = sourceutils.find_minimum_indents(code)
        indented_code = sourceutils.indent_lines(code, -min_indents)
        if isinstance(indented_body, unicode):
            indented_body = indented_body.encode('utf-8')
        ast = _parse_text(indented_code)
        visitor = _VariableReadsAndWritesFinder()
        compiler.walk(ast, visitor)
        return visitor.read, visitor.written

    @staticmethod
    def find_reads_for_one_liners(code):
        if code.strip() == '':
            return set(), set()
        ast = _parse_text(code)
        visitor = _VariableReadsAndWritesFinder()
        compiler.walk(ast, visitor)
        return visitor.read


class _ReturnOrYieldFinder(object):

    def __init__(self):
        self.returns = False
        self.loop_count = 0

    def check_loop(self):
        if self.loop_count < 1:
            self.error = True

    def visitReturn(self, node):
        self.returns = True

    def visitYield(self, node):
        self.returns = True

    def visitFunction(self, node):
        pass

    def visitClass(self, node):
        pass

    @staticmethod
    def does_it_return(code):
        if code.strip() == '':
            return False
        min_indents = sourceutils.find_minimum_indents(code)
        indented_code = sourceutils.indent_lines(code, -min_indents)
        ast = _parse_text(indented_code)
        visitor = _ReturnOrYieldFinder()
        compiler.walk(ast, visitor)
        return visitor.returns


class _UnmatchedBreakOrContinueFinder(object):

    def __init__(self):
        self.error = False
        self.loop_count = 0

    def visitFor(self, node):
        self.loop_encountered(node)

    def visitWhile(self, node):
        self.loop_encountered(node)

    def loop_encountered(self, node):
        self.loop_count += 1
        compiler.walk(node.body, self)
        self.loop_count -= 1
        if node.else_:
            compiler.walk(node.else_, self)

    def visitBreak(self, node):
        self.check_loop()

    def visitContinue(self, node):
        self.check_loop()

    def check_loop(self):
        if self.loop_count < 1:
            self.error = True

    def visitFunction(self, node):
        pass

    def visitClass(self, node):
        pass

    @staticmethod
    def has_errors(code):
        if code.strip() == '':
            return False
        min_indents = sourceutils.find_minimum_indents(code)
        indented_code = sourceutils.indent_lines(code, -min_indents)
        ast = _parse_text(indented_code)
        visitor = _UnmatchedBreakOrContinueFinder()
        compiler.walk(ast, visitor)
        return visitor.error


def _parse_text(body):
    if isinstance(body, unicode):
        body = body.encode('utf-8')
    ast = compiler.parse(body)
    return ast

def _join_lines(code):
    lines = []
    for line in code.splitlines():
        if line.endswith('\\'):
            lines.append(line[:-1].strip())
        else:
            lines.append(line.strip())
    return ' '.join(lines)
