"""A few useful functions for using rope as a library"""
import os.path

import rope.base.project
import rope.base.pycore


def path_to_resource(project, path, type=None):
    """Get the resource at path

    You only need to specify `type` if `path` does not exist.  It can
    be either 'file' or 'folder'.  If the type is `None` it is assumed
    that the resource already exists.

    Note that this function uses `Project.get_resource()`,
    `Project.get_file()`, and `Project.get_folder()` methods.

    """
    path = rope.base.project._realpath(path)
    project_path = path
    if path == project.address or path.startswith(project.address + os.sep):
        project_path = path[len(project.address):].lstrip('/' + os.sep)
    else:
        project = rope.base.project.get_no_project()
    if type is None:
        return project.get_resource(project_path)
    if type == 'file':
        return project.get_file(project_path)
    if type == 'folder':
        return project.get_folder(project_path)
    return None


def report_change(project, path, old_content):
    """Report that the contents of file at `path` was changed

    The new contents of file is retrieved by reading the file.

    """
    resource = path_to_resource(project, path)
    if resource is None:
        return
    for observer in list(project.observers):
        observer.resource_changed(resource)
    if project.pycore.automatic_soa:
        rope.base.pycore.perform_soi_on_changed_scopes(project, resource,
                                                       old_content)
