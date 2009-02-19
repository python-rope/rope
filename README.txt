========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

* caching all sub-modules of a module in `rope.contrib.autoimport`
* fix recursion when creating modules
* added basic support for setuptools
* extract method handles conditional variable updates
* added `rope.contrib.codeassist.CompletionProposal.parameters`

The `rope.contrib.autoimport.AutoImport.generate_module_cache()` has
been changed to handle module names that end with ``.*``.  Now one can
use ``rope.*`` to mean `rope` and all of its sub-modules.

Extract method now handles variable updates better.  For instance in::

  def f(a):
      if 0:
          a = 1
      print(a)

When extracting the first two lines of `f()`, `a` should be passed to
`g()`.  Although these lines don't read `a`, if the conditional write
(like in ``if`` or ``while`` blocks) does not happen, it results in an
error.  So the outcome will be::

  def f(a):
      a = g(a)
      print(a)

  def g(a):
      if 0:
          a = 1
      return a


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
.. _`docs/overview.txt`: docs/overview.html
.. _`docs/contributing.txt`: docs/contributing.html
.. _`docs/library.txt`: docs/library.html
