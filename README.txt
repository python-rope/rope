================================================
 rope, a python refactoring IDE and library ...
================================================


Overview
========

`rope`_ is a python refactoring IDE and library.  The IDE uses the
library for providing features like refactoring, code assist, and
auto-completion.  It is written in python.  The IDE uses `Tkinter`
library.

.. _`rope`: http://rope.sf.net/


New Features
============

* Replace method with method object refactoring
* Changing editor font and keybinding in ``~/.rope``
* Handling ``with`` statements
* Having two keybindings emacs/normal
* Performing change signature in class hierarchies
* Supporting builtin `zip` and `enumerate`
* Execute command; ``M-x``
* Removing extra spaces and lines; ``C-c C-f``

From this release, rope reads preferences from ``~/.rope`` file.  You
can edit this file to do things like changing the keybindings and
changing the font.  The good thing about this file is that it is in
python.  So you can do anything you like there before rope starts.
For example you can register your own `Actions` (see
`rope.ui.extension` module for more information) there.  You can
edit ``~/.rope`` using rope itself, too. (``Edit ~/.rope`` in ``Edit``
menu or ``edit_dot_rope`` action in execute_command.)

One of the main problems new users of rope had was that rope used
emacs keybinding and those not familiar with it had a hard time working
with rope.  This release adds a normal keybinding.  You can use it
by editing ``edit_to_rope`` file and setting ``i_like_emacs`` variable
to `False`.  The emacs keybinding has been enhanced very much.  But
be careful! Once you get used to it, you'll be addicted to rope!

The names of some the refactoring classes have been changed.  Those
who used rope library probably have to update their code.  The base
parts of rope has been enhanced maybe as much as the UI parts.
Introduce Method object refactoring has been added.  Some of the old
refactorings have been enhanced and the occurrence finding got notably
faster.


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
