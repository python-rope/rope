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

* Adding custom source folders in project ``config.py``
* A simple UI for performing restructurings; ``C-c r x``
* Restructurings

From this release rope will no longer support Python ``2.4`` and rope
``0.5`` was the last version that supported it.

Custom Source Folders
---------------------

By default rope searches the project for finding source folders
(folders that should be searched for finding modules).  You can add
paths to that list using ``source_folders`` config.  Note that rope
guesses project source folders correctly most of the time.  You can
also extend python path using ``python_path`` config.

Restructurings
--------------

Restructuring support is one of the main goals of the ``0.6`` release
of rope.  `rope.refactor.restructure` can be used for performing
restructurings.  Currently a simple dialog has been added for
performing them, but you cannot add checks to your restructuring in
that dialog, yet.  But the full functionality is available if you're
using rope as a library.

A restructuring is a program transformation; not as well defined as
other refactorings like rename.  Let's see some examples.

Example 1
'''''''''

In its basic form we have a pattern and a goal.  Consider we were not
aware of the ``**`` operator and wrote our own ::

  def pow(x, y):
      result = 1
      for i in range(y):
          result *= x
      return result

  print pow(2, 3)

Now that we know ``**`` exists we want to use it wherever `pow` is
used (There might be hundreds of them!).  We can use a pattern like::

  pattern = 'pow(${?param1}, ${?param2})'

Goal can be some thing like::

  goal = '${?param1} ** ${?param2}'

Note that ``${...}`` is used to match something in the pattern.  If
names that appear in ``${...}`` start with a leading ``?`` every
expression at that point will match, otherwise only the specified name
will match (This form is not useful if you're not using checks that is
described later).

You can use the matched names in goal and they will be replaced with
the string that was matched in each occurrence.  So the outcome of our
restructuring will be::

  def pow(x, y):
      result = 1
      for i in range(y):
          result *= x
      return result

  print 2 ** 3

It seems to be working but what if `pow` is imported in some module or
we have some other function defined in some other module that uses the
same name and we don't want to change it.  Checks come to rescue.  Each
restructuring gets a ``checks`` parameter in its constructor.  It can
be a dictionary.  Its keys are pattern names that appear in the
pattern (the names in ``${...}``) or it can be pattern names plus any
of ``.object`` or ``.type``.  The values can be rope
`rope.base.pyobject.PyObject` or `rope.base.pynames.PyNames` objects.

For solving the above problem we change our `pattern`.  But `goal`
remains the same::

  pattern = '${?pow_func}(${?param1}, ${?param2})'
  goal = '${?param1} ** ${?param2}'

Consider the name of the module containing our `pow` function is
`mod`.  ``checks`` can be::

  checks = {}
  mod = project.get_pycore().get_module('mod')
  pow_pyname = mod.get_attribute('pow')
  checks['?pow_func'] = pow_pyname

Note that project is an instance of `rope.base.project.Project`.  We
can perform the restructuring now::

  from rope.refactor import restructure

  restructuring = restructure.Restructure(project, pattern, goal, checks)
  project.do(restructuring.get_changes())

`PyName`\s and `PyObject`\s are used to describe names and objects in
rope.  Each name in a program (a `PyName`) might reference an object
(a `PyObject`) that has a type (a `PyObject`).


Example 2
'''''''''

As another example consider::

  class A(object):

      def f(self, p1, p2):
          print p1
          print p2


  a = A()
  a.f(1, 2)

Later we decide that `A.f()` is doing too much and we want to divide
it to `A.f1()` and `A.f2()`::

  class A(object):

      def f(self, p1, p2):
          print p1
          print p2

      def f1(self, p):
          print p

      def f2(self, p):
          print p2


  a = A()
  a.f(1, 2)

But who's going to fix all those nasty occurrences (Actually this
situation can be handled using inline method refactoring but this is
just an example; Consider inline refactoring is not implemented yet!).
Restructurings come to rescue::

  pattern = '${?inst}.f(${?p1}, ${?p2})'
  goal = '${?inst}.f1(${?p1}); ${?inst}.f2(${?p2})\n'
  
  mod = project.get_pycore().get_module('my.mod')
  a_class_pyname = mod.get_attribute('A')
  a_class_pyobject = a_pyname.get_object()
  checks = {}
  checks['?inst.type'] = a_class_pyobject

We can perform the restructuring using `Restructure` class as shown
above.  We will have::

  class A(object):

      def f(self, p1, p2):
          print p1
          print p2

      def f1(self, p):
          print p

      def f2(self, p):
          print p2


  a = A()
  a.f1(1); a.f2(2)

Issues
''''''

Adding checks is not available in the restructuring dialog, yet.  The
main reason is that I couldn't find a user-friendly way for specifying
them (though I have something in mind for the next release).  If you
have any idea I'll be glad to hear.

The other constraint that restructurings have is that pattern names
can only appear in at the start of an expression.  For instance
``var.${name}`` is invalid.  These situations can usually be fixed by
specifying good checks, for example on the type of `var` and using a
``${var}.name`` pattern.


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
