========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

* Inlining a single occurrence
* Global extract method/variable
* Reporting fixed errors when ``max_fixes`` errors were fixed but yet
  there are more syntax errors when using code-assist
* Better scope finding
* Better return value inference

``Inline(Method|Variable).get_changes()`` take a new parameter called
``only_current``.  If ``True``, only the current occurrence will be
inlined.

``Extract(Variable|Method).get_changes()`` take a new parameter called
``global_``.  If ``True``, the extracted variable|method will be made
global and the whole file is searched for similar pieces instead of
the original search scope.


Getting Started
===============

* List of features: `docs/rope.txt`_
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
.. _`docs/contributing.txt`: docs/contributing.html
.. _`docs/library.txt`: docs/library.html
