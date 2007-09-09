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

Base changes:

* Performing import actions on individual imports
* Changing inline and move to use froms for back imports
* An option for not removing the definition after inlining
* Fixed matching method implicit argument when extracting

UI changes:

* ``C-u`` action prefix
* Setting statusbar, menu and bufferlist fonts in ``~/.rope``
* Using ``/``\s to match parent folders in find file
* Better kill line

You can invoke actions with a prefix (``C-u`` by default).  For
instance sort scopes actions were changed so that you can sort in the
reverse order by using this prefix.

You can perform import actions on individual imports by using action
prefix.  For instance for expanding an star import just move to that
line and use ``C-u C-c i x``.

A piece of code might use names from its module.  When moving code in
inline or move refactorings, rope adds back imports for importing used
names.  Before this release, rope used to convert all moving imports
(back imports plus used imports in the source module) to normal
imports.  That made imported names long.  Now rope uses from imports
for back imports to prevent that.

In the find file dialog, you can use ``/``\s to match parent folders.
For instance for opening ``rope/base/__init__.py`` you can use
``base/__init__.py`` or ``ba*/__``.

Kill line has been changed to append to the last item in the kill ring
(instead of appending to the ring) when the last action was a kill
line, too.


Getting Started
===============

* Overview and keybinding: `docs/overview.txt`_
* List of features: `docs/index.txt`_
* Tutorial: `docs/tutorial.txt`_
* Using as a library: `docs/library.txt`_
* Contributing: `docs/contributing.txt`_

To change rope IDE preferences like font edit your ``~/.rope`` (which
is created the first time you start rope).  To change your project
preferences edit ``$PROJECT_ROOT/.ropeproject/config.py`` where
``$PROJECT_ROOT`` is the root folder of your project (this file is
created the first time you open a project).

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
