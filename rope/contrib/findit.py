import rope.base.codeanalyze
import rope.base.evaluate
from rope.base import taskhandle
from rope.refactor import occurrences


def find_occurrences(project, resource, offset, unsure=False, resources=None,
                     in_hierarchy=False, task_handle=taskhandle.NullTaskHandle()):
    """Return a list of `Location`\s

    If `unsure` is `True`, possible matches are returned, too.  You
    can use `Location.unsure` to see which are unsure occurrences.
    `resources` can be a list of `rope.base.resource.File`\s that
    should be searched for occurrences; if `None` all python files
    in the project are searched.

    """
    name = rope.base.codeanalyze.get_name_at(resource, offset)
    this_pymodule = project.pycore.resource_to_pyobject(resource)
    primary, pyname = rope.base.evaluate.get_primary_and_pyname_at(
        this_pymodule, offset)
    def is_match(occurrence):
        return unsure
    finder = occurrences.create_finder(
        project.pycore, name, pyname, unsure=is_match,
        in_hierarchy=in_hierarchy, instance=primary)
    if resources is None:
        resources = project.pycore.get_python_files()
    job_set = task_handle.create_jobset('Finding Occurrences',
                                        count=len(resources))
    return _find_locations(finder, resources, job_set)


def find_implementations(project, resource, offset, resources=None,
                         task_handle=taskhandle.NullTaskHandle()):
    """Find the places a given method is overridden.

    Finds the places a method is implemented.  Returns a list of
    `Location`\s.

    """
    name = rope.base.codeanalyze.get_name_at(resource, offset)
    this_pymodule = project.pycore.resource_to_pyobject(resource)
    pyname = rope.base.evaluate.get_pyname_at(this_pymodule, offset)
    def is_defined(occurrence):
        if not occurrence.is_defined():
            return False
    def not_self(occurrence):
        if occurrence.get_pyname().get_object() == pyname.get_object():
            return False
    filters = [is_defined, not_self, occurrences.InHierarchyFilter(pyname)]
    finder = occurrences.Finder(project.pycore, name, filters=filters)
    if resources is None:
        resources = project.pycore.get_python_files()
    job_set = task_handle.create_jobset('Finding Implementations',
                                        count=len(resources))
    return _find_locations(finder, resources, job_set)


class Location(object):

    resource = None
    offset = None
    unsure = False


def _find_locations(finder, resources, job_set):
    result = []
    for resource in resources:
        job_set.started_job(resource.path)
        for occurrence in finder.find_occurrences(resource):
            location = Location()
            location.resource = resource
            location.offset = occurrence.get_word_range()[0]
            location.unsure = occurrence.is_unsure()
            result.append(location)
        job_set.finished_job()
    return result
