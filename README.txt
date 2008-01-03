========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

* deprecated ``objectdb_type`` project config; use ``save_objectdb``
* added ``compress_history`` project config
* added ``compress_objectdb`` project configs
* removed sqlite and shelve objectdb types
* fixed removing history items when ``max_history_items`` is decreased
* fixed creating objectdb file if it is missing
* fixed renaming imported names that are aliased
* fixed some importing problems
* fixed string literal pattern


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
