========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

* supporting builtin and c-extension modules
* added in_hierarchy option to find occurrences
* faster class hierarchy analysis for refactorings
* added maxfixes to get doc and get definition location
* deprecated codeassist templates
* added extension_modules project config

If a module cannot be found in python path, rope looks it up in
``extension_modules`` project config; if it exists there, rope imports
it and analyzes its contents (rather than analyzing the source code
which is done for normal modules).

``in_hierarchy`` parameter (for matching all matching methods in class
hierarchies) and implicit interfaces (activated on attributes of
function parameters) have been added to
`codeassist.find_occurrences()` (rename and change signature already
support them).  Also ``in_hierarchy`` option no longer requires
scanning all files for making the class hierarchy, so it is much
faster.

`codeassist` module used to support templates.  But templates are much
more related to IDEs and most IDEs support them separately; so
functions and parameters related to them are deprecated now.


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
