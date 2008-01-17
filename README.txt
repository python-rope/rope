========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

* Adding restructuring arguments
* Checking isinstance in restructurings
* Better handling of one-liners
* Choosing which files to apply a restructuring on

Restructuring ``checks`` has been deprecated in favor of restructuring
``arguments``.  This change is the first step towards custom
wild-cards.  So if you used::

  strchecks = {'obj1.type': 'mod.A', 'obj2': 'mod.B',
               'obj3.object': 'mod.C'}
  checks = restructuring.make_checks(strchecks)

you should use::

  args = {'obj1': 'type=mod.A', 'obj2': 'name=mod.B',
          'obj3': 'object=mod.C'}

where obj1, obj2 and obj3 are wildcard names that appear in
restructuring pattern.  And `args` is passed to the constructor.

Also wild-card names starting with ``?`` used to match any expression
that appeared at that point.  From now on, all wild-cards do so by
default; if you want to match a name with the same name as wild-card
name, you can use the ``exact`` argument of the default wild-card.
Like ``pow: object:mod.A,exact``.

A new argument has been added to the default wild-cards that acts very
similar to ``isinstance`` built-in function.  ``obj: instance=mod.A``
means either `obj` is an instance of `mod.A` or it is an instance of a
subclass of it.

A new parameter called ``resources`` has been added to
`Restructure.get_changes()`.  It can be used to limit the list of
resources to apply a restructuring on; restructurings are applied on
all python files in the project, by default.


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
