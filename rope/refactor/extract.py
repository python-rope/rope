import compiler

from rope.exceptions import RefactoringException

import rope.codeanalyze
import rope.pyobjects
from rope.refactor.change import (ChangeSet, ChangeFileContents,
                                  MoveResource, CreateFolder)


class ExtractMethodRefactoring(object):
    
    def __init__(self, pycore):
        self.pycore = pycore
    
    def extract_method(self, resource, start_offset, end_offset,
                       extracted_name):
        new_contents = _ExtractMethodPerformer(self, resource, start_offset,
                                              end_offset, extracted_name).extract()
        changes = ChangeSet()
        changes.add_change(ChangeFileContents(resource, new_contents))
        return changes
        

class _ExtractMethodPerformer(object):
    
    def __init__(self, refactoring, resource, start_offset,
                 end_offset, extracted_name):
        self.refactoring = refactoring
        source_code = resource.read()
        self.source_code = source_code
        self.extracted_name = extracted_name
        
        self.lines = rope.codeanalyze.SourceLinesAdapter(source_code)
        self.start_offset = self._choose_closest_line_end(source_code, start_offset)
        self.end_offset = self._choose_closest_line_end(source_code, end_offset)
        
        start_line = self.lines.get_line_number(start_offset)
        self.first_line_indents = self._get_indents(start_line)
        self.scope = self.refactoring.pycore.get_string_scope(source_code, resource)
        self.holding_scope = self.scope.get_inner_scope_for_line(start_line)
        if self.holding_scope.pyobject.get_type() != \
           rope.pyobjects.PyObject.get_base_type('Module') and \
           self.holding_scope.get_start()  == start_line:
            self.holding_scope = self.holding_scope.parent
        self.scope_start = self.lines.get_line_start(self.holding_scope.get_start())
        self.scope_end = self.lines.get_line_end(self.holding_scope.get_end()) + 1

        self.is_method = self.holding_scope.parent is not None and \
                         self.holding_scope.parent.pyobject.get_type() == \
                         rope.pyobjects.PyObject.get_base_type('Type')
        self.is_global = self.holding_scope.pyobject.get_type() == \
                         rope.pyobjects.PyObject.get_base_type('Module')
        self.scope_indents = self._get_indents(self.holding_scope.get_start()) + 4
        if self.is_global:
            self.scope_indents = 0
        self._check_exceptional_conditions()
    
    def _check_exceptional_conditions(self):
        if self.holding_scope.pyobject.get_type() == rope.pyobjects.PyObject.get_base_type('Type'):
            raise RefactoringException('Can not extract methods in class body')
        if self.end_offset > self.scope_end:
            raise RefactoringException('Bad range selected for extract method')
        end_line = self.lines.get_line_number(self.end_offset - 1)
        end_scope = self.scope.get_inner_scope_for_line(end_line)
        if end_scope != self.holding_scope and end_scope.get_end() != end_line:
            raise RefactoringException('Bad range selected for extract method')
        if _ReturnFinder.does_it_return(self.source_code[self.start_offset:self.end_offset]):
            raise RefactoringException('Extracted piece should not contain return statements')
        
    def extract(self):
        args = self._find_function_arguments()
        returns = self._find_function_returns()
        
        result = []
        result.append(self.source_code[:self.start_offset])
        if self.is_global:
            result.append('\n%s\n' % self._get_function_definition())
        call_prefix = ''
        if returns:
            call_prefix = self._get_comma_form(returns) + ' = '
        result.append(' ' * self.first_line_indents + call_prefix
                      + self._get_function_call(args) + '\n')
        result.append(self.source_code[self.end_offset:self.scope_end])
        if not self.is_global:
            result.append('\n%s' % self._get_function_definition())
        result.append(self.source_code[self.scope_end:])
        return ''.join(result)
    
    def _get_function_definition(self):
        args = self._find_function_arguments()
        returns = self._find_function_returns()
        if not self.is_global:
            function_indents = self.scope_indents
        else:
            function_indents = 4
        result = []
        result.append('%sdef %s:\n' %
                      (' ' * self._get_indents(self.holding_scope.get_start()),
                       self._get_function_signature(args)))
        extracted_body = self.source_code[self.start_offset:self.end_offset]
        unindented_body = _indent_lines(extracted_body, -_find_minimum_indents(extracted_body))
        function_body = _indent_lines(unindented_body, function_indents)
        result.append(function_body)
        if returns:
            result.append(' ' * function_indents +
                          'return %s\n' % self._get_comma_form(returns))
        return ''.join(result)
    
    def _get_function_signature(self, args):
        args = list(args)
        if self.is_method:
            if 'self' in args:
                args.remove('self')
            args.insert(0, 'self')
        return self.extracted_name + '(%s)' % self._get_comma_form(args)
    
    def _get_function_call(self, args):
        prefix = ''
        if self.is_method:
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
    
    def _find_function_arguments(self):
        start1 = self.lines.get_line_start(self.holding_scope.get_start() + 1)
        code1 = self.source_code[start1:self.start_offset] + \
                '%spass' % (' ' * self.first_line_indents)
        read1, written1 = _VariableReadsAndWritesFinder.find_reads_and_writes(code1)
        if self.holding_scope.pyobject.get_type() == rope.pyobjects.PyObject.get_base_type('Function'):
            written1.update(self._get_function_arg_names())
        
        code2 = self.source_code[self.start_offset:self.end_offset]
        read2, written2 = _VariableReadsAndWritesFinder.find_reads_and_writes(code2)
        return list(written1.intersection(read2))
    
    def _get_function_arg_names(self):
        indents = self._get_indents(self.holding_scope.get_start())
        function_header_end = min(self.source_code.index('):\n', self.scope_start) + 1,
                                  self.scope_end)
        function_header = _indent_lines(self.source_code[self.scope_start:
                                                              function_header_end], -indents) + \
                                                              ':\n' + ' ' * 4 + 'pass'
        ast = compiler.parse(function_header)
        visitor = _FunctionArgnamesCollector()
        compiler.walk(ast, visitor)
        return visitor.argnames
        
    
    def _find_function_returns(self):
        code2 = self.source_code[self.start_offset:self.end_offset]
        read2, written2 = _VariableReadsAndWritesFinder.find_reads_and_writes(code2)
        code3 = self.source_code[self.end_offset:self.scope_end]
        read3, written3 = _VariableReadsAndWritesFinder.find_reads_and_writes(code3)
        return list(written2.intersection(read3))
        
    def _choose_closest_line_end(self, source_code, offset):
        lineno = self.lines.get_line_number(offset)
        line_start = self.lines.get_line_start(lineno)
        line_end = self.lines.get_line_end(lineno)
        if source_code[line_start:offset].strip() == '':
            return line_start
        return line_end + 1
    
    def _get_indents(self, lineno):
        indents = 0
        for c in self.lines.get_line(lineno):
            if c == ' ':
                indents += 1
            else:
                break
        return indents
    
