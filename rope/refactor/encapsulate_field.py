import rope.base.codeanalyze
from rope.base import pynames
from rope.base.change import ChangeSet, ChangeContents
from rope.refactor import sourceutils, taskhandle


class EncapsulateField(object):

    def __init__(self, project, resource, offset):
        self.pycore = project.pycore
        self.name = rope.base.codeanalyze.get_name_at(resource, offset)
        self.pyname = rope.base.codeanalyze.get_pyname_at(self.pycore,
                                                          resource, offset)
        if not self._is_an_attribute(self.pyname):
            raise rope.base.exceptions.RefactoringError(
                'Encapsulate field should be performed on class attributes.')
        self.resource = self.pyname.get_definition_location()[0].get_resource()

    def _is_an_attribute(self, pyname):
        if pyname is not None and isinstance(pyname, pynames.AssignedName):
            defining_pymodule, defining_line = self.pyname.get_definition_location()
            defining_scope = defining_pymodule.get_scope().\
                             get_inner_scope_for_line(defining_line)
            parent = defining_scope.parent
            if defining_scope.get_kind() == 'Class' or \
               (parent is not None and parent.get_kind() == 'Class'):
                return True
        return False

    def get_changes(self, task_handle=taskhandle.NullTaskHandle()):
        changes = ChangeSet('Encapsulate field <%s>' % self.name)
        job_set = task_handle.create_job_set(
            'Collecting Changes', len(self.pycore.get_python_files()))
        rename_in_module = GetterSetterRenameInModule(self.pycore, self.name,
                                                      [self.pyname])
        job_set.started_job('Working on defining file')
        self._change_holding_module(changes, rename_in_module)
        job_set.finished_job()
        for file in self.pycore.get_python_files():
            if file == self.resource:
                continue
            job_set.started_job('Working on <%s>' % file.path)
            result = rename_in_module.get_changed_module(file)
            if result is not None:
                changes.add_change(ChangeContents(file, result))
            job_set.finished_job()
        return changes

    def _get_defining_class_scope(self):
        defining_pymodule, defining_line = self.pyname.get_definition_location()
        defining_scope = defining_pymodule.get_scope().get_inner_scope_for_line(defining_line)
        if defining_scope.get_kind() == 'Function':
            defining_scope = defining_scope.parent
        return defining_scope

    def _change_holding_module(self, changes, rename_in_module):
        pymodule = self.pycore.resource_to_pyobject(self.resource)
        class_scope = self._get_defining_class_scope()
        class_start_line = class_scope.get_start()
        class_end_line = class_scope.get_end()
        class_start = pymodule.lines.get_line_start(class_start_line)
        class_end = pymodule.lines.get_line_end(class_end_line)
        new_source = rename_in_module.get_changed_module(pymodule=pymodule,
                                                         skip_start=class_start,
                                                         skip_end=class_end)
        if new_source is not None:
            pymodule = self.pycore.get_string_module(new_source, self.resource)
            class_scope = pymodule.get_scope().get_inner_scope_for_line(class_start_line)
        getter = 'def get_%s(self):\n    return self.%s' % (self.name, self.name)
        setter = 'def set_%s(self, value):\n    self.%s = value' % (self.name, self.name)
        new_source = sourceutils.add_methods(pymodule, class_scope,
                                             [getter, setter])
        changes.add_change(ChangeContents(pymodule.get_resource(), new_source))


class GetterSetterRenameInModule(object):

    def __init__(self, pycore, name, pynames):
        self.pycore = pycore
        self.name = name
        self.occurrences_finder = rope.refactor.occurrences.\
                                  FilteredFinder(pycore, name, pynames)
        self.getter = 'get_' + name
        self.setter = 'set_' + name

    def get_changed_module(self, resource=None, pymodule=None, skip_start=0, skip_end=0):
        return _FindChangesForModule(self, resource, pymodule,
                                     skip_start, skip_end).get_changed_module()


