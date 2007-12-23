# The default ``config.py``


def set_prefs(prefs):
    """This function is called before the project is opened"""

    # Specify which files and folders to ignore in the project.
    # Changes to ignored resources are not added to the history and
    # VCSs.  Also they are not shown in "Find File" dialog.
    prefs['ignored_resources'] = ['*.pyc', '*~', '.ropeproject', '.svn', '.hg']

    # Custom source folders:  By default rope searches the project
    # for finding source folders (folders that should be searched
    # for finding modules).  You can add paths to that list.  Note
    # that rope guesses project source folders correctly most of the
    # time; use this if you have any problems.
    # The folders should be relative to project root and use '/' for
    # separating folders regardless of the platform rope is running on.
    # 'src/my_source_folder' for instance.
    #prefs.add('source_folders', 'src')

    # You can extend python path:
    #prefs.add('python_path', '~/python/')

    # Should rope save object information or not.
    prefs['save_objectdb'] = True
    prefs['compress_objectdb'] = False

    # Shows whether to save history across sessions.  Defaults to
    # `False`.
    prefs['save_history'] = True
    prefs['max_history_items'] = 32
    prefs['compress_history'] = False

    # If `False` when running modules or unit tests "Dynamic Object
    # Inference" is turned off.  This makes them much faster.  The
    # default is `True`.
    prefs['perform_doi'] = True

    # Rope can test the validity of its object DB when running.  You
    # can turn this feature off by using `False`.  Defaults to
    # `True`.
    prefs['validate_objectdb'] = True

    # If `True`, rope will analyze each module when it is saved.
    prefs['automatic_soi'] = True

    # Set the number spaces used for indenting.  According to
    # :PEP:`8`, it is best to use 4 spaces.  Since most of rope's
    # unit-tests use 4 spaces it is more reliable, too.
    prefs['indent_size'] = 4

    # If `True` modules with syntax errors are considered to be empty.
    # The default value is `False`; When `False` syntax errors raise
    # `rope.base.exceptions.ModuleSyntaxError` exception.
    prefs['ignore_syntax_errors'] = False


def project_opened(project):
    """This function is called after the project is opened"""
    # Do whatever you like here!
