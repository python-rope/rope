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

Rope's development happens in  `python-rope's Github`_.

Use `python-rope's Github Issue Tracker`_ to discuss development-related issues:

* Send bug reports and request features
* Submit patches for bugs or new features

Use `python-rope's Github Discussion`_ for other discussions, such as:

* Help using rope
* Help integrating rope with text editors/tools
* Discuss your ideas
* Engage with the rope community

.. _`python-rope's Github`: https://github.com/python-rope/rope
.. _`python-rope's Github Issue Tracker`: https://github.com/python-rope/rope/issues
.. _`python-rope's Github Discussion`: https://github.com/python-rope/rope/discussions


Wish List
=========

You are welcome to make pull requests in `python-rope's Github Issue Tracker`_.

Here is a list of suggestions.

Issues
------

If this is your first time contributing in rope and you don't know where to start, 
tickets labeled `good first issue`_ is a good place start.

The `unresolved issues list`_ in Github is the latest todo list.

There is also a rather outdated list in `dev/issues.rst`_. There
is a section called "unresolved issues"; it contains almost every kind
of task.  This file will need some cleanup, thoughts, and discussions.

Pickup whichever you are most interested in.  If you have ideas or questions
about them, don't hesitate to create a Github ticket for it.

.. _`good first issue`: https://github.com/python-rope/rope/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22
.. _`unresolved issues list`: https://github.com/python-rope/rope/issues
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


Submitting pull requests
========================

Pull requests are welcome.

Follow the instructions on GitHub_ on how to setup Git and fork the
`python-rope/rope`_ repository. Once your changes are ready, send a
`pull request`_ for review.


Programming Style
-----------------

* Follow `black codestyle`_
* Follow :PEP:`8`.
* Use four spaces for indentation.
* Include good unit-tests when appropriate.
* Rope test suite should pass after patching

.. _`black codestyle`: https://github.com/psf/black

Testing
-------

Rope uses `pytest`_ as a test runner per default (although the 
tests are strictly unittest-based), so running::

    pytest -v

runs all tests. Make sure to have complete test suite passing and 
add new tests for the changes you are providing with each new 
submission.

All required packages for development could be installed with::

    pip install -e .[dev]

.. _GitHub: http://github.com/
.. _`python-rope/rope`: https://github.com/python-rope/rope
.. _`pull request`: https://help.github.com/articles/using-pull-requests
.. _`pytest`: https://pytest.org/
