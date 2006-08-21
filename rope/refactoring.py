import compiler
import re

import rope.codeanalyze


class Refactoring(object):

    def local_rename(self, source_code, offset, new_name):
        """Returns the changed source_code or ``None`` if nothing has been changed"""
    
    def rename(self, resource, offset, new_name):
        pass
    
    def extract_method(self, source_code, start_offset, end_offset, extracted_name):
        pass
    
    def undo_last_refactoring(self):
        pass


class PythonRefactoring(Refactoring):

    def __init__(self, pycore):
        self.pycore = pycore
        self.comment_pattern = PythonRefactoring.any("comment", [r"#[^\n]*"])
        sqstring = r"(\b[rR])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
        dqstring = r'(\b[rR])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
        sq3string = r"(\b[rR])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?"
        dq3string = r'(\b[rR])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?'
        self.string_pattern = PythonRefactoring.any("string",
                                                    [sq3string, dq3string, sqstring, dqstring])
        self.last_changes = ChangeSet()

    @staticmethod
    def any(name, list):
        return "(?P<%s>" % name + "|".join(list) + ")"

    def local_rename(self, source_code, offset, new_name):
        result = []
        module_scope = self.pycore.get_string_scope(source_code)
        word_finder = rope.codeanalyze.WordRangeFinder(source_code)
        old_name = word_finder.get_primary_at(offset).split('.')[-1]
        pyname_finder = rope.codeanalyze.ScopeNameFinder(source_code, module_scope)
        old_pyname = pyname_finder.get_pyname_at(offset)
        if old_pyname is None:
            return None
        pattern = self._get_occurance_pattern(old_name)
        def scope_retriever():
            return module_scope
        return self._rename_occurance_in_file(source_code, scope_retriever, old_pyname,
                                              pattern, new_name)
    
    def rename(self, resource, offset, new_name):
        module_scope = self.pycore.resource_to_pyobject(resource).get_scope()
        source_code = resource.read()
        word_finder = rope.codeanalyze.WordRangeFinder(source_code)
        old_name = word_finder.get_primary_at(offset).split('.')[-1]
        pyname_finder = rope.codeanalyze.ScopeNameFinder(source_code, module_scope)
        old_pyname = pyname_finder.get_pyname_at(offset)
        if old_pyname is None:
            return None
        pattern = self._get_occurance_pattern(old_name)
        changes = ChangeSet()
        for file_ in self.pycore.get_python_files():
            def scope_retriever():
                return self.pycore.resource_to_pyobject(file_).get_scope()
            new_content = self._rename_occurance_in_file(file_.read(), scope_retriever, 
                                                         old_pyname, pattern, new_name)
            if new_content is not None:
                changes.add_change(ChangeFileContents(file_, new_content))
        if old_pyname.get_object().get_type() == rope.pycore.PyObject.get_base_type('Module'):
            changes.add_change(self._rename_module(old_pyname.get_object(), new_name))
        changes.do()
        self.last_changes = changes
    
    def _rename_module(self, pyobject, new_name):
        resource = pyobject.get_resource()
        if not resource.is_folder():
            new_name = new_name + '.py'
        parent_path = resource.get_parent().get_path()
        if parent_path == '':
            new_location = new_name
        else:
            new_location = parent_path + '/' + new_name
        return MoveResource(resource, new_location)
    
    def _rename_occurance_in_file(self, source_code, scope_retriever, old_pyname,
                                  pattern, new_name):
        result = []
        last_modified_char = 0
        pyname_finder = None
        for match in pattern.finditer(source_code):
            for key, value in match.groupdict().items():
                if value and key == "occurance":
                    match_start = match.start(key)
                    match_end = match.end(key)
                    if pyname_finder == None:
                        module_scope = scope_retriever()
                        pyname_finder = rope.codeanalyze.ScopeNameFinder(source_code, module_scope)
                    new_pyname = pyname_finder.get_pyname_at(match_start + 1)
                    if self._are_pynames_the_same(old_pyname, new_pyname):
                        result.append(source_code[last_modified_char:match_start] + new_name)
                        last_modified_char = match_end
        if last_modified_char != 0:
            result.append(source_code[last_modified_char:])
            return ''.join(result)
        return None
    
    def _are_pynames_the_same(self, pyname1, pyname2):
        return pyname1 == pyname2 or \
               (pyname1 is not None and pyname2 is not None and 
                pyname1.get_object() == pyname2.get_object() and
                pyname1.get_definition_location() == pyname2.get_definition_location())
    
    def _get_occurance_pattern(self, name):
        occurance_pattern = PythonRefactoring.any('occurance', ['\\b' + name + '\\b'])
        pattern = re.compile(occurance_pattern + "|" + \
                             self.comment_pattern + "|" + self.string_pattern)
        return pattern

    def _get_scope_range(self, source_code, offset, module_scope, lineno):
        lines = rope.codeanalyze.SourceLinesAdapter(source_code)
        holding_scope = module_scope.get_inner_scope_for_line(lineno)
        start = lines.get_line_start(holding_scope.get_start())
        end = lines.get_line_end(holding_scope.get_end()) + 1
        return (start, end)

    def extract_method(self, source_code, start_offset, end_offset, extracted_name):
        return _ExtractMethodPerformer(self, source_code, start_offset,
                                       end_offset, extracted_name).extract()
    
    def undo_last_refactoring(self):
        self.last_changes.undo()

