========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

* Static object analysis can follow functions:

  In order to enhance SOA, ``soa_followed_calls`` project config has
  been added.  It specifies the number of calls to follow when
  analyzing function calls.  The default value is 0, but it might
  change in future.  A higher value enhances rope's SOA results, but
  makes SOA slower.

* `rope.base.libutils.report_change()` reads ``automatic_soa``:

  `libutils.report_change()` now honors ``automatic_soa`` project
  config and won't perform SOA if ``automatic_soa`` is `False`.

* Added `rope.base.libutils.analyze_modules()`:

  It can be used to analyze all modules in the project for filling
  rope's objectdb.  It probably isn't necessary if automatic SOA has
  been enabled from the beginning (the default).  But if you're using
  rope on project most of which has been written without rope (or
  automatic SOA has been disabled), this function can enhance rope's
  object inferences.

  It might take a long time but it uses task handles to make it more
  tolerable (see ``library.txt``).

  Note that rope saves object information in project rope folder
  (``.ropeproject`` by default; see ``library.txt`` for more
  information).  This folder can be safely copied in other clones of a
  project if you don't want to lose your objectdb and history.

* Added `rope.contrib.codeassist.get_calltip()`:

  It returns the signature of a function in the
  ``module_name.containing_scopes.function_name(args)`` format.

* Added GIT support in fscommands:

  Rope now handles git projects in refactorings.  Note that in rope
  VCS support is used when adding, renaming or moving modules.

* Handling property as decorator:

  Rope can handle cases like this::

    def C(object):
        @property
	def attr(self):
	    return ''
    c = C()
    x = c.attr

  Here, rope can infer the object `x` is holding.

* Not re-parsing unchanged modules for code assists:

  This will make code assist commands faster; specially when reviewing
  code in which you don't change the source-code.

* Better handling of for, with and except variables
* Not fixing try blocks ending with ``except:`` by mistake in code assist
* Fixed back importing underlined names in move


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
