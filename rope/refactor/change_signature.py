import copy

import rope.refactor.occurrences
import rope.base.exceptions
import rope.base.pyobjects
from rope.base import codeanalyze
from rope.refactor import sourceutils, functionutils
from rope.refactor.change import ChangeContents, ChangeSet


class ChangeSignature(object):
    
    def __init__(self, pycore, resource, offset):
        self.pycore = pycore
        self.resource = resource
        self.offset = offset
        self.name = codeanalyze.get_name_at(resource, offset)
        self.pyname = codeanalyze.get_pyname_at(pycore, resource, offset)
        if self.pyname is None or self.pyname.get_object() is None or \
           not isinstance(self.pyname.get_object(), rope.base.pyobjects.PyFunction):
            raise rope.base.exceptions.RefactoringException(
                'Change method signature should be performed on functions')
    
    def _change_calls(self, call_changer):
        changes = ChangeSet()
        finder = rope.refactor.occurrences.FilteredOccurrenceFinder(
            self.pycore, self.name, [self.pyname])
        for file in self.pycore.get_python_files():
            change_calls = _ChangeCallsInModule(
                self.pycore, finder, file, call_changer)
            changed_file = change_calls.get_changed_module()
            if changed_file is not None:
                changes.add_change(ChangeContents(file, changed_file))
        return changes
    
    def get_definition_info(self):
        pymodule, line = self.pyname.get_definition_location()
        line_start = pymodule.lines.get_line_start(line)
        line_end = pymodule.lines.get_line_end(line)
        start = pymodule.source_code.find('def', line_start) + 4
        return functionutils._DefinitionInfo.read(self.pyname.get_object(),
                                                  pymodule.source_code[start:line_end])
    
    def normalize(self):
        changer = _FunctionChangers(self.pyname.get_object(), self.get_definition_info(),
                                    [ArgumentNormalizer()])
        return self._change_calls(changer)
    
    def remove(self, index):
        changer = _FunctionChangers(self.pyname.get_object(), self.get_definition_info(),
                                    [ArgumentRemover(index)])
        return self._change_calls(changer)

    def add(self, index, name, default=None, value=None):
        changer = _FunctionChangers(self.pyname.get_object(), self.get_definition_info(),
                                    [ArgumentAdder(index, name, default, value)])
        return self._change_calls(changer)

    def inline_default(self, index):
        changer = _FunctionChangers(self.pyname.get_object(), self.get_definition_info(),
                                    [ArgumentDefaultInliner(index)])
        return self._change_calls(changer)

    def reorder(self, new_ordering):
        changer = _FunctionChangers(self.pyname.get_object(), self.get_definition_info(),
                                    [ArgumentReorderer(new_ordering)])
        return self._change_calls(changer)

    def apply_changers(self, changers):
        function_changer = _FunctionChangers(
            self.pyname.get_object(), self.get_definition_info(), changers)
        return self._change_calls(function_changer)


class _FunctionChangers(object):
    
    def __init__(self, pyfunction, definition_info, changers=None):
        self.pyfunction = pyfunction
        self.definition_info = definition_info
        self.changers = changers
        self.changed_definition_infos = self._get_changed_definition_infos()
    
    def _get_changed_definition_infos(self):
        result = []
        definition_info = self.definition_info
        result.append(definition_info)
        for changer in self.changers:
            definition_info = copy.deepcopy(definition_info)
            changer.change_definition_info(definition_info)
            result.append(definition_info)
        return result
    
    def change_definition(self, call):
        return self.changed_definition_infos[-1].to_string()

    def change_call(self, call):
        call_info = functionutils._CallInfo.read(self.definition_info, call)
        mapping = functionutils._ArgumentMapping(self.definition_info, call_info)
        
        for definition_info, changer in zip(self.changed_definition_infos, self.changers):
            changer.change_argument_mapping(definition_info, mapping)
        
        return mapping.to_call_info(self.changed_definition_infos[-1]).to_string()
    

class _ArgumentChanger(object):
    
    def change_definition_info(self, definition_info):
        pass
    
    def change_argument_mapping(self, definition_info, argument_mapping):
        pass


class ArgumentNormalizer(_ArgumentChanger):
    pass    


