================================================
 rope, a python refactoring IDE and library ...
================================================


Overview
========

`rope`_ is a python refactoring library and IDE.  The IDE uses the
library to provide features like refactoring, code assist, and
auto-completion.  It is written in python.  The IDE uses `Tkinter`
library.

Rope IDE and library are released in two separate packages.  *rope*
package contains only the library and *ropeide* package contains the
IDE and the library.

.. _`rope`: http://rope.sf.net/


New Features
============

* Sorting scopes
* Showing probable occurrences in show occurrences
* Cleaning up `rope.ide.codeassist` module

You can use ``C-c s ...`` for sorting current scope.  ``...`` can be
one of:

* ``a``: alphabetically
* ``A``: alphabetically reversed
* ``k``: classes first
* ``K``: functions first
* ``u``: underlineds first
* ``U``: underlineds last
* ``p``: those that have pydoc first
* ``P``: those that don't have pydoc first
* ``s``: special methods first
* ``S``: special methods last

Note that capitals sort in the reverse order of normals.  Sorts are
stable.  So if you want to sort by kind and alphabetically, for
instance, you can use ``C-c s a`` followed by ``C-c s k``.

Show occurrences dialog (``C-c C-s``) now shows possible matches, too.
These matches end with a question mark.

`rope.ide.codeassist` has been cleaned up.  Now you can do something
like::

  from rope.ide import codeassist

  # Get the completions
  proposals = codeassist.code_assist(project, source_code, offset)
  # Sorting proposals
  proposals = codeassist.sorted_proposals(proposals)
  # Where to insert the completions
  starting_offset = codeassist.starting_offset(source_code, offset)

See pydocs and source code for more information (other functions in
that module might be interesting, too; like `get_doc`,
`get_definition_location` and `find_occurrences`).  Note that this
module is included in *ropeide* package.


Getting Started
===============

* Overview and keybinding: `docs/overview.txt`_
* List of features: `docs/index.txt`_
* Tutorial: `docs/tutorial.txt`_
* Using as a library: `docs/library.txt`_
* Contributing: `docs/contributing.txt`_

To change rope IDE preferences like font edit your ``~/.rope`` (which
is created the first time you start rope).  To change your project
preferences edit ``$PROJECT_ROOT/.ropeproject/config.py`` where
``$PROJECT_ROOT`` is the root folder of your project (this file is
created the first time you open a project).

If you don't like rope's default emacs-like keybinding, edit the
default ``~/.rope`` file and change `i_like_emacs` variable to
`False`.


Project Road Map
================

The main motive for starting this project was the lack of good
refactoring tools for Python programming language.  Refactoring
programs like "bicycle repair man" aren't reliable due to type
inference problems and they support a limited number of refactorings.
*Rope* tries to improve these limitations.

The main goal of *rope* is to concentrate on the type inference and
refactoring of python programs and not a state of art IDE (at least
not in the first phase).  The type inference and refactoring parts
will not be dependent on *rope* IDE and if successful, will be
released as standalone programs and libraries so that other projects
may use them.


Get Involved!
=============

See `docs/contributing.txt`_.


Bug Reports
===========

Send your bug reports and feature requests in *rope*'s sourceforge.net
project page at http://sf.net/projects/rope.


License
=======

This program is under the terms of GPL (GNU General Public License).
Have a look at ``COPYING`` file for more information.


.. _`docs/overview.txt`: docs/overview.html
.. _`docs/tutorial.txt`: docs/tutorial.html
.. _`docs/index.txt`: docs/index.html
.. _`docs/contributing.txt`: docs/contributing.html
.. _`docs/library.txt`: docs/library.html
