import rope.base.exceptions
from rope.base import pyobjects, codeanalyze
from rope.base.change import ChangeSet, ChangeContents, MoveResource
from rope.refactor import (importutils, rename, occurrences,
                           sourceutils, functionutils)


def create_move(project, resource, offset=None):
    """A factory for creating Move objects"""
    if offset is None:
        return Move(project, resource)
    pyname = codeanalyze.get_pyname_at(project.pycore, resource, offset)
    if pyname is None:
        raise rope.base.exceptions.RefactoringError(
            'Move only works on classes, functions, modules and methods.')
    pyobject = pyname.get_object()
    if isinstance(pyobject, pyobjects.PyModule) or \
       isinstance(pyobject, pyobjects.PyPackage):
        return Move(project, pyobject.get_resource())
    if isinstance(pyobject, pyobjects.PyFunction) and \
       isinstance(pyobject.parent, pyobjects.PyClass):
        return MoveMethod(project, resource, offset)
    return Move(project, resource, offset)


class MoveMethod(object):

    def __init__(self, project, resource, offset):
        self.pycore = project.pycore
        pyname = codeanalyze.get_pyname_at(project.pycore, resource, offset)
        self.method_name = codeanalyze.get_name_at(resource, offset)
        self.pyfunction = pyname.get_object()

    def get_changes(self, dest_attr, new_name):
        changes = ChangeSet('Moving method <%s>' % self.method_name)
        resource1, start1, end1, new_content1 = \
            self._get_changes_made_by_old_class(dest_attr, new_name)
        collector1 = sourceutils.ChangeCollector(resource1.read())
        collector1.add_change(start1, end1, new_content1)

        resource2, start2, end2, new_content2 = \
            self._get_changes_made_by_new_class(dest_attr, new_name)
        if resource1 == resource2:
            collector1.add_change(start2, end2, new_content2)
        else:
            collector2 = sourceutils.ChangeCollector(resource2.read())
            collector2.add_change(start2, end2, new_content2)
            changes.add_change(ChangeContents(resource2,
                                              collector2.get_changed()))
        changes.add_change(ChangeContents(resource1,
                                          collector1.get_changed()))
        return changes

    def _get_changes_made_by_old_class(self, dest_attr, new_name):
        pymodule = self.pyfunction.get_module()
        indents = sourceutils.get_indents(
            pymodule.lines, self.pyfunction.get_scope().get_start())
        body = 'return self.%s.%s(%s)\n' % (dest_attr, new_name,
                                            self._get_passed_arguments_string())
        region = sourceutils.get_body_region(self.pyfunction)
        return (pymodule.get_resource(), region[0], region[1],
                sourceutils.fix_indentation(body, indents + 4))

    def _get_changes_made_by_new_class(self, dest_attr, new_name):
        old_pyclass = self.pyfunction.parent
        pyclass = old_pyclass.get_attribute(dest_attr).get_object().get_type()
        pymodule = pyclass.get_module()
        resource = pyclass.get_module().get_resource()
        insertion_point = min(pymodule.lines.get_line_end(
                              pyclass.get_scope().get_end()) + 1,
                              len(pymodule.source_code))
        indents = sourceutils.get_indents(pymodule.lines,
                                          pyclass.get_scope().get_start())
        body = '\n\n' + sourceutils.fix_indentation(self.get_new_method(new_name),
                                                    indents + 4)
        return resource, insertion_point, insertion_point, body

    def get_new_method(self, name):
        return '%s\n    %s' % (self._get_new_header(name), self._get_body())

    def _get_unchanged_body(self):
        body = sourceutils.get_body(self.pyfunction)
        indented_body = sourceutils.fix_indentation(body, 4)
        return body

    def _get_body(self, host='host'):
        self_name = self._get_self_name()
        body = self_name + ' = None\n' + self._get_unchanged_body()
        pymodule = self.pycore.get_string_module(body)
        finder = occurrences.FilteredOccurrenceFinder(
            self.pycore, self_name, [pymodule.get_attribute(self_name)])
        result = rename.rename_in_module(finder, host, pymodule=pymodule)
        return result[result.index('\n') + 1:]

    def _get_self_name(self):
        definition_info = functionutils.DefinitionInfo.read(self.pyfunction)
        return definition_info.args_with_defaults[0][0]

    def _get_new_header(self, name):
        header = 'def %s(self' % name
        if self._is_host_used():
            header += ', host'
        definition_info = functionutils.DefinitionInfo.read(self.pyfunction)
        others = definition_info.arguments_to_string(1)
        if others:
            header += ', ' + others
        return header + '):'

    def _get_passed_arguments_string(self):
        result = ''
        if self._is_host_used():
            result = 'self'
        definition_info = functionutils.DefinitionInfo.read(self.pyfunction)
        others = definition_info.arguments_to_string(1)
        if others:
            result += ', ' + others
        return result

    def _is_host_used(self):
        return self._get_body('__old_self') != self._get_unchanged_body()


