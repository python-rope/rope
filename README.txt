========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

* Performing refactorings across multiple projects
* Specifying the number of syntax error fixes in code_assist
* Deprecated `Pycore.create_(module|package)`

`Pycore.create_module()` and `create_package()` have been deprecated.
Use `rope.contrib.generate.create_module()` and `create_package()`
instead.


Cross-Project Refactorings
--------------------------

`rope.refactor.multiproject` can be used to perform a refactoring
across multiple projects.  See ``docs/library.txt`` for more
information.


`code_assist` Changes
---------------------

`rope.contrib.codeassist.code_assist()` takes two new optional
parameters.  `maxfixes` parameter decides how many syntax errors to
fix.  `later_locals`, if `True`, forces rope to propose names that are
defined later in current scope.  See ``docs/library.txt`` for more
information.


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
