================================================
 rope, a python refactoring IDE and library ...
================================================


Overview
========

*rope* is a python IDE.  Its main goal is to provide features like
refactoring, auto-completion, code assist and outline views.  It is
written in python and uses the Tkinter library.


New Features
============

Features added in this release:

* Change method signature

  * Reorder parameters
  * Remove parameter
  * Add parameter

* Inline argument default value

In the change method signature dialog these shortcuts work:

======  ======================
key     binding
======  ======================
C-n     move downward
C-p     move upward
M-n     move parameter down
M-p     move parameter up
M-r     remove parameter
M-a     add new parameter
======  ======================

The ``value`` field in add new parameter dialog changes all calls
to pass ``value`` as this new parameter if it is non-empty.  You
can do the same thing for existing arguments using inline argument
default value.

Inline argument default value changes all function calls that don't
pass any value as this argument to pass the default value specified
in function definition.

While reordering arguments you should consider the python
language order for argument types (i.e. : normal args, args with
defaults, *args, **keywords).  Rope won't complain if you don't but
python will.


Keybinding
==========

The keybinding will be customizable in future.  Some of these bindings
are chosen from emacs and some from eclipse.  ('C' stands for Control
key and 'M' for Meta(Alt) key.)

=============  ==========================
key            binding
=============  ==========================
C-x C-p        open/new project
C-x C-n        new file
C-x C-f        find file
C-x b          change active editor
C-x k          close active editor
C-x C-c        exit
M-X p          run active editor
M-X t          run unit-tests
M-Q r          show project tree
-------------  --------------------------
C-f            forward character
C-b            backward character
C-n            next line
C-p            previous line
M-f            next word
M-b            previous word
C-v            next page
M-v            previous page
C-s            start searching
C-x C-u        undo
C-x C-r        redo
C-space        set mark
C-w            cut region
M-w            copy region
C-x C-x        swap mark and insert
C-y            paste
C-x C-s        save
C-x s          save all
-------------  --------------------------
C-i            correct line indentation
M-/            code-assist
F3             go to definition location
F2             show doc
C-o            show quick outline
M-R            rename refactoring
M-M            extract method
M-V            move refactoring
M-I            inline refactoring
M-C            change method signature
M-L            extract local variable
C-O            organize imports
=============  ==========================

Have a look at `docs/user/overview.txt`_ file for an overview of rope's
features.

.. _`docs/user/overview.txt`: docs/user/overview.html


Project Road Map
================

The main motive for starting this project was the lack of good
refactoring tools for python language.  Refactoring programs like
"bicycle repair man" aren't reliable due to type inference problems
and they support a limited number of refactorings.

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
will not be dependent on *rope* and if successful, will be released as
standalone programs and libraries so that other projects may use them.


Get Involved!
=============

Read `docs/dev/contributing.txt`_.

.. _`docs/dev/contributing.txt`: docs/dev/contributing.html


Bug Reports
===========

Send your bug reports and feature requests in *rope*'s sourceforge.net
project page at http://sf.net/projects/rope.


License
=======

This program is under the terms of GPL(GNU General Public License).
Have a look at ``COPYING`` file for more information.

