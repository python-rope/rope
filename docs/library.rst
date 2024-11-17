=========================
 Using Rope As A Library
=========================

If you need other features, send a feature request.  Have a look at
:ref:`contributing:Contributing to Rope`.


.. contents:: Table of Contents


Quick Start
===========

This section will help you get started as soon as possible.


Making A Project
----------------

The first thing you should do is make a project:

.. code-block:: python

  import rope.base.project


  myproject = rope.base.project.Project('/path/to/myproject')

It's good to know that:

* A project is a folder in the file-system.
* It can contain anything.
* Rope searches for python modules and packages inside a project when
  needed.
* Refactorings only change files and folders inside the project that
  has been passed to them.
* Out of project modules that are imported from a module inside a
  project are handled but never changed by refactorings.
* Rope makes a rope folder inside projects.  By default the name of this
  folder is ``.ropeproject``, but that can be changed using the
  constructor's ``ropefolder`` parameter. Passing ``None`` prevents rope
  from making this folder.
* Rope uses the ``.ropeproject`` folder for things like saving object
  information and loading project configurations.
* Project preferences can be configured by passing options to the
  constructor or in ``.ropeproject/config.py``.  See the default
  ``config.py``, ``rope.base.default_config`` module, for more
  information.
* All configurations that are available in the ``config.py`` file can
  be specified as keyword parameters to the ``Project`` constructor.
  These parameters override the ones in the ``config.py`` file.
* Each project has a set of ignored resource patterns. You can use it
  to tell rope to ignore files and folders matching certain patterns.
* The ``.ropeproject`` folder can be safely copied in other clones of
  a project if you don't want to lose your objectdb and history.


Library Utilities
-----------------

The `rope.base.libutils`_ module provides tools that make using rope as a
library easier.  We'll talk more about this module later.


What Are These `Resource`\s?
----------------------------

