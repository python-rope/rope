====================================
 rope, a python refactoring IDE ...
====================================


Overview
========

*rope* is a python IDE.  Its main goal is to provide features like
refactoring, auto-completion, code assist and outline views.  It is
written in python and uses the Tkinter library.


New Features
============

Features added in this release:

* 


Getting Started
===============

If it is the first time you use *rope*, it might be helpful to try
these:
('C' stands for Control key and 'M' for Meta(Alt) key.)

=========  ======================
C-x C-f    Find file
M-Q r      Show project tree

M-/        Show code assists
F2         Show PyDoc
F3         Go to definition
C-o        Show quick outline
M-X p      Run module

M-R        Rename Refactoring
M-M        Extract method
M-V        Move refactoring
M-I        Inline local variable

C-O        Organize imports
=========  ======================


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
M-I            inline local variable
C-O            organize imports
=============  ==========================

Have a look at `docs/overview.txt`_ file for an overview of rope's features.

.. _`docs/overview.txt`: docs/overview.html


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

*rope* has just started.  Right now *rope*'s design changes rapidly
and it's not ready for code contributions in its central parts yet.  I
hope in soon future, somewhere about version 0.4, *rope* would be
mature enough for being extended easily in those parts.

Right now contributions are really needed in UI part and patches and
extensions in the UI part are extremely welcome.  Have a look at the
UI enhancement stories (docs/stories.txt).  Send your patches in
sourceforge.net project page, http://sf.net/projects/rope.  Patches
should use python coding style, :PEP:`8`, and should have good unit
tests.  *rope* uses a local repository right now, but it will be moved
to SVN repository on sourceforge.net some time before the 0.3 release.
If you're making your patches using source package distributions
specify the version of that package.


Bug Reports
===========

Send your bug reports and feature requests in *rope*'s sourceforge.net
project page at http://sf.net/projects/rope.


License
=======

This program is under the terms of GPL(GNU General Public License).
Have a look at ``COPYING`` file for more information.