class Move(object):
    """A class for moving modules, packages, global functions and classes."""

    def __init__(self, project, resource, offset=None):
        self.pycore = project.pycore
        if offset is not None:
            self.pyname = codeanalyze.get_pyname_at(
                self.pycore, resource, offset)
            if self.pyname is None:
                raise rope.base.exceptions.RefactoringError(
                    'Move works on classes,functions or modules.')
        else:
            if not resource.is_folder() and resource.name == '__init__.py':
                resource = resource.parent
            dummy_pymodule = self.pycore.get_string_module('')
            self.pyname = rope.base.pynames.ImportedModule(
                dummy_pymodule, resource=resource)

    def get_changes(self, dest_resource):
        moving_object = self.pyname.get_object()
        if moving_object.get_type() == pyobjects.get_base_type('Module'):
            mover = MoveModule(self.pycore, self.pyname, dest_resource)
        else:
            mover = MoveGlobal(self.pycore, self.pyname, dest_resource)
        return mover.get_changes()


class _Mover(object):

    def __init__(self, pycore, source, destination,
                 pyname, old_name, new_name):
        self.pycore = pycore
        self.source = source
        self.destination = destination
        self.old_pyname = pyname
        self.old_name = old_name
        self.new_name = new_name
        self.import_tools = importutils.ImportTools(self.pycore)
        self._check_exceptional_conditions()

    def _check_exceptional_conditions(self):
        pass

    def _add_imports_to_module(self, pymodule, new_imports):
        module_with_imports = self.import_tools.get_module_imports(pymodule)
        for new_import in new_imports:
            module_with_imports.add_import(new_import)
        return module_with_imports.get_changed_source()

    def _add_imports_to_module2(self, pymodule, new_imports):
        source = self._add_imports_to_module(pymodule, new_imports)
        if source is None:
            return pymodule, False
        else:
            return self.pycore.get_string_module(source, pymodule.get_resource()), True

    def _remove_old_pyname_imports(self, pymodule):
        old_source = pymodule.source_code
        module_with_imports = self.import_tools.get_module_imports(pymodule)
        class CanSelect(object):
            changed = False
            old_name = self.old_name
            old_pyname = self.old_pyname
            def __call__(self, name):
                try:
                    if name == self.old_name and \
                       pymodule.get_attribute(name).get_object() == \
                       self.old_pyname.get_object():
                        self.changed = True
                        return False
                except rope.base.exceptions.AttributeNotFoundError:
                    pass
                return True
        can_select = CanSelect()
        module_with_imports.filter_names(can_select)
        new_source = module_with_imports.get_changed_source()
        if old_source != new_source:
            pymodule = self.pycore.get_string_module(new_source,
                                                     pymodule.get_resource())
        return pymodule, can_select.changed

    def _rename_in_module(self, pymodule, new_name, imports=False):
        occurrence_finder = occurrences.FilteredOccurrenceFinder(
            self.pycore, self.old_name, [self.old_pyname], imports=imports)
        source = rename.rename_in_module(occurrence_finder, new_name,
                                         pymodule=pymodule, replace_primary=True)
        if source is None:
            return pymodule, False
        else:
            return self.pycore.get_string_module(source, pymodule.get_resource()), True


