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

Core:

* Enhanced static object inference
* Holding per name information for builtin containers
* Change signature for constructors
* Adding 'rename when unsure' option
* Enhanced returned object static object inference
* Supporting generator functions
* Handling ``*args`` and ``**kwds`` arguments
* Showing pydoc for some of builtin types and functions

UI:

* Filling paragraphs in text modes; ``M-q``
* Yanking; ``M-y``
* Repeating last command; ``C-x z``
* Enhancing show pydoc to include docs from superclasses


The most interesting features added in this release are related to
rope's object inference mechanisms.  I'd rather show some small
examples than going into to much detail here.

Enhanced static returned object inference::

    class C(object):

        def c_func(self):
            return ['']

    def a_func(arg):
        return arg.c_func()

    a_var = a_func(C)

Here rope knows that the type of a_var is a `list` that holds `str`\s.

Supporting generator functions::

  class C(object):
      pass

  def a_generator():
      yield C()


  for c in a_generator():
      a_var = c

Here the objects `a_var` and `c` hold are known.

Another thing that has been added is SOI analysis (Available in
``Edit`` menu or by using ``C-c x s``).  It analyzes a module for
finding useful object information.  Currently it is used only when the
user askes (Just like DOI), but in future that might change.

Many kinds of information is collected during SOI like per name data
for builtin container types::

  l1 = [C()]
  var1 = l1.pop()

  l2 = []
  l2.append(C())
  var2 = l2.pop()

Here rope knowns the type of `var1` without doing anything.  But for
knowing the type of `var2` we need to analyze the items added to `l2`
which might happen in other modules.  Rope can find out that by
running SOI analysis on this module.

You might be wondering is there any reason for using DOI instead of
SOI.  The answer is that DOI is more accurate and handles complex and
dynamic situations.  For example in::

  def f(arg):
      return eval(arg)

  a_var = f('C')

SOI can no way conclude the object `a_var` holds but it is really
trivial for DOI.  What's more SOI analyzes calls only in one module
while DOI analyzes any call that happens when running a module.  That
is for achieving the same result as DOI you might need to run SOI on
more than one module and more than once (not considering dynamic
situations.) One advantage of SOI is that it is much faster than DOI.

Many enhancements to rope's object inference has been planned and till
``0.5`` release most of them will be implemented.  I'll write more
about them in future releases.

'Rename when unsure' option has been added to rename refactoring.  This
option tells rope to rename when it doesn't know whether it is an exact
match or not.  For example after renaming `C.a_func` when the
'rename when unsure' option is set in::

  class C(object):

      def a_func(self):
          pass

  def a_func(arg):
      arg.a_func()

  C().a_func()
  
we would have::

  class C(object):

      def new_func(self):
          pass

  def a_func(arg):
      arg.new_func()

  C().new_func()

Note that the global `a_func` was not renamed because we are sure that
it is not a match.  But when using this option there might be some
unexpected renames.  So only use this option when the name is not
another python defined elements.


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
