========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

Changes since 0.8.4:

* supporting Darcs VCS
* handling files with mac line-ending
* not searching all files when inlining a local variable
* fixed cygwin path problems

Some of the changes since 0.8:

* inlining variable in other modules
* added `rope.contrib.findit.find_definition()`
* better extension module handling
* added `rope.contrib.findit.find_definition()`
* added GIT support in fscommands
* inlining parameters
* back importing underlined names in move
* added `codeassist.get_calltip()`
* added `libutils.analyze_modules()`
* added ``soa_followed_calls`` project config
* `libutils.report_change()` reads `automatic_soa`
* handling property decorator


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