class MoveGlobal(_Mover):
    """For moving global function and classes"""

    def __init__(self, pycore, pyname, destination):
        old_name = pyname.get_object()._get_ast().name
        pymodule = pyname.get_object().get_module()
        source = pymodule.get_resource()
        new_name = importutils.get_module_name(
            pycore, destination) + '.' + old_name
        if destination.is_folder() and destination.has_child('__init__.py'):
            destination = destination.get_child('__init__.py')

        super(MoveGlobal, self).__init__(pycore, source, destination,
                                           pyname, old_name, new_name)
        self.new_import = self.import_tools.get_import_for_module(
            self.pycore.resource_to_pyobject(self.destination))
        scope = pyname.get_object().get_scope()

    def _check_exceptional_conditions(self):
        if self.old_pyname is None or \
           not isinstance(self.old_pyname.get_object(), pyobjects.PyDefinedObject):
            raise rope.base.exceptions.RefactoringError(
                'Move refactoring should be performed on a class/function.')
        moving_pyobject = self.old_pyname.get_object()
        if not self._is_global(moving_pyobject):
            raise rope.base.exceptions.RefactoringError(
                'Move refactoring should be performed on a global class/function.')
        if self.destination.is_folder():
            raise rope.base.exceptions.RefactoringError(
                'Move destination for non-modules should not be folders.')

    def _is_global(self, pyobject):
        return pyobject.get_scope().parent == pyobject.get_module().get_scope()

    def get_changes(self):
        changes = ChangeSet('Moving global <%s>' % self.old_name)
        self._change_destination_module(changes)
        self._change_source_module(changes)
        self._change_other_modules(changes)
        return changes

    def _change_source_module(self, changes):
        uses_moving = False
        # Changing occurrences
        pymodule = self.pycore.resource_to_pyobject(self.source)
        pymodule, has_changed = self._rename_in_module(pymodule, self.new_name)
        if has_changed:
            uses_moving = True
        source = self._get_moved_moving_source(pymodule)
        if uses_moving:
            pymodule = self.pycore.get_string_module(source, self.source)
            # Adding new import
            source = self._add_imports_to_module(pymodule, [self.new_import])

        changes.add_change(ChangeContents(self.source, source))

    def _get_moved_moving_source(self, pymodule):
        source = pymodule.source_code
        lines = pymodule.lines
        scope = self.old_pyname.get_object().get_scope()
        start = lines.get_line_start(scope.get_start())
        end = lines.get_line_end(scope.get_end())
        source = source[:start] + source[end + 1:]
        return source

    def _change_destination_module(self, changes):
        # Changing occurrences
        pymodule = self.pycore.resource_to_pyobject(self.destination)
        pymodule, has_changed = self._rename_in_module(pymodule, self.old_name)

        moving, imports = self._get_moving_element_with_imports()
        pymodule, has_changed = self._remove_old_pyname_imports(pymodule)
        pymodule, has_changed = self._add_imports_to_module2(pymodule, imports)

        module_with_imports = self.import_tools.get_module_imports(pymodule)
        source = pymodule.source_code
        if module_with_imports.get_import_statements():
            start = pymodule.lines.get_line_end(
                module_with_imports.get_import_statements()[-1].end_line - 1)
            result = source[:start + 1] + '\n\n'
        else:
            result = ''
            start = -1
        result += moving + '\n' + source[start + 1:]

        # Organizing imports
        source = result
        pymodule = self.pycore.get_string_module(source, self.destination)
        source = self.import_tools.organize_imports(pymodule)
        changes.add_change(ChangeContents(self.destination, source))

    def _get_moving_element_with_imports(self):
        moving = self._get_moving_element()
        source_pymodule = self.pycore.resource_to_pyobject(self.source)
        new_imports = self._get_used_imports_by_the_moving_element()
        new_imports.append(self.import_tools.get_from_import_for_module(source_pymodule, '*'))

        pymodule = self.pycore.get_string_module(moving, self.source)
        pymodule, has_changed = self._add_imports_to_module2(pymodule, new_imports)

        source = self.import_tools.relatives_to_absolutes(pymodule)
        if source is not None:
            pymodule = self.pycore.get_string_module(source, self.source)
        source = self.import_tools.froms_to_imports(pymodule)
        module_with_imports = self._get_module_with_imports(source, self.source)
        imports = [import_stmt.import_info
                   for import_stmt in module_with_imports.get_import_statements()]
        start = 1
        if module_with_imports.get_import_statements():
            start = module_with_imports.get_import_statements()[-1].end_line
        lines = codeanalyze.SourceLinesAdapter(source)
        moving = source[lines.get_line_start(start):]
        return moving, imports

    def _get_module_with_imports(self, source_code, resource):
        pymodule = self.pycore.get_string_module(source_code, resource)
        return self.import_tools.get_module_imports(pymodule)

    def _get_moving_element(self):
        lines = self.pycore.resource_to_pyobject(self.source).lines
        scope = self.old_pyname.get_object().get_scope()
        start = lines.get_line_start(scope.get_start())
        end = lines.get_line_end(scope.get_end())
        moving = self.source.read()[start:end]
        return moving

    def _get_used_imports_by_the_moving_element(self):
        pymodule = self.pycore.resource_to_pyobject(self.source)
        module_with_imports = self.import_tools.get_module_imports(pymodule)
        return module_with_imports.get_used_imports(self.old_pyname.get_object())

    def _change_other_modules(self, changes):
        for file_ in self.pycore.get_python_files():
            if file_ in (self.source, self.destination):
                continue
            is_changed = False
            should_import = False
            pymodule = self.pycore.resource_to_pyobject(file_)
            # Changing occurrences
            pymodule, has_changed = self._rename_in_module(pymodule, self.new_name)
            if has_changed:
                should_import = True
                is_changed = True
            # Removing out of date imports
            pymodule, has_changed = self._remove_old_pyname_imports(pymodule)
            if has_changed:
                is_changed = True
            # Adding new import
            if should_import:
                source = self._add_imports_to_module(pymodule, [self.new_import])
            if is_changed:
                changes.add_change(ChangeContents(file_, source))


