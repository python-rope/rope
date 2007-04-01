================================================
 rope, a python refactoring IDE and library ...
================================================


Overview
========

`rope`_ is a python refactoring IDE and library.  The IDE uses the
library to provide features like refactoring, code assist, and
auto-completion.  It is written in python.  The IDE uses `Tkinter`
library.

.. _`rope`: http://rope.sf.net/


New Features
============

* Generating python elements
* Memorizing locations and texts
* Added `.ropeproject` folder
* Saving history across sessions
* Saving object data to disk
* Incremental ObjectDB validation
* Inlining `staticmethod`\s
* Setting ignored resources patterns

Maybe the most notable change in this release is the addition of a new
folder in projects for holding configurations and other informations
for a project.  Its default name is ``.ropeproject``, but it can be
changed in ``~/.rope`` or `Project` constructor (if using rope as a
library).  You can also force rope not to make such a folder by using
`None` instead of a `str`.

Currently it is used for these perposes:

* There is a ``config.py`` file in this folder in which you can change
  project configurations.  Look at the default ``config.py`` file,
  that is created when there is none available, for more information.
  When a project is open you can edit this file using ``"Edit Project
  config.py"`` action or ``C-x p c``.
* It can be used for saving project history, so that the next time you
  open the project you can see and undo past changes.  If you're new
  to rope use ``"Project History"`` (``C-x p h``) for more
  information.
* It can be used for saving object information.  Before this release
  all object information where kept in memory.  Saving them on disk
  has two advantages.  First, rope will need less memory and second,
  the calculated and collected information is not thrown away each
  time you close a project.

You can change what to save and what not to in the ``config.py`` file.

Since files on disk change overtime project object DB might hold
invalid information.  Currently there is a basic incremental object DB
validation that can be used to remove or fix out of date information.
Rope uses this feature by default but you can disable it by editing
``config.py``.  Other interesting features related to rope's object DB
and object inference are planned for ``0.5`` release.  So if you're
interested keep waiting!

The generate element actions make python elements.  You have to move
on an element that does not exist and perform one of these generate
actions.  For example::

  my_print(var=1)

Calling generate function on `my_print` (``C-c n f``) will result in:

  def my_print(var):
      pass


  my_print(var=1)

It handle methods, static methods, classes, variables, modules, and
packages, too.  Generate element actions use ``C-c n`` prefix.

Rope can now save locations or strings in memory.  These are similar
to emacs's bookmarks and registers.  These actions use ``C-x m``
prefix.


Getting Started
===============

* Overview and keybinding: `docs/user/overview.txt`_
* List of features: `docs/index.txt`_
* Tutorial: `docs/user/tutorial.txt`_
* Using as a library: `docs/dev/library.txt`_
* Contributing: `docs/dev/contributing.txt`_

If you don't like rope's default emacs-like keybinding, edit the
default ``~/.rope`` file (created the first time you start rope) and
change `i_like_emacs` variable to `False`.


Project Road Map
================

The main motive for starting this project was the lack of good
refactoring tools for Python programming language.  Refactoring
programs like "bicycle repair man" aren't reliable due to type
inference problems and they support a limited number of refactorings.
*Rope* tries to improve these limitations.

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
