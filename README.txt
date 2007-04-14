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

* `Stoppable refactorings`_
* `Basic implicit interfaces`_
* `Spell-Checker`_
* `Automatic SOI analysis`_
* `Renaming occurrences in strings and comments`_
* Faster occurrence finding

Basic Implicit Interfaces
-------------------------

Implicit interfaces are the interfaces that you don't explicitly
define; But you expect a group of classes to have some common
attributes.  These kinds of interfaces are very common in dynamic
languages; Since we only have implementation inheritance and not
interface inheritance.  For instance::

  class A(object):

      def count(self):
          pass

  class B(object):

      def count(self):
          pass

  def count_for(arg):
      return arg.count()

  count_for(A())
  count_for(B())

Here we know that there is an implicit interface defined by the
function `count_for` that provides `count()`.  Here when we rename
`A.count()` we expect `B.count()` to be renamed, too.  Currently rope
supports a basic form of implicit interfaces.  When you try to rename
an attribute of a parameter, rope renames that attribute for all
objects that have been passed to that function in different call
sites.  That is renaming the occurrence of `count` in `count_for`
function to `newcount` will result in::

  class A(object):

      def newcount(self):
          pass

  class B(object):

      def newcount(self):
          pass

  def count_for(arg):
      return arg.newcount()

  count_for(A())
  count_for(B())


This also works for change method signature.  Note that this feature
relies on rope's object inference mechanisms to find out the
parameters that are passed to a function.  Also see the `automatic SOI
analysis`_ that is added in this release.

Stoppable Refactorings
----------------------

Another notable new feature is stoppable refactorings.  Some
refactorings might take a long time to finish (based on the size of
your project).  Rope now shows a dialog that has a progress bar and a
stop button for these refactorings.  You can also use this feature
when using rope as a library.  The `get_changes()` method of these
refactorings take a new parameter called `task_handle`.  If you want
to monitor or stop these refactoring you can pass a `rope.refactor.
taskhandle.TaskHandle` to this method.  See `rope.refactor.taskhandle`
module for more information.

Automatic SOI Analysis
----------------------

Maybe the most important internal feature added in this release is
automatic static object inference analysis.  When turned on, it
analyzes the changed scopes of a file when saving for obtaining object
information; So this might make saving files a bit more time
consuming.  This feature is by default turned on, but you can turn it
off by editing your project ``config.py`` file (available in
``${your_project_root}/.ropeproject/config.py``, if you're new to
rope), though that is not recommended.

Renaming Occurrences In Strings And Comments
--------------------------------------------

You can tell rope to rename all occurrences of a name in comments and
strings.  This can be done in the rename dialog by selecting its radio
button or by passing ``docs=True`` to `Rename.get_changes()` method
when using rope as a library.  Rope renames names in comments and
strings only when the name is visible there.  For example in::

  def f():
      a_var = 1
      print 'a_var = %s' % a_var

  # f prints a_var

after we rename the `a_var` local variable in `f()` to `new_var` we
would get::

  def f():
      new_var = 1
      print 'new_var = %s' % new_var

  # f prints a_var

This makes it safe to assume that this option does not perform wrong
renames most of the time and for this reason it is by default on in
the UI (though not in `Rename.get_changes()`).

Spell-Checker
-------------

The new spell-checker uses ispell/aspell if available.  You can use
``M-$`` like emacs for checking current word.  You can also use ``C-x
$ r`` and ``C-x $ b`` for spell-checking region and buffer.


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
