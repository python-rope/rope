=========================
 ropemacs, rope in emacs
=========================

Using rope in emacs.  You should install `rope`_ library before using
ropemacs.

.. _`rope`: http://rope.sf.net/


Setting Up
==========

After installing pymacs, add these lines to your ``~/.emacs`` file::

  (load-library "pymacs")
  (pymacs-load "ropemacs" "rope-")
  (rope-init)


Keybinding
==========

Uses the same keybinding as in rope.


Getting Started
===============

* List of features: `docs/index.txt`_
* Contributing: `docs/contributing.txt`_

.. _`docs/index.txt`: docs/index.html
.. _`docs/contributing.txt`: docs/contributing.html


License
=======

This program is under the terms of GPL (GNU General Public License).
Have a look at ``COPYING`` file for more information.
