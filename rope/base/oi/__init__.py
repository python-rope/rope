"""Rope object inference package

Rope askes two things from object inference objects:

* The object returned from a function when a specific set of
  parameters are passed to it.
* The objects passed to a function as parameters.

These information suffies for object inference since rope makes some
simplifying assumptions about the program.  Rope assumes a program
performs two main tasks: assignments and function calls.  Tracking
assignments is simple and PyName objects handle that, themselves.  The
main problem is function calls.  Rope uses these two approaches for
obtaining call information:

* `rope.base.oi.dynamicoi.DynamicObjectInference`:

  Works good but is very slow.  What it does is when you run a module
  or your testsuite, it collects information about the parameters and
  objects returned from functions and later uses them.  The main
  problem with this approach is that it is quite slow; Not when
  looking up the information but when collecting them.

* `rope.base.oi.staticoi.StaticObjectInference`

  In ``0.5m3`` rope's SOI has been enhanced very much.  For Finding
  the value returned by a function, it analyzes the body of the
  function.  The good thing about it is that you don't have to run
  anything like DOI, although for complex functions this approach does
  not give good results (opposed to DOI in which rope does not care
  about the function body at all).

  But the main advantage of SOI is that it can analyze modules and
  complete its information about functions.  This is done by analyzing
  function calls in a module or scope.  Currently SOI analyzes the
  scopes that are changed while saving or when the user asks to
  analyze a module.  That is mainly because static analysis is
  time-consuming.

  Note that by repeatedly performing SOI analysis on modules
  (something like iterative object inference) the result gets more
  accurate.


"""
