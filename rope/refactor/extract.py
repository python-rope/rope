import compiler

import rope.base.pyobjects
from rope.base import codeanalyze
from rope.base.exceptions import RefactoringException
from rope.refactor import sourceutils
from rope.refactor.change import ChangeSet, ChangeContents


class _ExtractRefactoring(object):
    
    def __init__(self, pycore, resource, start_offset, end_offset):
        self.pycore = pycore
        self.resource = resource
        self.start_offset = start_offset
        self.end_offset = end_offset
    
class ExtractMethodRefactoring(_ExtractRefactoring):
    
    def get_changes(self, extracted_name):
        info = _ExtractInformation(self.pycore, self.resource,
                                   self.start_offset, self.end_offset)
        if info.is_one_line_extract():
            new_contents = _OneLineExtractPerformer(self.pycore, self.resource, info,
                                                    extracted_name).extract()
        else:
            new_contents = _MultiLineExtractPerformer(self.pycore, self.resource, info,
                                                      extracted_name).extract()
        changes = ChangeSet()
        changes.add_change(ChangeContents(self.resource, new_contents))
        return changes


class ExtractVariableRefactoring(_ExtractRefactoring):
    
    def get_changes(self, extracted_name):
        info = _ExtractInformation(self.pycore, self.resource,
                                   self.start_offset, self.end_offset)
        new_contents = _OneLineExtractPerformer(self.pycore, self.resource, info, 
                                                extracted_name, True).extract()
        changes = ChangeSet()
        changes.add_change(ChangeContents(self.resource, new_contents))
        return changes


