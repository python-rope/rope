import rope.base.change
from rope.base import codeanalyze, exceptions
from rope.refactor import functionutils, sourceutils, occurrences


class IntroduceParameter(object):

    def __init__(self, project, resource, offset):
        self.pycore = project.pycore
        self.resource = resource
        self.offset = offset
        self.pymodule = self.pycore.resource_to_pyobject(self.resource)
        scope = self.pymodule.get_scope().get_inner_scope_for_offset(offset)
        if scope.get_kind() != 'Function':
            raise exceptions.RefactoringError(
                'Introduce parameter should be performed inside functions')
        self.pyfunction = scope.pyobject
        self.name, self.pyname = self._get_name_and_pyname()
        if self.pyname is None:
            raise exceptions.RefactoringError(
                'Cannot find the definition of <%s>', self.name)

    def _get_primary(self):
        word_finder = codeanalyze.WordRangeFinder(self.resource.read())
        return word_finder.get_primary_at(self.offset)

    def _get_name_and_pyname(self):
        return (codeanalyze.get_name_at(self.resource, self.offset),
                codeanalyze.get_pyname_at(self.pycore, self.resource, self.offset))

    def get_changes(self, new_parameter):
        definition_info = functionutils.DefinitionInfo.read(self.pyfunction)
        definition_info.args_with_defaults.append((new_parameter,
                                                   self._get_primary()))
        change_collector = sourceutils.ChangeCollector(self.resource.read())
        header_start, header_end = self._get_header_offsets()
        body_start, body_end = sourceutils.get_body_region(self.pyfunction)
        change_collector.add_change(header_start, header_end,
                                    definition_info.to_string())
        self._change_function_occurances(change_collector, body_start,
                                         body_end, new_parameter)
        changes = rope.base.change.ChangeSet('Introduce parameter <%s>' % new_parameter)
        changes.add_change(rope.base.change.ChangeContents(self.resource,
                                                 change_collector.get_changed()))
        return changes

    def _get_header_offsets(self):
        lines = self.pymodule.lines
        start_line = self.pyfunction.get_scope().get_start()
        end_line = self.pymodule.logical_lines.\
                   get_logical_line_in(start_line)[1]
        start = lines.get_line_start(start_line)
        end = lines.get_line_end(end_line)
        start = self.pymodule.source_code.find('def', start) + 4
        end = self.pymodule.source_code.rfind(':', start, end)
        return start, end

    def _change_function_occurances(self, change_collector, function_start,
                                    function_end, new_name):
        finder = occurrences.FilteredFinder(self.pycore, self.name,
                                                      [self.pyname])
        for occurrence in finder.find_occurrences(resource=self.resource):
            start, end = occurrence.get_primary_range()
            if function_start <= start < function_end:
                change_collector.add_change(start, end, new_name)
