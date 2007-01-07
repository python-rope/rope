import rope.base.codeanalyze
import rope.base.pyobjects
import rope.base.exceptions
from rope.refactor import importutils
from rope.refactor import rename
from rope.refactor import occurrences
from rope.refactor.change import (ChangeSet, ChangeContents,
                                  MoveResource, CreateFolder)


class MoveRefactoring(object):
    """A class for moving modules, packages, global functions and classes."""

    def __init__(self, pycore, resource, offset=None):
        self.pycore = pycore
        if offset is not None:
            self.pyname = rope.base.codeanalyze.get_pyname_at(self.pycore, resource, offset)
            if self.pyname is None:
                raise rope.base.exceptions.RefactoringException(
                    'Move works on classes,functions or modules.')
        else:
            if not resource.is_folder() and resource.get_name() == '__init__.py':
                resource = resource.get_parent()
            dummy_pymodule = self.pycore.get_string_module('')
            self.pyname = rope.base.pynames.ImportedModule(dummy_pymodule, resource=resource)

    def get_changes(self, dest_resource):
        moving_object = self.pyname.get_object()
        if moving_object.get_type() == rope.base.pyobjects.PyObject.get_base_type('Module'):
            mover = _ModuleMover(self.pycore, self.pyname, dest_resource)
        else:
            mover = _GlobalMover(self.pycore, self.pyname, dest_resource)
        return mover.move()


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
        module_with_imports = self.import_tools.get_module_with_imports(pymodule)
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
        module_with_imports = self.import_tools.get_module_with_imports(pymodule)
        def can_select(name):
            try:
                if name == self.old_name and \
                   pymodule.get_attribute(name).get_object() == self.old_pyname.get_object():
                    return False
            except rope.base.exceptions.AttributeNotFoundException:
                pass
            return True
        module_with_imports.filter_names(can_select)
        new_source = module_with_imports.get_changed_source()
        if old_source != new_source:
            pymodule = self.pycore.get_string_module(new_source, pymodule.get_resource())
            return pymodule, True
        return pymodule, False

    def _rename_in_module(self, pymodule, new_name, imports=False):
        occurrence_finder = occurrences.FilteredOccurrenceFinder(
            self.pycore, self.old_name, [self.old_pyname], imports=imports)
        source = rename.rename_in_module(occurrence_finder, new_name,
                                         pymodule=pymodule, replace_primary=True)
        if source is None:
            return pymodule, False
        else:
            return self.pycore.get_string_module(source, pymodule.get_resource()), True


class _GlobalMover(_Mover):

    def __init__(self, pycore, pyname, destination):
        old_name = pyname.get_object()._get_ast().name
        pymodule = pyname.get_object().get_module()
        source = pymodule.get_resource()
        new_name = importutils.get_module_name(
            pycore, destination) + '.' + old_name
        if destination.is_folder() and destination.has_child('__init__.py'):
            destination = destination.get_child('__init__.py')

        super(_GlobalMover, self).__init__(pycore, source, destination,
                                           pyname, old_name, new_name)
        self.new_import = self.import_tools.get_import_for_module(
            self.pycore.resource_to_pyobject(self.destination))
        scope = pyname.get_object().get_scope()

    def _check_exceptional_conditions(self):
        if self.old_pyname is None or \
           not isinstance(self.old_pyname.get_object(), rope.base.pyobjects.PyDefinedObject):
            raise rope.base.exceptions.RefactoringException(
                'Move refactoring should be performed on a class/function.')
        moving_pyobject = self.old_pyname.get_object()
        if not self._is_global(moving_pyobject):
            raise rope.base.exceptions.RefactoringException(
                'Move refactoring should be performed on a global class/function.')
        if self.destination.is_folder():
            raise rope.base.exceptions.RefactoringException(
                'Move destination for non-modules should not be folders.')

    def _is_global(self, pyobject):
        return pyobject.get_scope().parent == pyobject.get_module().get_scope()

    def move(self):
        changes = ChangeSet()
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

        module_with_imports = self.import_tools.get_module_with_imports(pymodule)
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

        source = self.import_tools.transform_relative_imports_to_absolute(pymodule)
        if source is not None:
            pymodule = self.pycore.get_string_module(source, self.source)
        source = self.import_tools.transform_froms_to_normal_imports(pymodule)
        module_with_imports = self._get_module_with_imports(source, self.source)
        imports = [import_stmt.import_info
                   for import_stmt in module_with_imports.get_import_statements()]
        start = 1
        if module_with_imports.get_import_statements():
            start = module_with_imports.get_import_statements()[-1].end_line
        lines = rope.base.codeanalyze.SourceLinesAdapter(source)
        moving = source[lines.get_line_start(start):]
        return moving, imports

    def _get_module_with_imports(self, source_code, resource):
        pymodule = self.pycore.get_string_module(source_code, resource)
        return self.import_tools.get_module_with_imports(pymodule)

    def _get_moving_element(self):
        lines = self.pycore.resource_to_pyobject(self.source).lines
        scope = self.old_pyname.get_object().get_scope()
        start = lines.get_line_start(scope.get_start())
        end = lines.get_line_end(scope.get_end())
        moving = self.source.read()[start:end]
        return moving

    def _get_used_imports_by_the_moving_element(self):
        pymodule = self.pycore.resource_to_pyobject(self.source)
        module_with_imports = self.import_tools.get_module_with_imports(pymodule)
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


class _ModuleMover(_Mover):

    def __init__(self, pycore, pyname, destination):
        source = pyname.get_object().get_resource()
        if source.is_folder():
            old_name = source.get_name()
        else:
            old_name = source.get_name()[:-3]
        package = importutils.get_module_name(pycore, destination)
        if package:
            new_name = package + '.' + old_name
        else:
            new_name = old_name
        super(_ModuleMover, self).__init__(pycore, source, destination,
                                           pyname, old_name, new_name)
        self.new_import = importutils.NormalImport([(self.new_name, None)])

    def _check_exceptional_conditions(self):
        moving_pyobject = self.old_pyname.get_object()
        if not self.destination.is_folder():
            raise rope.base.exceptions.RefactoringException(
                'Move destination for modules should be packages.')

    def move(self):
        changes = ChangeSet()
        self._change_other_modules(changes)
        self._change_moving_module(changes)
        return changes

    def _change_moving_module(self, changes):
        if not self.source.is_folder():
            is_changed = False
            pymodule = self.pycore.resource_to_pyobject(self.source)
            source = self.import_tools.transform_relative_imports_to_absolute(pymodule)
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
                                        self.destination.get_path()))

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

