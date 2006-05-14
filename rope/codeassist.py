import compiler

from rope.exceptions import RopeException


class RopeSyntaxError(RopeException):
    pass


class CompletionProposal(object):
    global_variable = 'global_variable'

    def __init__(self, completion, kind):
        self.completion = completion
        self.kind = kind


class _GlobalVisitor(object):
    
    def __init__(self, starting):
        self.starting = starting
        self.result = {}

    def visitAssName(self, node):
        if node.name.startswith(self.starting):
            self.result[node.name] = CompletionProposal(node.name, 'global_variable')

    def visitFunction(self, node):
        if node.name.startswith(self.starting):
            self.result[node.name] = CompletionProposal(node.name, 'function')
    
    def visitClass(self, node):
        if node.name.startswith(self.starting):
            self.result[node.name] = CompletionProposal(node.name, 'class')


class ICodeAssist(object):
    def complete_code(self, source, offset):
        pass


class NoAssist(ICodeAssist):
    def complete_code(self, source_code, offset):
        return []


class CodeAssist(ICodeAssist):
    def _find_starting(self, source_code, offset):
        starting = ''
        current_offset = offset - 1
        while current_offset >= 0 and (source_code[current_offset].isalnum() or
                                       source_code[current_offset] == '_'):
            starting = source_code[current_offset] + starting
            current_offset -= 1;
        return starting

    def _comment_current_line(self, source_code, offset):
        line_beginning = offset - 1
        while line_beginning >= 0 and source_code[line_beginning] != '\n':
            line_beginning -= 1
        line_ending = offset
        while line_ending < len(source_code) and source_code[line_ending] != '\n':
            line_ending += 1
        result = source_code
        if line_beginning != -1 and line_beginning < line_ending - 1:
            result = source_code[:line_beginning] + '#' + source_code[line_beginning + 2:]
        return result

    def complete_code(self, source_code, offset):
        if offset > len(source_code):
            return []
        starting = self._find_starting(source_code, offset)
        commented_source_code = self._comment_current_line(source_code, offset)
        result = {}
        try:
            code_ast = compiler.parse(commented_source_code)
        except SyntaxError, e:
            raise RopeSyntaxError(e)
        visitor = _GlobalVisitor(starting)
        compiler.walk(code_ast, visitor)
        result.update(visitor.result)
        return result.values()

