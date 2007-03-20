from rope.base import change, codeanalyze, pyobjects, exceptions, pynames
from rope.refactor import sourceutils
from rope.refactor import importutils


def create_generate(kind, project, resource, offset):
    """A factory for creating `Generate` objects

    `kind` can be ``variable``, ``function``, ``class``, ``module``
    or ``package``.

    """
    generate = eval('Generate' + kind.title())
    return generate(project, resource, offset)


class _Generate(object):

    def __init__(self, project, resource, offset):
        self.project = project
        self.resource = resource
        self.insertion_location = _InsertionLocation(project.pycore,
                                                     resource, offset)
        self.name = codeanalyze.get_name_at(resource, offset)
        self._check_exceptional_conditions()

    def _check_exceptional_conditions(self):
        if self.insertion_location.element_already_exists():
            raise exceptions.RefactoringError(
                'Element <%s> already exists.' % self.name)
        if not self.insertion_location.primary_is_found():
            raise exceptions.RefactoringError(
                'Cannot determine the scope <%s> should be defined in.' % self.name)

    def get_changes(self):
        changes = change.ChangeSet('Generate %s <%s>' %
                                   (self._get_element_kind(), self.name))
        indents = self.insertion_location.get_scope_indents()
        blanks = self.insertion_location.get_blank_lines()
        base_definition = sourceutils.fix_indentation(self._get_element(), indents)
        definition = '\n' * blanks[0] + base_definition + '\n' * blanks[1]

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

    def _get_element_kind(self):
        raise NotImplementedError()

    def _get_element(self):
        raise NotImplementedError()


class GenerateFunction(_Generate):

    def _get_element(self):
        return 'def %s():\n    pass\n' % self.name

    def _get_element_kind(self):
        return 'Function'


class GenerateVariable(_Generate):

    def _get_element(self):
        return '%s = None\n' % self.name

    def _get_element_kind(self):
        return 'Class'


class GenerateClass(_Generate):

    def _get_element(self):
        return 'class %s(object):\n    pass\n' % self.name

    def _get_element_kind(self):
        return 'Class'


class GenerateModule(_Generate):

    def get_changes(self):
        package = self.insertion_location.get_package()
        changes = change.ChangeSet('Generate Module <%s>' % self.name)
        new_resource = self.project.get_file('%s/%s.py' % (package.path, self.name))
        if new_resource.exists():
            raise exceptions.RefactoringError(
                'Module <%s> already exists' % new_resource.path)
        changes.add_change(change.CreateResource(new_resource))
        changes.add_change(_add_import_to_module(
                           self.project.get_pycore(), self.resource, new_resource))
        return changes

    def get_location(self):
        package = self.insertion_location.get_package()
        return (package.get_child('%s.py' % self.name) , 1)


class GeneratePackage(_Generate):

    def get_changes(self):
        package = self.insertion_location.get_package()
        changes = change.ChangeSet('Generate Package <%s>' % self.name)
        new_resource = self.project.get_folder('%s/%s' % (package.path, self.name))
        if new_resource.exists():
            raise exceptions.RefactoringError(
                'Package <%s> already exists' % new_resource.path)
        changes.add_change(change.CreateResource(new_resource))
        changes.add_change(_add_import_to_module(
                           self.project.get_pycore(), self.resource, new_resource))
        child = self.project.get_folder(package.path + '/' + self.name)
        changes.add_change(change.CreateFile(child, '__init__.py'))
        return changes

    def get_location(self):
        package = self.insertion_location.get_package()
        child = package.get_child(self.name)
        return (child.get_child('__init__.py') , 1)


def _add_import_to_module(pycore, resource, imported):
    pymodule = pycore.resource_to_pyobject(resource)
    import_tools = importutils.ImportTools(pycore)
    module_imports = import_tools.get_module_imports(pymodule)
    module_name = importutils.get_module_name(pycore, imported)
    new_import = importutils.NormalImport(((module_name, None), ))
    module_imports.add_import(new_import)
    return change.ChangeContents(resource, module_imports.get_changed_source())


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
        if scope is None:
            return
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

    def get_blank_lines(self):
        if self.goal_scope.get_kind() == 'Module':
            base_blanks = 2
            if self.goal_pymodule.source_code.strip() == '':
                base_blanks = 0
        if self.goal_scope.get_kind() == 'Class':
            base_blanks = 1
        if self.goal_scope.get_kind() == 'Function':
            base_blanks = 0
        if self.goal_scope == self.source_scope:
            return (0, base_blanks)
        return (base_blanks, 0)

    def get_package(self):
        primary = self.primary
        if self.primary is None:
            return self.pycore.get_source_folders()[0]
        if isinstance(primary.get_object(), pyobjects.PyPackage):
            return primary.get_object().get_resource()
        raise exceptions.RefactoringError(
            'A module/package can be only created in a package.')

    def primary_is_found(self):
        return self.goal_scope is not None

    def element_already_exists(self):
        if self.pyname is None or isinstance(self.pyname, pynames.UnboundName):
            return False
        return True