class _ExtractInformation(object):
    
    def __init__(self, pycore, resource, start_offset, end_offset):
        self.source_code = source_code = resource.read()
        
        pymodule = pycore.resource_to_pyobject(resource)
        self.lines = pymodule.lines
        self.line_finder = codeanalyze.LogicalLineFinder(self.lines)
        
        self.region = (self._choose_closest_line_end(start_offset),
                       self._choose_closest_line_end(end_offset, end=True))
        
        self.region_linenos = (
            self.line_finder.get_logical_line_in(self.lines.get_line_number(self.region[0]))[0],
            self.line_finder.get_logical_line_in(self.lines.get_line_number(self.region[1]))[1])

        self.region_lines = (self.lines.get_line_start(self.region_linenos[0]),
                             self.lines.get_line_end(self.region_linenos[1]))
        
        holding_scope = self._find_holding_scope(pymodule.get_scope(), self.region_linenos[0])
        self.scope = (self.lines.get_line_start(holding_scope.get_start()),
                      self.lines.get_line_end(holding_scope.get_end()) + 1)
        
    def _find_holding_scope(self, scope, start_line):
        holding_scope = scope.get_inner_scope_for_line(start_line)
        if holding_scope.get_kind() != 'Module' and \
           holding_scope.get_start() == start_line:
            holding_scope = holding_scope.parent
        return holding_scope
    
    def _choose_closest_line_end(self, offset, end=False):
        lineno = self.lines.get_line_number(offset)
        line_start = self.lines.get_line_start(lineno)
        line_end = self.lines.get_line_end(lineno)
        if self.source_code[line_start:offset].strip() == '':
            if end:
                return line_start - 1
            else:
                return line_start
        elif self.source_code[offset:line_end].strip() == '':
            return min(line_end, len(self.source_code))
        return offset
    
    def is_one_line_extract(self):
        return self.region != self.region_lines and \
               (self.line_finder.get_logical_line_in(self.region_linenos[0]) == 
                self.line_finder.get_logical_line_in(self.region_linenos[1]))


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
    
    The parts marked as before_line, call and after_scope are
    used in refactoring and we use `ExtractInfo` to find the
    new contents of these parts.

    """
    
    def __init__(self, pycore, resource, info, extracted_name, extract_variable=False):
        self.source_code = source_code = resource.read()
        self.extracted_name = extracted_name
        self.extract_variable = extract_variable
        self.info = info
        
        self.lines = info.lines
        
        self.first_line_indents = self._get_indents(self.info.region_linenos[0])
        self.scope = pycore.get_string_scope(source_code, resource)
        self.holding_scope = self._find_holding_scope(self.info.region_linenos[0])
        
        self.extract_info = self._create_extract_info()
        
        self._check_exceptional_conditions()
        self.info_collector = self._create_info_collector()
    
    def _create_extract_info(self):
        if self.extract_variable:
            return _ExtractedVariablePieces(self)
        else:
            return _ExtractedPieces(self)

    def _find_holding_scope(self, start_line):
        holding_scope = self.scope.get_inner_scope_for_line(start_line)
        if holding_scope.get_kind() != 'Module' and \
           holding_scope.get_start() == start_line:
            holding_scope = holding_scope.parent
        return holding_scope
    
    def _is_global(self):
        return self.holding_scope.pyobject.get_type() == \
               rope.base.pyobjects.PyObject.get_base_type('Module')

    def _is_method(self):
        return self.holding_scope.parent is not None and \
               self.holding_scope.parent.pyobject.get_type() == \
               rope.base.pyobjects.PyObject.get_base_type('Type')
    
    def _check_exceptional_conditions(self):
        if self.holding_scope.pyobject.get_type() == rope.base.pyobjects.PyObject.get_base_type('Type'):
            raise RefactoringException('Can not extract methods in class body')
        if self.info.region[1] > self.info.scope[1]:
            raise RefactoringException('Bad range selected for extract method')
        end_line = self.info.region_linenos[1]
        end_scope = self.scope.get_inner_scope_for_line(end_line)
        if end_scope != self.holding_scope and end_scope.get_end() != end_line:
            raise RefactoringException('Bad range selected for extract method')
        try:
            if _ReturnOrYieldFinder.does_it_return(
                self.source_code[self.info.region[0]:self.info.region[1]]):
                raise RefactoringException('Extracted piece should not contain return statements')
        except SyntaxError:
            raise RefactoringException('Extracted piece should contain complete statements.')

    def _is_on_a_word(self, offset):
        prev = self.source_code[offset]
        next = self.source_code[offset + 1]
        return (prev.isalnum() or prev == '_') and (next.isalnum() or next == '_')

    def _create_info_collector(self):
        zero = self.holding_scope.get_start() - 1
        start_line = self.info.region_linenos[0] - zero
        end_line = self.info.region_linenos[1] - zero
        info_collector = _FunctionInformationCollector(start_line, end_line,
                                                       self._is_global())
        indented_body = self.source_code[self.info.scope[0]:self.info.scope[1]]
        body = sourceutils.indent_lines(indented_body,
                                        -sourceutils.find_minimum_indents(indented_body))
        ast = _parse_text(body)
        compiler.walk(ast, info_collector)
        return info_collector

    def extract(self):
        result = []
        result.append(self.source_code[:self.info.region_lines[0]])
        result.append(self.extract_info.get_before_line())
        result.append(self.source_code[self.info.region_lines[0]:self.info.region[0]])
        result.append(self.extract_info.get_call())
        result.append(self.source_code[self.info.region[1]:self.info.region_lines[1]])
        result.append(self.source_code[self.info.region_lines[1]:self.info.scope[1]])
        result.append(self.extract_info.get_after_scope())
        result.append(self.source_code[self.info.scope[1]:])
        return ''.join(result)

    def _get_scope_indents(self):
        if self._is_global():
            return 0
        else:
            return self._get_indents(self.holding_scope.get_start()) + 4
    
    def _get_function_indents(self):
        if self._is_global():
            return 4
        else:
            return self._get_scope_indents()
    
    def _get_function_definition(self):
        args = self._find_function_arguments()
        returns = self._find_function_returns()
        function_indents = self._get_function_indents()
        result = []
        result.append('%sdef %s:\n' %
                      (' ' * self._get_indents(self.holding_scope.get_start()),
                       self._get_function_signature(args)))
        unindented_body = self._get_unindented_function_body(returns)
        function_body = sourceutils.indent_lines(unindented_body, function_indents)
        result.append(function_body)
        definition = ''.join(result)
        
        return definition + '\n'

    def _get_one_line_definition(self):
        extracted_body = self.source_code[self.info.region[0]:self.info.region[1]]
        lines = []
        for line in extracted_body.splitlines():
            if line.endswith('\\'):
                lines.append(line[:-1].strip())
            else:
                lines.append(line.strip())
        return ' '.join(lines)
    
    def _get_function_signature(self, args):
        args = list(args)
        if self._is_method():
            if 'self' in args:
                args.remove('self')
            args.insert(0, 'self')
        return self.extracted_name + '(%s)' % self._get_comma_form(args)
    
    def _get_function_call(self, args):
        prefix = ''
        if self._is_method():
            if  'self' in args:
                args.remove('self')
            prefix = 'self.'
        return prefix + '%s(%s)' % (self.extracted_name, self._get_comma_form(args))

    def _get_comma_form(self, names):
        result = ''
        if names:
            result += names[0]
            for name in names[1:]:
                result += ', ' + name
        return result
    
    def _get_indents(self, lineno):
        return sourceutils.get_indents(self.lines, lineno)


class _OneLineExtractPerformer(_ExtractPerformer):
    
    def __init__(self, *args, **kwds):
        super(_OneLineExtractPerformer, self).__init__(*args, **kwds)

    def _check_exceptional_conditions(self):
        super(_OneLineExtractPerformer, self)._check_exceptional_conditions()
        if (self.info.region[0] > 0 and self._is_on_a_word(self.info.region[0] - 1)) or \
           (self.info.region[1] < len(self.source_code) and self._is_on_a_word(self.info.region[1] - 1)):
            raise RefactoringException('Should extract complete statements.')
        if self.extract_variable and not self.info.is_one_line_extract():
            raise RefactoringException('Extract variable should not span multiple lines.')
    
    def _get_call(self, returns, args):
        return self._get_function_call(args)

    def _find_function_arguments(self):
        function_definition = self.source_code[self.info.region[0]:self.info.region[1]]
        read = _VariableReadsAndWritesFinder.find_reads_for_one_liners(
            function_definition)
        return list(self.info_collector.prewritten.intersection(read))
    
    def _find_function_returns(self):
        return []
        
    def _get_unindented_function_body(self, returns):
        return 'return ' + self._get_one_line_definition()
    

class _MultiLineExtractPerformer(_ExtractPerformer):
    
    def __init__(self, *args, **kwds):
        super(_MultiLineExtractPerformer, self).__init__(*args, **kwds)

    def _check_exceptional_conditions(self):
        super(_MultiLineExtractPerformer, self)._check_exceptional_conditions()
        if self.info.region[0] != self.info.region_lines[0] or \
           self.info.region[1] != self.info.region_lines[1]:
            raise RefactoringException('Extracted piece should contain complete statements.')
    
    def _get_call(self, returns, args):
        call_prefix = ''
        if returns:
            call_prefix = self._get_comma_form(returns) + ' = '
        return ' ' * self.first_line_indents + call_prefix + \
               self._get_function_call(args)

    def _find_function_arguments(self):
        return list(self.info_collector.prewritten.intersection(self.info_collector.read))
    
    def _find_function_returns(self):
        return list(self.info_collector.written.intersection(self.info_collector.postread))
        
    def _get_unindented_function_body(self, returns):
        extracted_body = self.source_code[self.info.region[0]:self.info.region[1]]
        unindented_body = sourceutils.indent_lines(
            extracted_body, -sourceutils.find_minimum_indents(extracted_body))
        if returns:
            unindented_body += '\nreturn %s' % self._get_comma_form(returns)
        return unindented_body
    

class _ExtractedPieces(object):
    
    def __init__(self, performer):
        self.performer = performer
    
    def get_before_line(self):
        if self.performer._is_global():
            return '\n%s\n' % self.performer._get_function_definition()
        return ''
    
    def get_call(self):
        args = self.performer._find_function_arguments()
        returns = self.performer._find_function_returns()
        return self.performer._get_call(returns, args)
    
    def get_after_scope(self):
        if not self.performer._is_global():
            return '\n%s' % self.performer._get_function_definition()
        return ''


class _ExtractedVariablePieces(object):
    
    def __init__(self, performer):
        self.performer = performer
    
    def get_before_line(self):
        result = ' ' * self.performer.first_line_indents + \
                 self.performer.extracted_name + ' = ' + \
                 self.performer._get_one_line_definition() + '\n'
        return result
    
    def get_call(self):
        return self.performer.extracted_name
    
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
        self.host_function = True
    
    def _read_variable(self, name, lineno):
        if self.start <= lineno <= self.end:
            self.read.add(name)
        if self.end < lineno:
            self.postread.add(name)
    
    def _written_variable(self, name, lineno):
        if self.start <= lineno <= self.end:
            self.written.add(name)
        if self.start > lineno:
            self.prewritten.add(name)
        
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

def _parse_text(body):
    if isinstance(body, unicode):
        body = body.encode('utf-8')
    ast = compiler.parse(body)
    return ast

