========================================
 rope, a python refactoring library ...
========================================


Overview
========

`Rope`_ is a python refactoring library.

.. _`rope`: http://rope.sf.net/


New Features
============

* added "use function" refactoring
* completing names after from-imports
* adding resources parameter to some refactorings
* added rope.contrib.autoimport module
* handling unsure matches in restructurings
* deprecated in_file argument of Rename.get_changes()


``Use Function`` Refactoring
----------------------------

It tries to find the places in which a function can be used and
changes the code to call it instead.  For instance if mod1 is::

  def square(p):
      return p ** 2

  my_var = 3 ** 2


and mod2 is::

  another_var = 4 ** 2

if we perform "use function" on square function, mod1 will be::

  def square(p):
      return p ** 2

  my_var = square(3)

and mod2 will be::

  import mod1
  another_var = mod1.square(4)

(Example from the mailing list)


Completing Names After From Imports
-----------------------------------

`rope.base.codeassist.code_assist` now completes the names
after from-imports, too.  For instance completing::

  from shutil import rm

will propose ``rmtree``.


Refactoring Resources Parameter
-------------------------------

I've added a new parameter to some refactorings, restructure and find
occurrences called ``resources``.  If it is a list of `File`\s, all
other resources in the project are ignored and the refactoring only
analyzes them; if it is `None` all python module in the project will
be analyzed.  Using this parameter, IDEs can let the user limit the
files on which a refactoring should be applied.

I've also deprecated the "in_file" parameter of rename refactoring;
``resources`` can be used instead.


Auto-Importing
--------------

`rope.contrib.autoimport` module has been added.  This module can be
used to find the modules that provide a name.  IDEs can use this
module to auto-import names.  `AutoImport.get_modules()` returns the
list of modules with the given global name.
`AutoImport.import_assist()` tries to find the modules that have a
global name that starts with the given prefix.


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
