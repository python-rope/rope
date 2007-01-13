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

* Builtin functions: super, sorted, reversed, range, open
* Sorting imports according to :PEP:`8` in organize imports
* Support for builtin file type
* Enhanced dynamic object inference
* Handling long imports

Organize imports now sorts imports two.  It will sort imports according
to :PEP:`8`::

  [standard imports]

  [third-party imports]

  [project imports]


  [the rest of module]

Dynamic object inference has been enhanced to two infer the returned
objects of functions based on their parameters.

"Handle long imports" command trys to make long imports look better
by transforming ``import pkg1.pkg2.pkg3.pkg4.mod1`` to
``from pkg1.pkg2.pkg3.pkg4 import mod1``.  Long imports can be
identified either by having lots of dots or being very long.  The
default configuration considers imports with more than 2 dots or
with length more than 27 characters to be long.


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

Read `docs/dev/contributing.txt`_.


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

