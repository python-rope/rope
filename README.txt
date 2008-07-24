========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

* inline variable can now inline variable in other modules
* handling only_current option for inline in other modules
* better extension module handling
* added `rope.contrib.findit.find_definition()`
* added `rope.contrib.changestack` module to perform many refactorings
  as a single command
* added `rope.contrib.fixmodnames` for fixing module and package names
* added `rope.contrib.finderrors` module for finding bad name and
  attribute accesses
* added ``region`` field to `rope.contrib.findit.Location`
* added ``remove_self`` argument to `codeassist.get_calltip()`


Inline Refactoring Enhancements
-------------------------------

Inline variable can now inline variables in other (the ones not
containing the definition) modules.  It adds import to changed modules
when needed.

One problem for inline refactoring is from-imports.  If a name is
imported as ``from mod import f`` then after removing the definition
of `f`, these imports should be removed; rope does this now.

Also ``only_current`` option of inline didn't work in other modules;
it was fixed.

`rope.contrib.changestack`
--------------------------

`changestack` module can be used to perform many refactorings on top
of each other as one bigger command.  It can be used like::

  stack = ChangeStack(project, 'my big command')

  #..
  stack.push(refactoring1.get_changes())
  #..
  stack.push(refactoring2.get_changes())
  #..
  stack.push(refactoringX.get_changes())

  stack.pop_all()
  changes = stack.merged()

Now `changes` can be previewed or performed as before.

`rope.contrib.fixmodnames`
--------------------------

This module is useful when you want to rename many of the modules in
your project.  That can happen specially when you want to change their
naming style.

For instance::

  fixmods = FixModuleNames(project)
  changes = fixmods.get_changes(fixer=str.lower)
  project.do(changes)

renames all modules and packages to use lower-cased chars.  You can
tell it to use any other style by using the ``fixer`` argument.

`rope.contrib.finderrors`
-------------------------

`find_errors` function can be used to find possible bad name and
attribute accesses.  As an example::

  errors = find_errors(project, project.get_resource('mod.py'))
  for error in errors:
      print '%s: %s' % (error.lineno, error.error)

prints possible errors for ``mod.py`` file.

Currently this module is experimental and reports many
false-positives.  Contributions are welcome.

`rope.contrib.findit.find_definition`
-------------------------------------

This function finds the definition of a name, just like the older
`rope.contrib.codeassist.get_definition_location` function.  The
difference is it returns a `findit.Location` object like other
functions is `findit` module.

Also `rope.contrib.findit.Location` has a new field called ``region``
it is a tuple that holds the start and end offset of the occurrence;
this can probably be used in IDE's that highlight locations.

Better Extension Module Handling
--------------------------------

`extension_modules` project config tells rope to import these modules
if their source code cannot be found.  Rope can now handle nested
extension modules in normal packages.


Getting Started
===============

* List of features: `docs/rope.txt`_
* Overview of some of rope's features: `docs/overview.txt`_
* Using as a library: `docs/library.txt`_
* Contributing: `docs/contributing.txt`_

To change your project preferences edit
``$PROJECT_ROOT/.ropeproject/config.py`` where ``$PROJECT_ROOT`` is
the root folder of your project (this file is created the first time
you open a project).


Bug Reports
===========

Send your bug reports and feature requests to `rope-dev (at)
googlegroups.com`_.

.. _`rope-dev (at) googlegroups.com`: http://groups.google.com/group/rope-dev


License
=======

This program is under the terms of GPL (GNU General Public License).
Have a look at ``COPYING`` file for more information.


.. _`docs/rope.txt`: docs/rope.html
.. _`docs/overview.txt`: docs/overview.html
.. _`docs/contributing.txt`: docs/contributing.html
.. _`docs/library.txt`: docs/library.html
