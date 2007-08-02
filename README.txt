================================================
 rope, a python refactoring IDE and library ...
================================================


Overview
========

`rope`_ is a python refactoring library and IDE.  The IDE uses the
library to provide features like refactoring, code assist, and
auto-completion.  It is written in python.  The IDE uses `Tkinter`
library.

Rope IDE and library are released in two separate packages.  *rope*
package contains only the library and *ropeide* package contains the
IDE and the library.

.. _`rope`: http://rope.sf.net/


New Features
============

*


Getting Started
===============

* Overview and keybinding: `docs/overview.txt`_
* List of features: `docs/index.txt`_
* Tutorial: `docs/tutorial.txt`_
* Using as a library: `docs/library.txt`_
* Contributing: `docs/contributing.txt`_

To change rope IDE preferences edit your ``~/.rope`` (which is created
the first time you start rope).  To change your project preferences
edit ``$PROJECT_ROOT/.ropeproject/config.py`` where ``$PROJECT_ROOT``
is the root folder of your project (this file is created the first
time you open a project).

If you don't like rope's default emacs-like keybinding, edit the
default ``~/.rope`` file and change `i_like_emacs` variable to
`False`.


Project Road Map
================

The main motive for starting this project was the lack of good
refactoring tools for Python programming language.  Refactoring
programs like "bicycle repair man" aren't reliable due to type
inference problems and they support a limited number of refactorings.
*Rope* tries to improve these limitations.

The main goal of *rope* is to concentrate on the type inference and
refactoring of python programs and not a state of art IDE (at least
not in the first phase).  The type inference and refactoring parts
will not be dependent on *rope* IDE and if successful, will be
released as standalone programs and libraries so that other projects
may use them.


Get Involved!
=============

See `docs/contributing.txt`_.


Bug Reports
===========

Send your bug reports and feature requests in *rope*'s sourceforge.net
project page at http://sf.net/projects/rope.


License
=======

This program is under the terms of GPL (GNU General Public License).
Have a look at ``COPYING`` file for more information.


.. _`docs/overview.txt`: docs/overview.html
.. _`docs/tutorial.txt`: docs/tutorial.html
.. _`docs/index.txt`: docs/index.html
.. _`docs/contributing.txt`: docs/contributing.html
.. _`docs/library.txt`: docs/library.html
