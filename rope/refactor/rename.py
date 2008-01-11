import warnings

from rope.base import exceptions, codeanalyze, pyobjects, pynames, taskhandle, evaluate
from rope.base.change import ChangeSet, ChangeContents, MoveResource
from rope.refactor import occurrences, sourceutils


class Rename(object):
    """A class for performing rename refactoring

    It can rename everything: classes, functions, modules, packages,
    methods, variables and keyword arguments.

    """

    def __init__(self, project, resource, offset=None):
        """If `offset` is None, the `resource` itself will be renamed"""
        self.project = project
        self.pycore = project.pycore
        self.resource = resource
        if offset is not None:
            self.old_name = codeanalyze.get_name_at(self.resource, offset)
            this_pymodule = self.pycore.resource_to_pyobject(self.resource)
            self.old_instance, self.old_pyname = \
                evaluate.get_primary_and_pyname_at(this_pymodule, offset)
            if self.old_pyname is None:
                raise exceptions.RefactoringError(
                    'Rename refactoring should be performed'
                    ' on resolvable python identifiers.')
        else:
            if not resource.is_folder() and resource.name == '__init__.py':
                resource = resource.parent
            dummy_pymodule = self.pycore.get_string_module('')
            self.old_instance = None
            self.old_pyname = pynames.ImportedModule(dummy_pymodule,
                                                     resource=resource)
            if resource.is_folder():
                self.old_name = resource.name
            else:
                self.old_name = resource.name[:-3]

    def get_old_name(self):
        return self.old_name

    def get_changes(self, new_name, in_file=False, in_hierarchy=False,
                    unsure=None, docs=False,
                    task_handle=taskhandle.NullTaskHandle()):
        """Get the changes needed for this refactoring

        :parameters:
            - `in_file`: if True implies only renaming occurrences in the
              passed resource.
            - `in_hierarchy`: when renaming a method this keyword forces
              to rename all matching methods in the hierarchy
            - `docs`: when `True` rename refactoring will rename
              occurrences in comments and strings where the name is
              visible.  Setting it will make renames faster, too.
            - `unsure`: decides what to do about unsure occurrences.
              If `None`, they are ignored.  Otherwise `unsure` is
              called with an instance of `occurrence.Occurrence` as
              parameter.  If it returns `True`, the occurrence is
              considered to be a match.

        """
        if unsure in (True, False):
            warnings.warn(
                'unsure parameter should be a function that returns'
                ' True or False', DeprecationWarning, stacklevel=2)
            def unsure_func(value=unsure):
                return value
            unsure = unsure_func
        old_pynames = self._get_old_pynames(in_file, in_hierarchy, task_handle)
        if not in_file and len(old_pynames) == 1 and \
           self._is_renaming_a_function_local_name():
            in_file = True
        files = self._get_interesting_files(in_file)
        changes = ChangeSet('Renaming <%s> to <%s>' %
                            (self.old_name, new_name))
        finder = occurrences.FilteredFinder(
            self.pycore, self.old_name, old_pynames, unsure=unsure, docs=docs)
        job_set = task_handle.create_jobset('Collecting Changes', len(files))
        for file_ in files:
            job_set.started_job('Working on <%s>' % file_.path)
            new_content = rename_in_module(finder, new_name, resource=file_)
            if new_content is not None:
                changes.add_change(ChangeContents(file_, new_content))
            job_set.finished_job()
        if self._is_renaming_a_module():
            self._rename_module(old_pynames[0].get_object(),
                                new_name, changes)
        return changes

    def _is_renaming_a_function_local_name(self):
        module, lineno = self.old_pyname.get_definition_location()
        if lineno is None:
            return False
        scope = module.get_scope().get_inner_scope_for_line(lineno)
        if isinstance(self.old_pyname, pynames.DefinedName) and \
           scope.get_kind() in ('Function', 'Class'):
            scope = scope.parent
        return scope.get_kind() == 'Function' and \
               self.old_pyname in scope.get_names().values() and \
               isinstance(self.old_pyname, pynames.AssignedName)

    def _is_renaming_a_module(self):
        if isinstance(self.old_pyname.get_object(), pyobjects.AbstractModule):
            return True
        return False

    def _get_old_pynames(self, in_file, in_hierarchy, handle):
        return FindMatchingPyNames(
            self.old_instance, self.old_pyname, self.old_name,
            in_file, in_hierarchy and self.is_method(), handle).get_all()

    def _get_interesting_files(self, in_file):
        if not in_file:
            return self.pycore.get_python_files()
        return [self.resource]

    def is_method(self):
        pyname = self.old_pyname
        return isinstance(pyname, pynames.DefinedName) and \
               isinstance(pyname.get_object(), pyobjects.PyFunction) and \
               isinstance(pyname.get_object().parent, pyobjects.PyClass)

    def _rename_module(self, pyobject, new_name, changes):
        resource = pyobject.get_resource()
        if not resource.is_folder():
            new_name = new_name + '.py'
        if resource.project == self.project:
            parent_path = resource.parent.path
            if parent_path == '':
                new_location = new_name
            else:
                new_location = parent_path + '/' + new_name
            changes.add_change(MoveResource(resource, new_location))


