====================================
 rope, a python refactoring IDE ...
====================================


Overview
========

`Ropeide`_ is a python refactoring IDE.  It uses rope library to
provide features like refactoring, code assist, and auto-completion.
It is written in python.  The IDE uses `Tkinter` library.

You should install `rope`_ library before using this IDE.

.. _`rope`: http://rope.sf.net/


New Features
============

* *Ropemacs* package for using rope in emacs
* Added `Core.add_extension()` for registering extension modules for
  *ropeide*
* A new open project dialog


Backward Incompatible Changes
-----------------------------

* *Ropeide* and *ropemacs* packages depend on *rope* package; *rope*
  should be installed, first.
* Renamed ``rope.py`` and ``rope`` scripts to ``ropeide.py`` and
  ``ropeide``.
* *Ropeide* reads ``~/.ropeide`` instead of ``~/.rope``
* `rope.ide.codeassist` was moved to `rope.contrib.codeassist`


Getting Started
===============

* Overview and keybinding: `docs/overview.txt`_
* List of features: `docs/index.txt`_
* Tutorial: `docs/tutorial.txt`_
* Contributing: `docs/contributing.txt`_

To change rope IDE preferences like font edit your ``~/.ropeide``
(which is created the first time you start rope).  To change your
project preferences edit ``$PROJECT_ROOT/.ropeproject/config.py``
where ``$PROJECT_ROOT`` is the root folder of your project (this file
is created the first time you open a project).

If you don't like rope's default emacs-like keybinding, edit the
default ``~/.ropeide`` file and change `i_like_emacs` variable to
`False`.


Bug Reports
===========

Send your bug reports and feature requests to `rope-dev (at)
googlegroups.com`_.

.. _`rope-dev (at) googlegroups.com`: http://groups.google.com/group/rope-dev


License
=======

This program is under the terms of GPL (GNU General Public License).
Have a look at ``COPYING`` file for more information.


.. _`docs/overview.txt`: docs/overview.html
.. _`docs/tutorial.txt`: docs/tutorial.html
.. _`docs/index.txt`: docs/index.html
.. _`docs/contributing.txt`: docs/contributing.html
