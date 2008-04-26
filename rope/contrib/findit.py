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
    result = []
    for resource in resources:
        job_set.started_job('Working On <%s>' % resource.path)
        for occurrence in finder.find_occurrences(resource):
            location = Location()
            location.resource = resource
            location.offset = occurrence.get_word_range()[0]
            location.unsure = occurrence.is_unsure()
            result.append(location)
        job_set.finished_job()
    return result


class Location(object):

    resource = None
    offset = None
    unsure = False
