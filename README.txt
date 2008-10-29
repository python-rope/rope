========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

* added import_dynload_stdmods project variable
* finding dynload standard modules on windows
* fixed some windows-specific bugs

If ``import_dynload_stdmods`` is set, most standard C-extension
modules are inserted to ``extension_modules``.  Note that rope uses
the source code to collect information about modules.  If rope cannot
find the source code of a module (like C-extensions), it can import
them directly, if listed in ``extension_modules`` variable, and
analyze them.


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
