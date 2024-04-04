
.. _GitHub python-rope / rope: https://github.com/python-rope/rope


rope -- the world's most advanced open source Python refactoring library
========================================================================

|Build status badge| |Latest version badge| |Download count badge| |ReadTheDocs status badge| |Codecov badge|

.. |Build status badge| image:: https://github.com/python-rope/rope/actions/workflows/main.yml/badge.svg
   :target: https://github.com/python-rope/rope/actions/workflows/main.yml
   :alt: Build Status

.. |Latest version badge| image:: https://badge.fury.io/py/rope.svg
   :target: https://badge.fury.io/py/rope
   :alt: Latest version

.. |Download count badge| image:: https://img.shields.io/pypi/dm/rope.svg
   :alt: Download count

.. |ReadTheDocs status badge| image:: https://readthedocs.org/projects/rope/badge/?version=latest
   :target: https://rope.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. |Codecov badge| image:: https://codecov.io/gh/python-rope/rope/graph/badge.svg?token=pU08MBXFIS
   :target: https://codecov.io/gh/python-rope/rope
   :alt: Codecov 

Overview
========

`Rope`_ is the world's most advanced open source Python refactoring library
(yes, I totally stole that tagline from Postgres).

.. _`rope`: https://github.com/python-rope/rope


Most Python syntax up to Python 3.10 is supported. Please file bugs and contribute
patches if you encounter gaps.

Since version 1.0.0, rope no longer support running on Python 2.
If you need Python 2 support, then check out the `python2` branch or the 0.x.x
releases.

Getting Started
===============

* `Documentation <https://rope.readthedocs.io/en/latest/overview.html>`_
* `How to use Rope in my IDE or Text editor? <https://github.com/python-rope/rope/wiki/How-to-use-Rope-in-my-IDE-or-Text-editor%3F>`_
* `Configuration <https://rope.readthedocs.io/en/latest/configuration.html>`_
* `List of features <https://rope.readthedocs.io/en/latest/rope.html>`_
* `Overview of some of rope's features <https://rope.readthedocs.io/en/latest/overview.html>`_
* `Using as a library <https://rope.readthedocs.io/en/latest/library.html>`_
* `Contributing <https://rope.readthedocs.io/en/latest/contributing.html>`_

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

Send your bug reports and feature requests at `python-rope's issue tracker`_ in GitHub.

.. _`python-rope's issue tracker`: https://github.com/python-rope/rope/issues


Maintainers
===========

Current active maintainer of Rope is Lie Ryan (`@lieryan`_).

Special Thanks
==============

Many thanks the following people:

- Ali Gholami Rudi (`@aligrudi`_) for initially creating the initial Rope project and most of Rope's code
- Matej Cepl (`@mcepl`_) as former long-time Rope maintainer
- Nick Smith <nicks@fastmail.fm> (`@soupytwist`_) as former Rope maintainer
- `all of our current and former contributors`_
- `all authors of editor integrations`_
- all maintainers of distro/package managers

.. _`@aligrudi`: https://github.com/aligrudi
.. _`@soupytwist`: https://github.com/soupytwist
.. _`@lieryan`: https://github.com/lieryan
.. _`@mcepl`: https://github.com/mcepl
.. _`all of our current and former contributors`: https://github.com/python-rope/rope/blob/master/CONTRIBUTORS.md
.. _`all authors of editor integrations`: https://github.com/python-rope/rope/wiki/How-to-use-Rope-in-my-IDE-or-Text-editor%3F

Packaging Status
================

.. image:: https://repology.org/badge/vertical-allrepos/python:rope.svg?exclude_unsupported=1
   :target: https://repology.org/project/python:rope/versions
   :alt: Packaging status

.. image:: https://repology.org/badge/vertical-allrepos/rope.svg?exclude_unsupported=1
   :target: https://repology.org/project/rope/versions
   :alt: Packaging status

License
=======

This program is under the terms of LGPL v3+ (GNU Lesser General Public License).
Have a look at `COPYING`_ for more information.

.. _`COPYING`: COPYING