class ArgumentRemover(_ArgumentChanger):
    
    def __init__(self, index):
        self.index = index
    
    def change_definition_info(self, call_info):
        if self.index < len(call_info.args_with_defaults):
            del call_info.args_with_defaults[self.index]
        elif self.index == len(call_info.args_with_defaults) and \
           call_info.args_arg is not None:
            call_info.args_arg = None
        elif (self.index == len(call_info.args_with_defaults) and
            call_info.args_arg is None and call_info.keywords_arg is not None) or \
           (self.index == len(call_info.args_with_defaults) + 1 and
            call_info.args_arg is not None and call_info.keywords_arg is not None):
            call_info.keywords_arg = None

    def change_argument_mapping(self, definition_info, mapping):
        if self.index < len(definition_info.args_with_defaults):
            name = definition_info.args_with_defaults[0]
            if name in mapping.param_dict:
                del mapping.param_dict[name]
    

class ArgumentAdder(_ArgumentChanger):
    
    def __init__(self, index, name, default=None, value=None):
        self.index = index
        self.name = name
        self.default = default
        self.value = value
    
    def change_definition_info(self, definition_info):
        for pair in definition_info.args_with_defaults:
            if pair[0] == self.name:
                raise rope.base.exceptions.RefactoringException(
                    'Adding duplicate parameter: <%s>.' % self.name)
        definition_info.args_with_defaults.insert(self.index,
                                                  (self.name, self.default))

    def change_argument_mapping(self, definition_info, mapping):
        if self.value is not None:
            mapping.param_dict[self.name] = self.value


class ArgumentDefaultInliner(_ArgumentChanger):
    
    def __init__(self, index):
        self.index = index
        self.remove = remove = False
    
    def change_definition_info(self, definition_info):
        if self.remove:
            definition_info.args_with_defaults[self.index] = \
                (definition_info.args_with_defaults[self.index][0], None)

    def change_argument_mapping(self, definition_info, mapping):
        default = definition_info.args_with_defaults[self.index][1]
        name = definition_info.args_with_defaults[self.index][0]
        if default is not None and name not in mapping.param_dict:
            mapping.param_dict[name] = default


class ArgumentReorderer(_ArgumentChanger):
    
    def __init__(self, new_order):
        self.new_order = new_order
    
    def change_definition_info(self, definition_info):
        new_args = list(definition_info.args_with_defaults)
        for index, new_index in enumerate(self.new_order):
            new_args[new_index] = definition_info.args_with_defaults[index]
        definition_info.args_with_defaults = new_args


# XXX: This cannot be used because we need some way of changing
# occurances inside function bodies.  By the way renaming
# parameters is already supported by normal rename refactoring.
# Supproting renaming parameters in change method signature
# increases the compexity considerably.  So we leave that for now.
class _XXXArgumentRenamer(_ArgumentChanger):
    
    def __init__(self, index, new_name):
        self.index = index
        self.new_name = new_name
    
    def change_definition_info(self, call_info):
        if self.index < len(call_info.args_with_defaults):
            call_info.args_with_defaults[self.index] = (
                self.new_name, call_info.args_with_defaults[self.index][1])
        elif self.index == len(call_info.args_with_defaults) and \
           call_info.args_arg is not None:
            call_info.args_arg = self.new_name
        elif (self.index == len(call_info.args_with_defaults) and
            call_info.args_arg is None and call_info.keywords_arg is not None) or \
           (self.index == len(call_info.args_with_defaults) + 1 and
            call_info.args_arg is not None and call_info.keywords_arg is not None):
            call_info.keywords_arg = self.new_name

    def change_argument_mapping(self, definition_info, mapping):
        if self.index < len(definition_info.args_with_defaults):
            old_name = definition_info.args_with_defaults[self.index][0]
            if old_name != self.new_name and old_name in mapping.param_dict:
                mapping.param_dict[self.new_name] = mapping.param_dict[old_name]
                del mapping.param_dict[old_name]
    

class _ChangeCallsInModule(object):
    
    def __init__(self, pycore, occurrence_finder, resource, call_changer):
        self.pycore = pycore
        self.occurrence_finder = occurrence_finder
        self.resource = resource
        self.call_changer = call_changer
        self._pymodule = None
        self._lines = None
        self._source = None

    def get_changed_module(self):
        change_collector = sourceutils.ChangeCollector(self.source)
        for occurrence in self.occurrence_finder.find_occurrences(self.resource):
            if not occurrence.is_called() and not occurrence.is_defined():
                continue
            start, end = occurrence.get_primary_range()
            begin_parens =  self.source.index('(', end)
            end_parens = self._find_end_parens(self.source, begin_parens)
            if occurrence.is_called():
                changed_call = self.call_changer.change_call(
                    self.source[start:end_parens])
            else:
                changed_call = self.call_changer.change_definition(
                    self.source[start:end_parens])
            if changed_call is not None:
                change_collector.add_change(start, end_parens, changed_call)
        return change_collector.get_changed()
    
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
