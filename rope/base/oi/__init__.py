"""Rope object inference package

You can add new object inference mechanisms by implementing a
class with `infer_returned_object` and `infer_parameter_objects`
methods and changing `rope.base.oi.objectinfer.ObjectInfer.__init__()`
to add your class.

Note that rope askes two things from object inference objects:

* The object returned from a function when a specific set of parameters
  are passed to it.
* The objects passed to a function as parameters.

Rope only needs these information since rope makes some
simplifying assumptions about the program.  Actually a program
performs two main tasks: assignments and function calls.  Tracking
assignments is simple and rope handles that.  The main problem are
function calls.  There are two approaches currently used by rope for
obtaining these information:

* `rope.base.oi.staticoi.StaticObjectInference`

  Currently it is very simple.  It cannot infer the parameters, since
  it does not analyze the function calls.  For obtaining the returned
  object it analyzes the expression returned from a function.  The
  main problem with advanced algorithms is that they take very long
  and for collecting useful data we have to analyze many modules
  simultaneously.  Maybe a limited, simplified version would be
  implemented in future.

* `rope.base.oi.dynamicoi.DynamicObjectInference`:

  Works good but is very slow.  What it does is when you run a
  module or your testsuite, it collects information about the
  parameters and objects returned from functions and later
  uses them.  The main problem with this approach is that it is
  quite slow; Not when looking up the information but when collecting
  them.

"""