class ChangeOccurrences(object):
    """A class for changing the occurrences of a name in a scope

    This class replaces the occurrences of a name.  Note that it only
    changes the scope containing the offset passed to the constructor.
    What's more it does not have any side-effects.  That is for
    example changing occurrences of a module does not rename the
    module; it merely replaces the occurrences of that module in a
    scope with the given expression.  This class is useful for
    performing many custom refactorings.

    """

    def __init__(self, project, resource, offset):
        self.pycore = project.pycore
        self.resource = resource
        self.offset = offset
        self.old_name = codeanalyze.get_name_at(resource, offset)
        self.pymodule = self.pycore.resource_to_pyobject(self.resource)
        self.old_pyname = evaluate.get_pyname_at(self.pymodule, offset)

    def get_old_name(self):
        word_finder = codeanalyze.WordRangeFinder(self.resource.read())
        return word_finder.get_primary_at(self.offset)

    def _get_scope_offset(self):
        lines = self.pymodule.lines
        scope = self.pymodule.get_scope().\
                get_inner_scope_for_line(lines.get_line_number(self.offset))
        start = lines.get_line_start(scope.get_start())
        end = lines.get_line_end(scope.get_end())
        return start, end

    def get_changes(self, new_name, only_calls=False, reads=True, writes=True):
        changes = ChangeSet('Changing <%s> occurrences to <%s>' %
                            (self.old_name, new_name))
        scope_start, scope_end = self._get_scope_offset()
        finder = occurrences.FilteredFinder(
            self.pycore, self.old_name, [self.old_pyname],
            imports=False, only_calls=only_calls)
        new_contents = rename_in_module(
            finder, new_name, pymodule=self.pymodule, replace_primary=True,
            region=(scope_start, scope_end), reads=reads, writes=writes)
        if new_contents is not None:
            changes.add_change(ChangeContents(self.resource, new_contents))
        return changes


def rename_in_module(occurrences_finder, new_name, resource=None, pymodule=None,
                     replace_primary=False, region=None, reads=True, writes=True):
    """Returns the changed source or `None` if there is no changes"""
    if resource is not None:
        source_code = resource.read()
    else:
        source_code = pymodule.source_code
    change_collector = sourceutils.ChangeCollector(source_code)
    for occurrence in occurrences_finder.find_occurrences(resource, pymodule):
        if replace_primary and occurrence.is_a_fixed_primary():
            continue
        if replace_primary:
            start, end = occurrence.get_primary_range()
        else:
            start, end = occurrence.get_word_range()
        if (not reads and not occurrence.is_written()) or \
           (not writes and occurrence.is_written()):
            continue
        if region is None or region[0] <= start < region[1]:
            change_collector.add_change(start, end, new_name)
    return change_collector.get_changed()


class FindMatchingPyNames(object):
    """Find matching pynames

    This is useful for finding overriding and overridden methods in
    class hierarchy and attributes concluded from implicit interfaces.
    """

    def __init__(self, primary, pyname, name, in_file,
                 in_hierarchy, handle=taskhandle.NullTaskHandle()):
        self.name = name
        self.pyname = pyname
        self.instance = primary
        self.in_file = in_file
        self.in_hierarchy = in_hierarchy
        self.handle = handle

    def get_all(self):
        result = set()
        if self.pyname is not None:
            result.add(self.pyname)
        if isinstance(self.instance, pynames.ParameterName):
            for pyobject in self.instance.get_objects():
                try:
                    result.add(pyobject[self.name])
                except exceptions.AttributeNotFoundError:
                    pass
        if self.in_hierarchy:
            for pyname in set(result):
                result.update(self.get_all_methods_in_hierarchy(
                              self.pyname.get_object().parent, self.name))
        return list(result)

    def get_all_methods_in_hierarchy(self, pyclass, attr_name):
        superclasses = self._get_superclasses_defining_method(pyclass,
                                                              attr_name)
        methods = set()
        for superclass in superclasses:
            methods.update(self._get_all_methods_in_subclasses(
                           superclass, attr_name))
        return methods

    def _get_superclasses_defining_method(self, pyclass, attr_name):
        result = set()
        for superclass in pyclass.get_superclasses():
            if attr_name in superclass:
                result.update(self._get_superclasses_defining_method(
                              superclass, attr_name))
        if not result:
            return set([pyclass])
        return result

    def _get_all_methods_in_subclasses(self, pyclass, attr_name):
        result = set([pyclass[attr_name]])
        for subclass in pyclass.pycore.get_subclasses(pyclass, self.handle):
            result.update(self._get_all_methods_in_subclasses(subclass, attr_name))
        return result