class MoveModule(_Mover):
    """For moving modules and packages"""

    def __init__(self, pycore, pyname, destination):
        source = pyname.get_object().get_resource()
        if source.is_folder():
            old_name = source.name
        else:
            old_name = source.name[:-3]
        package = importutils.get_module_name(pycore, destination)
        if package:
            new_name = package + '.' + old_name
        else:
            new_name = old_name
        super(MoveModule, self).__init__(pycore, source, destination,
                                           pyname, old_name, new_name)
        self.new_import = importutils.NormalImport([(self.new_name, None)])

    def _check_exceptional_conditions(self):
        moving_pyobject = self.old_pyname.get_object()
        if not self.destination.is_folder():
            raise rope.base.exceptions.RefactoringError(
                'Move destination for modules should be packages.')

    def get_changes(self):
        changes = ChangeSet('Moving module <%s>' % self.old_name)
        self._change_other_modules(changes)
        self._change_moving_module(changes)
        return changes

    def _change_moving_module(self, changes):
        if not self.source.is_folder():
            is_changed = False
            pymodule = self.pycore.resource_to_pyobject(self.source)
            source = self.import_tools.relatives_to_absolutes(pymodule)
            if source is not None:
                pymodule = self.pycore.get_string_module(source, self.source)
                is_changed = True
            source = self._change_occurrences_in_module(pymodule)
            if source is not None:
                is_changed = True
            else:
                source = pymodule.source_code
            if is_changed:
                changes.add_change(ChangeContents(self.source, source))
        changes.add_change(MoveResource(self.source,
                                        self.destination.path))

    def _change_other_modules(self, changes):
        for module in self.pycore.get_python_files():
            if module in (self.source, self.destination):
                continue
            pymodule = self.pycore.resource_to_pyobject(module)
            source = self._change_occurrences_in_module(pymodule)
            if source is not None:
                changes.add_change(ChangeContents(module, source))

    def _change_occurrences_in_module(self, pymodule):
        is_changed = False
        should_import = False
        pymodule, has_changed = self._rename_in_module(pymodule, self.new_name,
                                                       imports=True)
        if has_changed:
            is_changed = True
        pymodule, has_changed = self._remove_old_pyname_imports(pymodule)
        if has_changed:
            should_import = True
            is_changed = True
        if should_import:
            source = self._add_imports_to_module(pymodule, [self.new_import])
        else:
            source = pymodule.source_code
        if is_changed:
            return source
