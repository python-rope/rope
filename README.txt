========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

* added python_files project config
* python_path project config should be searched before sys.path
* added AutoImport.clear_cache()
* added codeassist.starting_expression()
* inferring the type of except variables

* refactorings and code-assists are considerably faster
* better import insertion location
* better syntax errors
* fixed preventing maximum recursion for mutual star imports
* re-added deprecated NoProject.close() to make ropeide work
* better handling of parameters that are assigned
* fixed updating project file cache
* better global function extraction
* importing version control modules lazily

python_files
------------

The ``python_files`` project config can be used to tell rope which
files in the project are python modules.  By default it is
``['*.py']``.  If you have scripts in your project it can be useful;
for instance add::

  ``prefs['python_files'] = ['*.py', ``*.pyw``, ``scripts/*``]``

to your ``.ropeproject/config.py``.


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
