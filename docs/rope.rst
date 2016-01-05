Features
========

Features implemented so far:

* Refactorings

  * Rename everything!
  * Extract method/local variable
  * Move class/function/module/package/method
  * Inline method/local variable/parameter
  * Restructuring (like converting ``${a}.f(${b})`` to
    ``${b}.g(${a})`` where ``a: type=mymod.A``)
  * Introduce factory
  * Change method signature
  * Transform module to package
  * Encapsulate field
  * Replace method with method object
  * And a few others

* Refactoring Features

  * Extracting similar statements in extract refactorings
  * Fixing imports when needed
  * Previewing refactorings
  * Undo/redo refactorings
  * Stopping refactorings
  * Cross-project refactorings
  * Basic implicit interfaces handling in rename and change signature
  * Mercurial_, GIT_, Darcs_ and SVN (pysvn_ library) support in
    refactorings

* IDE helpers

  * Auto-completion
  * Definition location
  * Get pydoc
  * Find occurrences
  * Organize imports (remove unused and duplicate imports and sort them)
  * Generating python elements

* Object Inference

  * Static and dynamic object analysis
  * Handling built-in container types
  * Saving object information on disk and validating them
  * Type hints using docstring or type comments PEP 0484

For more information see `overview.rst`_.


.. _overview.rst: overview.rst
.. _pysvn: http://pysvn.tigris.org
.. _Mercurial: http://selenic.com/mercurial
.. _GIT: http://git.or.cz
.. _darcs: http://darcs.net
