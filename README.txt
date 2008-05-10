========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

* added `rope.contrib.findit.find_implementations()`
* moved `find_occurrences()` to `rope.contrib.findit` module
* inlining parameters
* adding underlined parameter to `AutoImport`
* automatic default insertion in change signature
* some internal source code analysis improvements


Inlining parameters
-------------------

`rope.refactor.inline.create_inline()` creates an `InlineParameter`
object when it is performed on a parameter.  It passes the default
value of the parameter wherever its function is called without passing
it.  For instance in::

  def f(p1=1, p2=1):
      pass

  f(3)
  f()
  f(3, 4)

after inlining p2 parameter will have::

  def f(p1=1, p2=1):
      pass

  f(3, 2)
  f(p2=2)
  f(3, 4)


`findit` module
---------------

A new `rope.contrib.findit` module has been added and
`find_occurrences()` has been moved there.  A new function was also
added to this module called `find_implementations()`.  It finds the
places in which the selected method is overridden.


``underlined`` parameter of `AutoImport`
----------------------------------------

You can control whether `rope.contrib.autoimport.AutoImport` should
cache names starting with an underline or not by using the
``underlined`` argument of its constructor.


Automatic default insertion in change signature
-----------------------------------------------

The `rope.refactor.change_signature.ArgumentReorderer` signature
changer takes a new parameter called ``autodef``.  If not `None`, its
value is used whenever rope needs to insert a default for a parameter
(that happens when an argument without default is moved after another
that has a default value).  For instance in::

  def f(p1, p2=2):
      pass

if we reorder using::

  changers = [ArgumentReorderer([1, 0], autodef='1')]

will result in::

  def f(p2=2, p1=1):
      pass


Getting Started
===============

* List of features: `docs/rope.txt`_
* Overview of some of rope's features: `docs/overview.txt`_
* Using as a library: `docs/library.txt`_
* Contributing: `docs/contributing.txt`_

To change your project preferences edit
``$PROJECT_ROOT/.ropeproject/config.py`` where ``$PROJECT_ROOT`` is
the root folder of your project (this file is created the first time
you open a project).


Bug Reports
===========

Send your bug reports and feature requests to `rope-dev (at)
googlegroups.com`_.

.. _`rope-dev (at) googlegroups.com`: http://groups.google.com/group/rope-dev


License
=======

This program is under the terms of GPL (GNU General Public License).
Have a look at ``COPYING`` file for more information.


.. _`docs/rope.txt`: docs/rope.html
.. _`docs/rope.txt`: docs/overview.html
.. _`docs/contributing.txt`: docs/contributing.html
.. _`docs/library.txt`: docs/library.html