In rope, files and folders in a project are accessed through
``rope.base.resources.Resource`` objects.  It has two subclasses
``File`` and ``Folder``.  What we care about is that refactorings and
``Change``\s (we'll talk about them later) use resources.

There are two options for creating a ``Resource`` for a path in a project.
The first approach uses the ``Project.get_resource()`` method.

.. code-block:: python

  from rope.base import project


  myresource = myproject.get_resource('/path/to/resource')

However, it's preferable to use the ``libutils.path_to_resource()``
function, because it's more flexible and offers a unified way to create
resources.  It takes a ``project`` and ``path`` as parameters with an
optional ``type``.  The ``type`` parameter, with values ``file`` or
``folder``, can create a resource for an object that doesn't exist yet.

.. code-block:: python

  from rope.base import libutils


  myresource = libutils.path_to_resource(myproject, '/path/to/resource')


Consider we have a resource.  How can we know anything about it? The
answer is to use its ``path`` and ``real_path`` attributes.
``Resource.real_path`` is the absolute path of the resource in the
file-system.  The ``Resource.path`` attribute contains the address of a
resource relative to the project's root.


Performing Refactorings
-----------------------

As a short example of performing refactorings, we'll show how to extract
a variable from a file.  First we need the ``Resource`` object that
points to a file in a project:

.. code-block:: python

  resource = libutils.path_to_resource(myproject, '/path/to/my/module.py')

Now we can make our Refactoring class:

.. code-block:: python

  from rope.refactor.extract import ExtractVariable


  extractor = ExtractVariable(myproject, resource, start, end)

Where ``start`` and ``end`` are the offsets of the region to extract in
``resource``.  Be careful when calculating the offsets.  DOS
line-endings and multi-byte characters are considered to be one
character.  This is actually easier for IDEs, since most GUI libraries
handle those cases for you.

Next, the IDE ask the user to configure refactoring options, like
specifying the name of the extracted variable.

After that, we can calculate the changes:

.. code-block:: python

  changes = extractor.get_changes('extracted_variable')

Each refactoring returns a ``rope.base.change.Change`` object that holds
the changes it made.  Calculating those changes can be time consuming.
See the `rope.base.taskhandle.TaskHandle`_ section for measuring its
progress or interrupting it.


Previewing And Performing Changes
---------------------------------

As mentioned in the last section each refactoring returns a
``rope.base.change.Change`` object.  Now how can we know what it
contains and how to perform it?

*Previewing*:

You can use ``changes.get_description()`` to get a preview. It is useful
when you don't care much about the format.  Otherwise you can use the
``changes`` object directly.  See the documentation in
``rope.base.change`` module.

*Performing*:

The easiest way for performing the refactoring is to use the
`Project.do()`_ method:

.. code-block:: python

  myproject.do(changes)

If you want to perform the changes yourself, you have two options.
Note that the main reason for performing the changes manually is
handling version control systems that are not supported by rope.

1. The first approach is to use `rope.base.fscommands`_ (see `Writing A
   FileSystemCommands`_).  The changes can be performed as before using
   `Project.do()`_.

2. The second approach is to perform the changes manually based on the
   returned ``changes`` object (again see the documentation in
   ``rope.base.change`` module).  If this approach is used you cannot undo
   the refactoring using ``project.history.undo()``.

*Updating Open Buffers In IDEs*:

Usually editors need to reload the files changed by rope.  You can use
``Change.get_changed_resources()`` to get the list of resources that
need to be reloaded.


Validating The Project
----------------------

When using rope as a library, you probably change the files in it in
parallel (for example in IDEs).  To force rope to invalidate cached
information about resources that have been removed or changed outside
rope, you should call the `Project.validate()`_ method.  You can pass a
resource to this method.  For example:

.. code-block:: python

  myproject.validate(resource)

This validates all files and directories in resource.  Call this
function every time you want use rope (i.e., before performing
refactorings).


Performing Static Object Analysis
---------------------------------

One of the greatest strengths of rope is its Static Object Analysis
(SOA). It analyzes function calls and assignments to collect the types
of objects passed to the function. Rope uses the collected data to infer
the type of function parameters, return values, and the objects stored
in built-in containers. The function
``rope.base.libutils.analyze_modules()`` performs SOA on all modules in
the project. It is recommended that you call this function occasionally,
and especially before performing large refactorings. Note that analyzing
all modules of a project may take a long time.

If you have ``automatic_soa`` set, which instructs rope to analyze the
changed scopes of modules, then you should report the changes by calling
``rope.base.libutils.report_change()`` when saving files, as follows:

.. code-block:: python

  # Save the new contents.
  old_contents = resource.read()
  resource.write(new_contents)

  # Inform rope about the change.
  libutils.report_change(myproject, path, old_contents)

Note, however, that the use of ``automatic_soa`` is discouraged, because it may
slow down saving considerably.


Closing The Project
-------------------

`Project.close()`_ closes a project's open resources.  Always call this
function when you don't need a project anymore:

.. code-block:: python

  myproject.close()


``rope.base.libutils``
======================

The ``rope.base.libutils`` module contains functions that make life
easier for building refactoring tools. In some cases, the functions
offer a unified way to access or create objects. You're encouraged to
use ``rope.base.libutils`` functions whenever possible, because the APIs
here may not be as volatile as class methods.


``libutils.analyze_module()``
------------------------------

Perform static object analysis on a Python file in the project. Note,
this may be a very time consuming task.

.. code-block:: python

  libutils.analyze_module(myproject, resource)


``libutils.analyze_modules()``
------------------------------

Perform static object analysis on all Python files in the project. Note
that it might take a long time to finish.

.. code-block:: python

  libutils.analyze_modules(myproject)


``libutils.get_string_module()``
--------------------------------

Returns a ``rope.base.pyobjects.PyModule`` object for the code string.
An optional ``resource`` argument can be specified for the resource this
code is associated with. If ``force_errors`` is ``True``, then
``rope.base.exceptions.ModuleSyntaxError`` is raised when the code has
syntax errors. Otherwise, syntax errors are silently ignored. Note that
``force_errors`` overrides the ``ignore_syntax_errors`` project
configuration flag.

.. code-block:: python

  pymodule = libutils.get_string_module(myproject, source)


``libutils.get_string_scope()``
-------------------------------

Get the ``rope.base.pyscopes.GlobalScope`` object for the code string.
This is the outermost scope of the code encompassing the whole module.

.. code-block:: python

  scope = libutils.get_string_scope(myproject, source)


``libutils.is_python_file()``
-----------------------------

Returns ``True`` if the resource is a Python file.

.. code-block:: python

  libutils.is_python_file(myproject, resource)


``libutils.modname()``
----------------------

Retrieves the dotted path string to the module that contains that given
resource.

.. code-block:: python

  # If resource is 'path/to/resource.py' relative to the project's root
  # directory, this returns the string: 'path.to.resource'.
  module_name = libutils.modname(resource)


``libutils.path_relative_to_project_root()``
--------------------------------------------

Retrieve the path relative to the project's root directory.

.. code-block:: python

  # Get the path relative to the project's root directory.
  relpath = libutils.relative(myproject.address, path)


``libutils.path_to_resource()``
-------------------------------

Get the resource --- a file or folder --- at the given path. An optional
``type`` argument can be used if the resource doesn't yet exist. The
values for ``type`` are the strings ``'file'`` or ``'folder'``.

.. code-block:: python

  # Resource for an existing file.
  myfile = libutils.path_to_resource(myproject, '/path/to/file.py')

  # Resource for a non-existing folder.
  new_folder = libutils.path_to_resource(myproject, '/path/to/folder', type='folder')


``rope.base.project.Project``
=============================

You can create a project by:

.. code-block:: python

  project = Project(root_address)

Where the ``root_address`` is the root folder of your project.

A project has some useful attributes.  ``Project.address`` is the
address of the root folder of a project.  ``Project.root`` is a
``Folder`` object that points to that folder.


`Project.do()`
--------------

Used to commit changes returned by refactorings:

.. code-block:: python

  project.do(changes)


`Project.history`
-----------------

A ``rope.base.history.History`` object.  You can use its ``undo`` and
``redo`` methods for undoing or redoing changes.  Note that you can use
this only if you have committed your changes using rope.


`Project.validate()`
--------------------

When using rope as a library, you will probably change the files in that
project in parallel (for example in IDEs).  To force rope to validate
cached information about resources that have been removed or changed
outside rope, you should call ``Project.validate()``.  You should pass a
resource to this method.  For example:

.. code-block:: python

  project.validate(project.root)

This validates all files and directories in the project and clears the
cache of all recorded changes.


`Project.close()`
-----------------

Closes a project's open resources.  Always call this function when you
don't need a project anymore.  Currently it closes the files used for
storing object information and project history.  Because some parts of
these files are in memory for efficiency, not closing a project might
put them in an inconsistent state.


`rope.base.fscommands`
======================

The ``rope.base.fscommands`` module implements basic file system
operations that rope needs to perform.  The main reason for the
existence of this module is supporting version control systems.  Have a
look at ``FileSystemCommands`` and ``SubversionCommands`` in the same
module.  If you need other version control systems you can write a new
class that provides this interface.  ``rope.base.project.Project``
accepts an ``fscommands`` argument.  You can use this argument to force
rope to use your new class.


``.ropeproject`` Folder
=======================

Since version ``0.5``, rope makes a ``.ropeproject`` folder in the
project by default for saving project configurations and data.  The name
of this folder is passed to the constructor if you want to change that.
You can force rope not to make such a folder by passing ``None``.

If such a folder exists, rope loads the ``config.py`` file in that
folder.  It might also use it for storing object information and
history.


`rope.base.pycore.PyCore`
=========================

Provides useful methods for managing python modules and packages.  Each
project has a ``PyCore`` that can be accessed using the
``Project.pycore`` attribute.

``PyCore.run_module()`` runs a resource.  When running, it collects type
information to do dynamic object inference.  For this reason modules
run much slower.

Also ``Pycore.analyze_module()`` collects object information for a
module.  The collected information can be used to enhance rope's
static object inference.


`rope.base.taskhandle.TaskHandle`
=================================

A TaskHandle can be used for stopping and monitoring the progress of
time consuming tasks, like some refactorings.  The ``Project.do()`` and
``Refactoring.get_changes()`` methods for most refactorings take a
keyword parameter called ``task_handle``.  You can pass a ``TaskHandle``
object to them.  A ``TaskHandle`` can be used for interrupting or
observing a task.

Always pass ``task_handle`` as keyword argument.  It will always be the
last argument, and new arguments of the refactoring are added before it.

A task might consist of a few ``JobSet``\s.  Each ``JobSet`` performs a
few jobs.  For instance calculating the changes for renaming a method in
a class hierarchy has two job sets: one to find the classes for
constructing the class hierarchy and another to change the occurrences.

The ``TaskHandle.current_jobset()`` returns the most recent ``JobSet``
or ``None`` if none has been started.  You can use the methods of
``JobSet`` for obtaining information about the current job.  So you
might want to do something like:

.. code-block:: python

  import rope.base.taskhandle


  handle = rope.base.taskhandle.TaskHandle("Test Task")

  def update_progress():
      jobset = handle.current_jobsets()
      if jobset:
          text = ''
          # getting current job set name
          if jobset.get_name() is not None:
              text += jobset.get_name()
          # getting active job name
          if jobset.get_active_job_name() is not None:
              text += ' : ' + jobset.get_active_job_name()
          # adding done percent
          percent = jobset.get_percent_done()
          if percent is not None:
              text += ' ... %s percent done' % percent
          print(text)

  handle.add_observer(update_progress)

  changes = renamer.get_changes('new_name', task_handle=handle)

Also you can use something like this for stopping the task:

.. code-block:: python

  def stop():
      handle.stop()

After calling ``stop()``, the thread that is executing the task will
be interrupted by a ``rope.base.exceptions.InterruptedTaskError``
exception.


Refactorings
============

Have a look at ``rope.refactor`` package and its sub-modules.  For
example for performing a move refactoring you can create an object
representing this operation (which will be an instance of e.g.
`MoveMethod`, `MoveModule`, ...) like this:

.. code-block:: python

  from rope.refactor.move import create_move

  mover = create_move(project, resource, offset)

Where ``resource`` and ``offset`` is the location to perform the
refactoring.

Then you can commit the changes by it using the ``get_changes()``
method:

.. code-block:: python

  project.do(mover.get_changes(destination))

Where the ``destination`` module/package is the destination resource for
move refactoring.  Other refactorings classes have a similar interface.


List Of Refactorings
--------------------

Here is the list of refactorings rope provides.  (Note that this list
might be out of date.)  For more information about these refactoring see
pydocs in their modules and the unit-tests in the ``ropetest/refactor/``
folder.

* ``rope.refactor.rename``:
  Rename something in the project.  See the example below.

* ``rope.refactor.move``:
  Move a python element in the project.

* ``rope.refactor.restructure``:
  Restructure code.  See the example below.

* ``rope.refactor.extract``:
  Extract methods/variables.

* ``rope.refactor.inline``:
  Inline occurrences of a method/variable/parameter.

* ``rope.refactor.usefunction``:
  Try to use a function wherever possible.

* ``rope.refactor.method_object``:
  Transform a function or a method to a method object.

* ``rope.refactor.change_signature``:
  Change the signature of a function/method.

* ``rope.refactor.introduce_factory``:
  Introduce a factory for a class and changes all constructors to use
  it.

* ``rope.refactor.introduce_parameter``:
  Introduce a parameter in a function.

* ``rope.refactor.encapsulate_field``:
  Generate a getter/setter for a field and changes its occurrences to
  use them.

* ``rope.refactor.localtofield``:
  Change a local variable to field.

* ``rope.refactor.topackage``:
  Transform a module to a package with the same name.

* ``rope.refactor.importutils``:
  Perform actions like organize imports.


Refactoring Resources Parameter
-------------------------------

Some refactorings, restructure and find occurrences accept an argument
called ``resources``.  If it is a list of `File`\s, all other
resources in the project are ignored and the refactoring only analyzes
them. If it is ``None`` all python modules in the project will be
analyzed.  Using this parameter, IDEs can let the user limit the files
on which a refactoring should be applied.


Examples
========

Rename
------

Using rename refactoring:

.. code-block:: python

  # Creating a project
  >>> from rope.base.project import Project
  >>> project = Project('.')

  # Working with files to create a module
  >>> mod1 = project.root.create_file('mod1.py')
  >>> mod1.write('a_var = 10\n')

  # Alternatively you can use `generate` module.
  # Creating modules and packages using `generate` module
  >>> from rope.contrib import generate
  >>> pkg = generate.create_package(project, 'pkg')
  >>> mod2 = generate.create_module(project, 'mod2', pkg)
  >>> mod2.write('import mod1\nprint(mod1.a_var)\n')

  # We can use `Project.find_module` for finding modules, too
  >>> assert mod2 == project.find_module('pkg.mod2')

  # Performing rename refactoring on `mod1.a_var`
  >>> from rope.refactor.rename import Rename
  >>> changes = Rename(project, mod1, 1).get_changes('new_var')
  >>> project.do(changes)
  >>> mod1.read()
  u'new_var = 10\n'
  >>> mod2.read()
  u'import mod1\nprint(mod1.new_var)\n'

  # Undoing rename refactoring
  >>> project.history.undo()
  ...
  >>> mod1.read()
  u'a_var = 10\n'
  >>> mod2.read()
  u'import mod1\nprint(mod1.a_var)\n'

  # Cleaning up
  >>> pkg.remove()
  >>> mod1.remove()
  >>> project.close()


Restructuring
-------------

The example for replacing occurrences of our ``pow`` function to ``**``
operator (see ref:`overview:Restructurings`):

.. code-block:: python

  # Setting up the project
  >>> from rope.base.project import Project
  >>> project = Project('.')

  >>> mod1 = project.root.create_file('mod1.py')
  >>> mod1.write('def pow(x, y):\n    result = 1\n'
  ...            '    for i in range(y):\n        result *= x\n'
  ...            '    return result\n')
  >>> mod2 = project.root.create_file('mod2.py')
  >>> mod2.write('import mod1\nprint(mod1.pow(2, 3))\n')

  >>> from rope.refactor import restructure

  >>> pattern = '${pow_func}(${param1}, ${param2})'
  >>> goal = '${param1} ** ${param2}'
  >>> args = {'pow_func': 'name=mod1.pow'}

  >>> restructuring = restructure.Restructure(project, pattern, goal, args)

  >>> project.do(restructuring.get_changes())
  >>> mod2.read()
  u'import mod1\nprint(2 ** 3)\n'

  # Cleaning up
  >>> mod1.remove()
  >>> mod2.remove()
  >>> project.close()


See code documentation and test suites for more information.


Other Topics
============


Writing A `FileSystemCommands`
------------------------------

The ``get_changes()`` method of refactoring classes return a
``rope.base.change.Change`` object.  You perform these changes by
calling ``Project.do()``.  But as explained above some IDEs need to
perform the changes themselves.

Every change to the file-system in rope is committed using an object that
provides a ``rope.base.fscommands.FileSystemCommands`` interface.  As
explained above in `rope.base.fscommands`_ section, rope uses this
interface to handle different VCSs.

You can implement your own fscommands object:

.. code-block:: python

  class MyFileSystemCommands(object):

    def create_file(self, path):
        """Create a new file"""
        # ...

    def create_folder(self, path):
        """Create a new folder"""
        # ...

    def move(self, path, new_location):
        """Move resource at `path` to `new_location`"""
        # ...

    def remove(self, path):
        """Remove resource"""
        # ...

    def write(self, path, data):
        """Write `data` to file at `path`"""
        # ...

    def read(self, path):
        """Read `data` from file at `path`"""
        # ...

And you can create a project like this:

.. code-block:: python

  my_fscommands = MyFileSystemCommands()
  project = rope.base.project.Project('~/myproject',
                                      fscommands=my_fscommands)


`rope.contrib.codeassist`
-------------------------

The ``rope.contrib`` package contains modules that use rope base parts
and provide useful features.  ``rope.contrib.codeassist`` module can be
used in IDEs:

.. code-block:: python

  from rope.ide import codeassist


  # Get the proposals; you might want to pass a Resource
  proposals = codeassist.code_assist(project, source_code, offset)

  # Sorting proposals; for changing the order see pydoc
  proposals = codeassist.sorted_proposals(proposals)

  # Where to insert the completions
  starting_offset = codeassist.starting_offset(source_code, offset)

  # Applying a proposal
  proposal = proposals[x]
  replacement = proposal.name

  new_source_code = (source_code[:starting_offset] +
                     replacement + source_code[offset:])

``maxfixes`` parameter of ``code_assist`` decides how many syntax errors
to fix.  The default value is one.  For instance:

.. code-block:: python

  def f():
      g(my^

  myvariable = None

  def g(p):
      invalid syntax ...

will report ``myvariable``, only if ``maxfixes`` is greater than 1.

``later_locals``, if ``True``, forces rope to propose names that are
defined later in current scope.  It is ``True`` by default.  For
instance:

.. code-block:: python

  def f():
      my^
      myvariable = None

will not report ``myvariable``, if ``later_locals`` is ``False``.

See pydocs and source code for more information (other functions in
this module might be interesting, too; like ``get_doc``,
``get_definition_location``).


`rope.contrib.findit`
---------------------

``findit`` module provides ``find_occurrences()`` for finding
occurrences of a name.  Also the ``find_implementations()`` function
finds the places in which a method is overridden.


`rope.contrib.autoimport`
-------------------------

This module can be used to find the modules that provide a name.  IDEs
can use this module to auto-import names.  ``AutoImport.get_modules()``
returns the list of modules with the given global name.
``AutoImport.import_assist()`` tries to find the modules that have a
global name that starts with the given prefix.


There are currently two implementations of autoimport in rope, a deprecated
implementation that uses pickle-based storage
(rope.contrib.autoimport.pickle.AutoImport) and a new, experimental one that
uses sqlite3 database (rope.contrib.autoimport.sqlite.AutoImport). New and
existing integrations should migrate to the sqlite3 storage as the pickle-based
autoimport will be removed in the future.


`rope.contrib.autoimport.sqlite`
--------------------------------

Currently, the sqlite3-based only stores autoimport cache in an in-memory
sqlite3 database, you can make it write the import cache to persistent storage
by passing memory=False to AutoImport constructor. This default will change in
the future, if you want to always store the autoimport cache in-memory, then
you need to explicitly pass memory=True.

It must be closed when done with the ``AutoImport.close()`` method.

AutoImport can search for a name from both modules and statements you can import from them.

.. code-block:: python

  from rope.base.project import Project
  from rope.contrib.autoimport import AutoImport

  project = Project("/path/to/project")
  autoimport = AutoImport(project, memory=False)
  autoimport.generate_resource_cache()  # Generates a cache of the local modules, from the project you're working on
  autoimport.generate_modules_cache()  # Generates a cache of external modules
  print(autoimport.search("Dict"))
  autoimport.close()
  project.close()

It provides two new search methods:
 -  search_full() - returns a list of mostly unsorted tuples. This has itemkind and source information.
 -  search() - simpler wrapper around search_full with a basic sorting algorithm


Cross-Project Refactorings
--------------------------

``rope.refactor.multiproject`` can be used to perform a refactoring
across multiple projects.

Usually refactorings have a main project.  That is the project that
contains the definition of the changing python name.  Other projects
depend on the main one, and the uses of the changed name in them should
be updated.

Each refactoring changes only one project (the project passed to its
constructor).  But we can use the ``MultiProjectRefactoring`` proxy to
perform a refactoring on other projects, too.

First we need to create a multi-project refactoring constructor.  As
an example consider that we want to perform a rename refactoring:

.. code-block:: python

  from rope.refactor import multiproject, rename


  CrossRename = multiproject.MultiProjectRefactoring(rename.Rename,
                                                     projects)


Here ``projects`` is the list of dependent projects.  It does not
include the main project.  The first argument is the refactoring class
(such as ``Rename``) or factory function (like ``create_move``).

Next we can construct the refactoring:

.. code-block:: python

  renamer = CrossRename(project, resource, offset)

We create the rename refactoring as we do for normal refactoings.  Note
that ``project`` is the main project.

As mentioned above, other projects use the main project. Rope
automatically adds the main project to the python path of other
projects.

Finally we can calculate the changes.  But instead of calling
``get_changes()`` (which returns main project changes only), we can
call ``get_all_changes()`` with the same arguments.  It returns a list
of ``(project, changes)`` tuples.  You can perform them manually by
calling ``project.do(changes)`` for each tuple, or use
``multiproject.perform()``:

.. code-block:: python

  project_and_changes = renamer.get_all_changes('newname')

  multiproject.perform(project_and_changes)
