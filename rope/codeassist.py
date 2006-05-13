import compiler

class CompletionProposal(object):
    global_variable = 'global_variable'

    def __init__(self, completion, kind):
        self.completion = completion
        self.kind = kind


class _GlobalVisitor(object):
    
    def __init__(self, starting):
        self.starting = starting
        self.result = []

    def visitAssName(self, node):
        if node.name.startswith(self.starting):
            self.result.append(CompletionProposal(node.name, 'global_variable'))


class ICodeAssist(object):
    def complete_code(self, source, offset):
        pass


class NoAssist(ICodeAssist):
    def complete_code(self, source_code, offset):
        return []


class CodeAssist(ICodeAssist):
    def complete_code(self, source_code, offset):
        if offset > len(source_code):
            return []
        starting = ''
        current_offset = offset - 1
        while current_offset >= 0 and (source_code[current_offset].isalnum() or
                                       source_code[current_offset] == '_'):
            starting = source_code[current_offset] + starting
            current_offset -= 1;
        result = []
        code_ast = compiler.parse(source_code)
        visitor = _GlobalVisitor(starting)
        compiler.walk(code_ast, visitor)
        result.extend(visitor.result)
        return result