def _find_minimum_indents(source_code):
    result = 80
    lines = source_code.split('\n')
    for line in lines:
        if line.strip() == '':
            continue
        indents = 0
        for c in line:
            if c == ' ':
                indents += 1
            else:
                break
        result = min(result, indents)
    return result

def _indent_lines(source_code, amount):
    if amount == 0:
        return source_code
    lines = source_code.split('\n')
    result = []
    for l in lines:
        if amount < 0 and len(l) > -amount:
            indents = 0
            while indents < len(l) and l[indents] == ' ':
                indents += 1
            result.append(l[-min(amount, indents):])
        elif amount > 0 and l.strip() != '':
            result.append(' ' * amount + l)
        else:
            result.append('')
    return '\n'.join(result)
    

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
        min_indents = _find_minimum_indents(code)
        indented_code = _indent_lines(code, -min_indents)
        ast = compiler.parse(indented_code)
        visitor = _VariableReadsAndWritesFinder()
        compiler.walk(ast, visitor)
        return visitor.read, visitor.written


class _ReturnFinder(object):
    
    def __init__(self):
        self.returns = False

    def visitReturn(self, node):
        self.returns = True

    def visitFunction(self, node):
        pass
    
    def visitClass(self, node):
        pass
    
    @staticmethod
    def does_it_return(code):
        if code.strip() == '':
            return False
        min_indents = _find_minimum_indents(code)
        indented_code = _indent_lines(code, -min_indents)
        ast = compiler.parse(indented_code)
        visitor = _ReturnFinder()
        compiler.walk(ast, visitor)
        return visitor.returns


class _FunctionArgnamesCollector(object):
    
    def __init__(self):
        self.argnames = []
    
    def visitFunction(self, node):
        self.argnames = node.argnames
