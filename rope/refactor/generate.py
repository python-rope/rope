from rope.base import change, codeanalyze, pyobjects
from rope.refactor import sourceutils


class GenerateVariable(object):

    def __init__(self, project, resource, offset):
        self.insertion_location = _InsertionLocation(project.pycore,
                                                     resource, offset)
        self.name = codeanalyze.get_name_at(resource, offset)

    def get_changes(self):
        changes = change.ChangeSet('Generate Variable %s' % self.name)
        indents = self.insertion_location.get_scope_indents()
        definition = sourceutils.fix_indentation('%s = None\n' % self.name,
                                                 indents)

        resource = self.insertion_location.get_insertion_resource()
        start, end = self.insertion_location.get_insertion_offsets()

        collector = sourceutils.ChangeCollector(resource.read())
        collector.add_change(start, end, definition)
        changes.add_change(change.ChangeContents(
                           resource, collector.get_changed()))
        return changes

    def get_location(self):
        return (self.insertion_location.get_insertion_resource(),
                self.insertion_location.get_insertion_lineno())


class _InsertionLocation(object):

    def __init__(self, pycore, resource, offset):
        self.pycore = pycore
        self.resource = resource
        self.offset = offset
        self.source_pymodule = self.pycore.resource_to_pyobject(resource)
        finder = codeanalyze.ScopeNameFinder(self.source_pymodule)
        self.primary, self.pyname = finder.get_primary_and_pyname_at(offset)
        self.goal_pymodule = self._get_goal_module()
        self.source_scope = self._get_source_scope()
        self.goal_scope = self._get_goal_scope()

    def _get_goal_scope(self):
        if self.primary is None:
            return self._get_source_scope()
        pyobject = self.primary.get_object()
        if isinstance(pyobject, pyobjects.PyDefinedObject):
            return pyobject.get_scope()
        elif isinstance(pyobject.get_type(), pyobjects.PyClass):
            return pyobject.get_type().get_scope()

    def _get_goal_module(self):
        scope = self._get_goal_scope()
        while scope.parent is not None:
            scope = scope.parent
        return scope.pyobject

    def _get_source_scope(self):
        module_scope = self.source_pymodule.get_scope()
        lineno = self.source_pymodule.lines.get_line_number(self.offset)
        return module_scope.get_inner_scope_for_line(lineno)

    def get_insertion_lineno(self):
        lines = self.goal_pymodule.lines
        if self.goal_scope == self.source_scope:
            line_finder = codeanalyze.LogicalLineFinder(lines)
            current_line = lines.get_line_number(self.offset)
            return line_finder.get_logical_line_in(current_line)[0]
        else:
            return min(self.goal_scope.get_end() + 1, lines.length())

    def get_insertion_resource(self):
        return self.goal_pymodule.get_resource()

    def get_insertion_offsets(self):
        if self.goal_scope.get_kind() == 'Class':
            start, end = sourceutils.get_body_region(self.goal_scope.pyobject)
            if self.goal_pymodule.source_code[start:end].strip() == 'pass':
                return start, end
        lines = self.source_pymodule.lines
        start = lines.get_line_start(self.get_insertion_lineno())
        return (start, start)


    def get_scope_indents(self):
        if self.goal_scope.get_kind() == 'Module':
            return 0
        return sourceutils.get_indents(self.goal_pymodule.lines,
                                       self.goal_scope.get_start()) + 4
