"""rope UI package

This package contains a sample GUI that uses rope core
parts.  Currently it uses `Tkinter` but in future this will
probably change.  The UI modules use other rope packages
such as `rope.base`, `rope.refactor` and `rope.ide`.

Note that there might be some modules that do not rely on
the GUI library.  These modules can be moved to
`rope.ide` package if they are general enough so that if
we plan to use an new graphical library (maybe wxpython) we
can reuse those modules.

"""