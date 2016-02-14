======================
 Contributing to Rope
======================


Getting Involved!
=================

Rope's main goal is being a good refactoring tool for python.  It also
provides some IDE helpers.  If you would like to contribute, you're
welcome to!


How to Help Rope?
=================

Look into `Issues`_ page and check if you can fix/help/suggest how to fix any issue/enhancement.

.. _`Issues`: https://github.com/sergeyglazyrindev/rope/issues


Wish List
=========

You are welcome to send your patches to this repository Issues page.

Issues
------

The `dev/issues.rst`_ file is actually the main rope todo file.  There
is a section called "unresolved issues"; it contains almost every kind
of task.  Most of them need some thought or discussion.  Pickup
whichever you are most interested in.  If you have ideas or questions
about them, please create corresponding issue and we can discuss enhancements, etc

.. _`dev/issues.rst`: dev/issues.rst

Write Plugins For Other IDEs
----------------------------

See ropemacs_, ropevim_, eric4_ and ropeide_.


.. _ropemacs: http://rope.sf.net/ropemacs.rst
.. _ropevim: http://rope.sf.net/ropevim.rst
.. _ropeide: http://rope.sf.net/ropeide.rst
.. _eric4: http://www.die-offenbachs.de/eric/index.rst


Rope Structure
==============

Rope package structure:

* `rope.base`: the base part of rope
* `rope.refactor`: refactorings and tools used in them
* `rope.contrib`: IDE helpers

Have a look at ``__init__.py`` of these packages or `library.rst`_ for
more information.

.. _`library.rst`: library.rst


Source Repository
=================

Rope uses GitHub_. The repository exists at https://github.com/sergeyglazyrindev/rope.


Submitting patches
==================

Patches are welcome.

Programming Style
-----------------

* Follow :PEP:`8`.
* Use four spaces for indentation.
* Include good unit-tests when appropriate.
* Rope test suite should pass after patching

Sending Patches
---------------

Follow the instructions on GitHub_ on how to setup Git and fork the
`sergeyglazyrindev/rope`_ repository. Once your changes are ready, send a
`pull request`_ for review.

.. _GitHub: http://github.com/
.. _`sergeyglazyrindev/rope`: https://github.com/sergeyglazyrindev/rope
.. _`pull request`: https://help.github.com/articles/using-pull-requests