class _ExtractMethodPerformer(object):
    
    def __init__(self, refactoring, source_code, start_offset, end_offset, extracted_name):
        self.refactoring = refactoring
        self.source_code = source_code
        self.extracted_name = extracted_name
        scope = self.refactoring.pycore.get_string_scope(source_code)
        self.lines = rope.codeanalyze.SourceLinesAdapter(source_code)
        self.start_offset = self._choose_closest_line_end(source_code, start_offset)
        self.end_offset = self._choose_closest_line_end(source_code, end_offset)
        start_line = self.lines.get_line_number(start_offset)
        self.holding_scope = scope.get_inner_scope_for_line(start_line)
        self.scope_start = self.lines.get_line_start(self.holding_scope.get_start())
        self.scope_end = self.lines.get_line_end(self.holding_scope.get_end()) + 1
        self.scope_indents = self._get_indents(self.holding_scope.get_start() + 1)
        
    def extract(self):
        args = self._find_function_arguments()
        returns = self._find_function_returns()
        method_signature = self._get_method_signature(args)
        result = []
        result.append(self.source_code[:self.start_offset])
        call_prefix = ''
        if returns:
            call_prefix = self._get_comma_form(returns) + ' = '
        result.append(' ' * self.scope_indents + call_prefix + method_signature + '\n')
        result.append(self.source_code[self.end_offset:self.scope_end])
        result.append('\ndef %s:\n' % method_signature)
        result.append(self.source_code[self.start_offset:self.end_offset])
        if returns:
            result.append(' ' * self.scope_indents + 'return %s\n' % self._get_comma_form(returns))
        result.append(self.source_code[self.scope_end:])
        return ''.join(result)
    
    def _get_method_signature(self, args):
        return self.extracted_name + '(%s)' % self._get_comma_form(args)
    
    def _get_comma_form(self, names):
        result = ''
        if names:
            result += names[0]
            for name in names[1:]:
                result += ', ' + name
        return result        
    
    def _find_function_arguments(self):
        start1 = self.lines.get_line_start(self.holding_scope.get_start() + 1)
        code1 = self._deindent_lines(self.source_code[start1:
                                                      self.start_offset],
                                     self.scope_indents)
        ast1 = compiler.parse(code1)
        visitor1 = _VariableReadsAndWritesFinder()
        compiler.walk(ast1, visitor1)
        
        code2 = self._deindent_lines(self.source_code[self.start_offset:
                                                      self.end_offset],
                                     self.scope_indents)
        ast2 = compiler.parse(code2)
        visitor2 = _VariableReadsAndWritesFinder()
        compiler.walk(ast2, visitor2)
        return list(visitor1.written.intersection(visitor2.read))
    
    def _find_function_returns(self):
        code2 = self._deindent_lines(self.source_code[self.start_offset:
                                                      self.end_offset],
                                     self.scope_indents)
        ast2 = compiler.parse(code2)
        visitor2 = _VariableReadsAndWritesFinder()
        compiler.walk(ast2, visitor2)
        
        code3 = self._deindent_lines(self.source_code[self.end_offset:
                                                      self.scope_end],
                                     self.scope_indents)
        ast3 = compiler.parse(code3)
        visitor3 = _VariableReadsAndWritesFinder()
        compiler.walk(ast3, visitor3)
        
        return list(visitor2.written.intersection(visitor3.read))
        
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
    
    def _deindent_lines(self, source_code, amount):
        lines = source_code.split('\n')
        result = []
        for l in lines:
            if len(l) > amount:
                result.append(l[amount:])
        return '\n'.join(result)
    

class _VariableReadsAndWritesFinder(object):
    
    def __init__(self):
        self.written = set()
        self.read = set()
    
    def visitAssName(self, node):
        self.written.add(node.name)
    
    def visitName(self, node):
        self.read.add(node.name)


class NoRefactoring(Refactoring):
    pass


class Change(object):
    
    def do(self):
        pass
    
    def undo(self):
        pass


class ChangeSet(Change):
    
    def __init__(self):
        self.changes = []
    
    def do(self):
        try:
            done = []
            for change in self.changes:
                change.do()
                done.append(change)
        except Exception:
            for change in done:
                change.undo()
            raise
    
    def undo(self):
        try:
            done = []
            for change in self.changes:
                change.undo()
                done.append(change)
        except Exception:
            for change in done:
                change.do()
            raise
    
    def add_change(self, change):
        self.changes.append(change)


class ChangeFileContents(Change):
    
    def __init__(self, resource, new_content):
        self.resource = resource
        self.new_content = new_content
        self.old_content = None

    def do(self):
        self.old_content = self.resource.read()
        self.resource.write(self.new_content)
    
    def undo(self):
        self.resource.write(self.old_content)


class MoveResource(Change):
    
    def __init__(self, resource, new_location):
        self.resource = resource
        self.new_location = new_location
        self.old_location = None
    
    def do(self):
        self.old_location = self.resource.get_path()
        self.resource.move(self.new_location)
    
    def undo(self):
        self.resource.move(self.old_location)
        

