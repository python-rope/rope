import copy

import rope.base.exceptions
from rope.base import pyobjects, codeanalyze, taskhandle, evaluate
from rope.base.change import ChangeContents, ChangeSet
from rope.refactor import occurrences, sourceutils, functionutils, rename


class ChangeSignature(object):

    def __init__(self, project, resource, offset):
        self.pycore = project.pycore
        self.resource = resource
        self.offset = offset
        self._set_name_and_pyname()
        if self.pyname is None or self.pyname.get_object() is None or \
           not isinstance(self.pyname.get_object(), pyobjects.PyFunction):
            raise rope.base.exceptions.RefactoringError(
                'Change method signature should be performed on functions')

    def _set_name_and_pyname(self):
        self.name = codeanalyze.get_name_at(self.resource, self.offset)
        self.primary, self.pyname = evaluate.get_primary_and_pyname_at(
            self.pycore, self.resource, self.offset)
        if self.pyname is None:
            return
        pyobject = self.pyname.get_object()
        if isinstance(pyobject, pyobjects.PyClass) and \
           '__init__' in pyobject.get_attributes():
            self.pyname = pyobject.get_attribute('__init__')
            self.name = '__init__'
        pyobject = self.pyname.get_object()
        self.others = None
        if self.name == '__init__' and \
           isinstance(pyobject, pyobjects.PyFunction) and \
           isinstance(pyobject.parent, pyobjects.PyClass):
            pyclass = pyobject.parent
            self.others = (pyclass.get_name(),
                           pyclass.parent.get_attribute(pyclass.get_name()))

    def _change_calls(self, call_changer, in_hierarchy=False,
                      handle=taskhandle.NullTaskHandle()):
        changes = ChangeSet('Changing signature of <%s>' % self.name)
        job_set = handle.create_jobset('Collecting Changes',
                                        len(self.pycore.get_python_files()))
        pynames = rename.FindMatchingPyNames(
            self.primary, self.pyname, self.name, False,
            in_hierarchy and self.is_method(), handle).get_all()
        finder = occurrences.FilteredFinder(self.pycore, self.name, pynames)
        if self.others:
            name, pyname = self.others
            constructor_finder = occurrences.FilteredFinder(
                self.pycore, name, [pyname], only_calls=True)
            finder = occurrences.MultipleFinders(
                [finder, constructor_finder])
        for file in self.pycore.get_python_files():
            job_set.started_job('Working on <%s>' % file.path)
            change_calls = _ChangeCallsInModule(
                self.pycore, finder, file, call_changer)
            changed_file = change_calls.get_changed_module()
            if changed_file is not None:
                changes.add_change(ChangeContents(file, changed_file))
            job_set.finished_job()
        return changes

    def is_method(self):
        pyfunction = self.pyname.get_object()
        return isinstance(pyfunction.parent, pyobjects.PyClass)

    def get_definition_info(self):
        return functionutils.DefinitionInfo.read(self.pyname.get_object())

    def normalize(self):
        changer = _FunctionChangers(
            self.pyname.get_object(), self.get_definition_info(),
            [ArgumentNormalizer()])
        return self._change_calls(changer)

    def remove(self, index):
        changer = _FunctionChangers(
            self.pyname.get_object(), self.get_definition_info(),
            [ArgumentRemover(index)])
        return self._change_calls(changer)

    def add(self, index, name, default=None, value=None):
        changer = _FunctionChangers(
            self.pyname.get_object(), self.get_definition_info(),
            [ArgumentAdder(index, name, default, value)])
        return self._change_calls(changer)

    def inline_default(self, index):
        changer = _FunctionChangers(
            self.pyname.get_object(), self.get_definition_info(),
            [ArgumentDefaultInliner(index)])
        return self._change_calls(changer)

    def reorder(self, new_ordering):
        changer = _FunctionChangers(
            self.pyname.get_object(), self.get_definition_info(),
            [ArgumentReorderer(new_ordering)])
        return self._change_calls(changer)

    def get_changes(self, changers, in_hierarchy=False,
                    task_handle=taskhandle.NullTaskHandle()):
        """Get changes caused by this refactoring

        `changers` is a list of `_ArgumentChanger`\s.  If `in_hierarchy`
        is `True` the changers are applyed to all matching methods in
        the class hierarchy.

        """
        function_changer = _FunctionChangers(
            self.pyname.get_object(), self.get_definition_info(), changers)
        return self._change_calls(function_changer, in_hierarchy, task_handle)


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

    def change_call(self, primary, pyname, call):
        call_info = functionutils.CallInfo.read(
            primary, pyname, self.definition_info, call)
        mapping = functionutils.ArgumentMapping(self.definition_info, call_info)

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
                raise rope.base.exceptions.RefactoringError(
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
        """Construct an `ArgumentReorderer`

        Note that the `new_order` is a list containing the new
        position of parameters; not the position each parameter
        is going to be moved to. (changed in ``0.5m4``)

        For example changing ``f(a, b, c)`` to ``f(c, a, b)``
        requires passing ``[2, 0, 1]`` and *not* ``[1, 2, 0]``.

        """
        self.new_order = new_order

    def change_definition_info(self, definition_info):
        new_args = list(definition_info.args_with_defaults)
        for new_index, index in enumerate(self.new_order):
            new_args[new_index] = definition_info.args_with_defaults[index]
        definition_info.args_with_defaults = new_args


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
        word_finder = codeanalyze.WordRangeFinder(self.source)
        change_collector = sourceutils.ChangeCollector(self.source)
        for occurrence in self.occurrence_finder.find_occurrences(self.resource):
            if not occurrence.is_called() and not occurrence.is_defined():
                continue
            start, end = occurrence.get_primary_range()
            begin_parens, end_parens = word_finder.get_word_parens_range(end - 1)
            if occurrence.is_called():
                primary, pyname = occurrence.get_primary_and_pyname()
                changed_call = self.call_changer.change_call(
                    primary, pyname, self.source[start:end_parens])
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

    source = property(_get_source)
    lines = property(_get_lines)
    pymodule = property(_get_pymodule)
