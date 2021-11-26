
.. _GitHub python-rope / rope: https://github.com/python-rope/rope


=========================================================================
 rope -- the world's most advanced open source Python refactoring library
=========================================================================


Overview
========

`Rope`_ is the world's most advanced open source Python refactoring library
(yes, I totally stole that tagline from Postgres).

.. _`rope`: https://github.com/python-rope/rope


Most Python syntax from Python 2.7 up to Python 3.10 is supported. Please file bugs and contribute
patches if you encounter gaps.

Getting Started
===============

* `How to use Rope in my IDE or Text editor? <https://github.com/python-rope/rope/wiki/How-to-use-Rope-in-my-IDE-or-Text-editor%3F>`_
* List of features: `<docs/rope.rst>`_
* Overview of some of rope's features: `<docs/overview.rst>`_
* Using as a library: `<docs/library.rst>`_
* Contributing: `<docs/contributing.rst>`_

To change your project preferences edit
``$PROJECT_ROOT/.ropeproject/config.py`` where ``$PROJECT_ROOT`` is
the root folder of your project (this file is created the first time
you open a project).


Why use Rope?
=============

- Rope aims to provide powerful and safe refactoring
- Rope is light on dependency, Rope only depends on Python itself
- Unlike PyRight or PyLance, Rope does not depend on Node.js
- Unlike PyLance or PyCharm, Rope is open source.
- Unlike PyRight and PyLance, Rope is written in Python itself, so if you experience problems, you would be able to debug and hack it yourself in a language that you are already familiar with
- In comparison to Jedi, Rope is focused on refactoring. While Jedi provides some basic refactoring capabilities, Rope supports many more advanced refactoring operations and options that Jedi does not.

Bug Reports
===========

Send your bug reports and feature requests at `python-rope's issue tracker`_ in Github.

.. _`python-rope's issue tracker`: https://github.com/python-rope/rope/issues


Maintainers
===========

Current active maintainers of Rope are Matej Cepl (`@mcepl`_) and Lie Ryan (`@lieryan`_).

Special Thanks
==============

Many thanks the following people:

- Ali Gholami Rudi (`@aligrudi`_) for initially creating the initial Rope project and most of Rope's code
- Nick Smith <nicks@fastmail.fm> (`@soupytwist`_) as former Rope maintainer
- `all of our current and former contributors`_
- authors of editor integrations

.. _`@aligrudi`: https://github.com/aligrudi
.. _`@soupytwist`: https://github.com/soupytwist
.. _`@lieryan`: https://github.com/lieryan
.. _`@mcepl`: https://github.com/mcepl
.. _`all of our current and former contributors`: https://github.com/python-rope/rope/blob/master/CONTRIBUTORS.md

License
=======

This program is under the terms of LGPL v3+ (GNU Lesser General Public License).
Have a look at `COPYING`_ for more information.


.. _`docs/rope.rst`: docs/rope.html
.. _`docs/overview.rst`: docs/overview.html
.. _`docs/contributing.rst`: docs/contributing.html
.. _`docs/library.rst`: docs/library.html
.. _`COPYING`: COPYING

.. image:: https://secure.travis-ci.org/python-rope/rope.svg
   :alt: Build Status
