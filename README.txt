========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

Changes since 0.7.9:

* added `AutoImport.get_name_locations()`
* ``ignore_bad_imports`` project config
* supporting python 2.6a2

Some of the changes since 0.7:

* specifying the number of syntax fixes for codeassist commands
* supporting builtin and c-extension modules
* handling future imports in organize imports
* added `rope.contrib.autoimport`
* added use function refactoring
* choosing which files to perform refactorings on
* global extract method/variable
* performing refactorings across multiple projects
* deprecated codeassist templates


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
