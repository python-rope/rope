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

New features since 0.4:

Core:

* Moving methods
* Replace method with method object
* Renaming occurrences in strings and comments
* Stoppable refactorings
* Automatic SOI analysis
* Basic implicit interfaces
* Performing change signature in class hierarchies
* Change occurrences
* Saving history across sessions
* Saving object data to disk
* Enhanced static object inference
* Adding ``rename when unsure`` option
* Holding per name information for builtin containers
* Adding ``.ropeproject`` folder
* Supporting generator functions
* Handling ``with`` statements

IDE and UI:

* Generating python elements; ``C-c n ...``
* Spell-checker; ``M-$`` and ``C-x $ ...``
* Saving locations and texts; ``C-x m ...``
* Open Type; ``C-x C-t``
* Showing current file history; ``C-x p 1 h``
* Registering templates in ``~/.rope``
* Filling paragraphs in text modes; ``M-q``
* Yanking; ``M-y``
* Repeating last command; ``C-x z``
* Showing annotations(codetag/error/warning list); ``C-c a ...``
* Auto-completing function keyword arguments when calling
* Execute command; ``M-x``
* Changing editor font and keybinding in ``~/.rope``
* Having two keybindings emacs/normal
* Removing extra spaces and lines; ``C-c C-f``


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
