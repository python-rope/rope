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

Rope's mailing list is `rope-dev (at) googlegroups.com`_.  Click the
"Join group to post" button to subscribe. Then:

* Use rope
* Send bug reports and request features
* Submit patches for bugs or new features
* Discuss your ideas

.. _`rope-dev (at) googlegroups.com`: http://groups.google.com/group/rope-dev


Wish List
=========

You are welcome to send your patches to the `rope-dev (at)
googlegroups.com`_ mailing list.  Here is a list of suggestions.

Issues
------

The `dev/issues.rst`_ file is actually the main rope todo file.  There
is a section called "unresolved issues"; it contains almost every kind
of task.  Most of them need some thought or discussion.  Pickup
whichever you are most interested in.  If you have ideas or questions
about them, don't hesitate to discuss it in the mailing list.

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

Rope uses GitHub_. The repository exists at
`https://github.com/python-rope/rope`_.


Submitting patches
==================

Patches are welcome.

Programming Style
-----------------

* Follow :PEP:`8`.
* Use four spaces for indentation.
* Include good unit-tests when appropriate.
* Rope test suite should pass after patching

Testing
-------

Rope uses `pytest`_ as a test runner per default (although the 
tests are strictly unittest-based), so running::

    pytest -v

or::

    python3 -munittest -v discover

runs all tests. Make sure to have complete test suite passing and 
add new tests for the changes you are providing with each new 
submission.

All required packages for development could be installed with::

    pip install -e .[dev]


Sending Patches
---------------

Follow the instructions on GitHub_ on how to setup Git and fork the
`python-rope/rope`_ repository. Once your changes are ready, send a
`pull request`_ for review.

.. _GitHub: http://github.com/
.. _`python-rope/rope`: https://github.com/python-rope/rope
.. _`pull request`: https://help.github.com/articles/using-pull-requests
.. _`pytest`: https://pytest.org/