class _FindChangesForModule(object):

    def __init__(self, occurrence_finder, resource, pymodule, skip_start, skip_end):
        self.pycore = occurrence_finder.pycore
        self.occurrences_finder = occurrence_finder.occurrences_finder
        self.getter = occurrence_finder.getter
        self.setter = occurrence_finder.setter
        self.resource = resource
        self.pymodule = pymodule
        self._source = None
        self._lines = None
        self.last_modified = 0
        self.last_set = None
        self.set_index = None
        self.skip_start = skip_start
        self.skip_end = skip_end

    def get_changed_module(self):
        result = []
        line_finder = None
        word_finder = rope.base.codeanalyze.WordRangeFinder(self.source)
        for occurrence in self.occurrences_finder.find_occurrences(self.resource,
                                                                   self.pymodule):
            start, end = occurrence.get_word_range()
            if self.skip_start <= start < self.skip_end:
                continue
            self._manage_writes(start, result)
            result.append(self.source[self.last_modified:start])
            if self._is_assigned_in_a_tuple_assignment(occurrence):
                raise rope.base.exceptions.RefactoringError(
                    'Cannot handle tuple assignments in encapsulate field.')
            if occurrence.is_written():
                assignment_type = word_finder.get_assignment_type(start)
                if assignment_type == '=':
                    result.append(self.setter + '(')
                else:
                    var_name = self.source[occurrence.get_primary_range()[0]:
                                           start] + self.getter + '()'
                    result.append(self.setter + '(' + var_name + ' %s ' % assignment_type[:-1])
                if line_finder is None:
                    line_finder = rope.base.codeanalyze.LogicalLineFinder(self.lines)
                current_line = self.lines.get_line_number(start)
                start_line, end_line = line_finder.get_logical_line_in(current_line)
                self.last_set = self.lines.get_line_end(end_line)
                end = self.source.index('=', end) + 1
                self.set_index = len(result)
            else:
                result.append(self.getter + '()')
            self.last_modified = end
        if self.last_modified != 0:
            self._manage_writes(len(self.source), result)
            result.append(self.source[self.last_modified:])
            return ''.join(result)
        return None

    def _manage_writes(self, offset, result):
        if self.last_set is not None and self.last_set <= offset:
            result.append(self.source[self.last_modified:self.last_set])
            set_value = ''.join(result[self.set_index:]).strip()
            del result[self.set_index:]
            result.append(set_value + ')')
            self.last_modified = self.last_set
            self.last_set = None

    def _is_assigned_in_a_tuple_assignment(self, occurance):
        line_finder = rope.base.codeanalyze.LogicalLineFinder(self.lines)
        offset = occurance.get_word_range()[0]
        lineno = self.lines.get_line_number(offset)
        start_line, end_line = line_finder.get_logical_line_in(lineno)
        start_offset = self.lines.get_line_start(start_line)

        line = self.source[start_offset:self.lines.get_line_end(end_line)]
        word_finder = rope.base.codeanalyze.WordRangeFinder(line)

        relative_offset = offset - start_offset
        relative_primary_start = occurance.get_primary_range()[0] - start_offset
        relative_primary_end = occurance.get_primary_range()[1] - start_offset
        prev_char_offset = word_finder._find_last_non_space_char(relative_primary_start - 1)
        next_char_offset = word_finder._find_first_non_space_char(relative_primary_end)
        next_char = prev_char = ''
        if prev_char_offset >= 0:
            prev_char = line[prev_char_offset]
        if next_char_offset < len(line):
            next_char = line[next_char_offset]
        try:
            equals_offset = line.index('=')
        except ValueError:
            return False
        if prev_char != ',' and next_char not in ',)':
            return False
        parens_start = word_finder.find_parens_start_from_inside(relative_offset)
        return relative_offset < equals_offset and (parens_start <= 0 or
                                                    line[:parens_start].strip() == '')

    def _get_source(self):
        if self._source is None:
            if self.resource is not None:
                self._source = self.resource.read()
            else:
                self._source = self.pymodule.source_code
        return self._source

    def _get_lines(self):
        if self._lines is None:
            if self.pymodule is None:
                self.pymodule = self.pycore.resource_to_pyobject(self.resource)
            self._lines = self.pymodule.lines
        return self._lines

    source = property(_get_source)
    lines = property(_get_lines)
