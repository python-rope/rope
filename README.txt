================================================
 rope, a python refactoring IDE and library ...
================================================


Overview
========

`rope`_ is a python refactoring IDE and library.  Its main goal is to
provide features like refactoring, auto-completion, code assist and
outline views.  It is written in python and uses Tkinter library.

.. _`rope`: http://rope.sf.net/


New Features
============

Features added in this release:

* Project History; Undoing refactorings in any order
* Handling ``global`` keywords
* Undoing everything
* Removing `PythonRefactoring` facade
* Basic ``lambda`` handling
* Handling builtin `property`

The "Undo/Redo Refactoring" menu item has been removed from refactor
menu.  Instead a new "Undo/Redo Project Change" has been added to the
edit menu.  The new actions undo every change to a project; like saving
files, creating files and folders and refactorings.  Also a "Project
History" action has been added to edit menu.  In its dialog you can
see and select changes to be undone in any order.  Note that undoing
changes in project history undoes the changes it depends on, too.

`rope.refactor.PythonRefactoring` facade has been removed.  You can
use `rope.refactor` sub-modules for performing refactorings.  Also
you can commit the changes using `Project.do()`.  Also the
`Project.history` has been added for undoing and redoing changes.


Getting Started
===============

* Overview and keybinding: `docs/user/overview.txt`_
* List of features: `docs/index.txt`_
* Tutorial: `docs/user/tutorial.txt`_
* Using as a library: `docs/dev/library.txt`_
* Contributing: `docs/dev/contributing.txt`_


Project Road Map
================

The main motive for starting this project was the lack of good
refactoring tools for python language.  Refactoring programs like
"bicycle repair man" aren't reliable due to type inference problems
and they support a limited number of refactorings.  *Rope* tries to
improve these limitations.

* Why an IDE and not a standalone library or program?

As Don Roberts one of the writers of the "Refactoring Browser" for
smalltalk writes in his doctoral thesis:

  "An early implementation of the Refactoring Browser for Smalltalk
  was a separate tool from the standard Smalltalk development tools.
  What we found was that no one used it.  We did not even use it
  ourselves.  Once we integrated the refactorings directly into the
  Smalltalk Browser, we used them extensively."

The main goal of *rope* is to concentrate on the type inference and
refactoring of python programs and not a state of art IDE (At least
not in the first phase).  The type inference and refactoring parts
will not be dependent on *rope* IDE and if successful, will be
released as standalone programs and libraries so that other projects
may use them.


Get Involved!
=============

See `docs/dev/contributing.txt`_.


Bug Reports
===========

Send your bug reports and feature requests in *rope*'s sourceforge.net
project page at http://sf.net/projects/rope.


License
=======

This program is under the terms of GPL(GNU General Public License).
Have a look at ``COPYING`` file for more information.


.. _`docs/user/overview.txt`: docs/user/overview.html
.. _`docs/user/tutorial.txt`: docs/user/tutorial.html
.. _`docs/index.txt`: docs/index.html
.. _`docs/dev/contributing.txt`: docs/dev/contributing.html
.. _`docs/dev/library.txt`: docs/dev/library.html

