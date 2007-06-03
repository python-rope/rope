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

* Extracting similar expressions/statements
* Adding checks in restructuring dialog
* Enhancing extract method on staticmethods/classmethods

Extracting Similar Expressions/Statements
-----------------------------------------

When performing extract method or local variable refactorings you can
tell rope to extract similar expressions/statements.  For instance
in::

  if True:
      x = 2 * 3
  else:
      x = 2 * 3 + 1

Extracting ``2 * 3`` will result in::

  six = 2 * 3
  if True:
      x = six
  else:
      x = six + 1

Adding checks in restructuring dialog
-------------------------------------

The restructuring dialog has been enhanced so that you can add checks
in it, too.  For instance if you like to replace every occurrences of
``x.set(y)`` with ``x = y`` when x is an instance of `mod.A` in::

  from mod import A

  a = A()
  b = A()
  a.set(b)

We can perform a restructuring with these information::

  pattern = '${?x}.set(${?y})'
  goal = '${?x} = ${?y}'

  check: '?x.type' -> 'mod.A'

The names in checks as you see should be the name of a wild card
pattern like ``?x`` or ``?y`` in the above example.  They can have a
``.type`` or ``.object`` prefix if you want to match the type of the
object or the type a name holds instead of the reference itself.  The
values in checks are the representation of python references.  They
should start from the module that contains the element.

After performing the above restructuring we'll have::

  from mod import A

  a = A()
  b = A()
  a = b

Note that ``mod.py`` contains something like::

  class A(object):

      def set(self, arg):
          pass

Enhancing Extract Method On Staticmethods/Classmethods
------------------------------------------------------

The extract method refactoring has been enhanced to handle static and
class methods better.  For instance in::

  class A(object):

      @staticmethod
      def f(a):
          b = a * 2

if you extract ``a * 2`` as a method you'll get::

  class A(object):

      @staticmethod
      def f(a):
          b = A.twice(a)

      @staticmethod
      def twice(a):
          return a * 2


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
smalltalk writes:

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
