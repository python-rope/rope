===============
 Rope Overview
===============


The purpose of this file is to give an overview of some of rope's
features.  It is incomplete.  And some of the features shown here are
old and do not show what rope can do in extremes.  So if you really
want to feel the power of rope try its features and see its unit
tests.

This file is more suitable for the users.  Developers who plan to use
rope as a library might find :ref:`library:Using Rope As A Library` more useful.

.. contents:: Table of Contents


``.ropeproject`` Folder
=======================

Rope uses a folder inside projects for holding project configuration
and data.  Its default name is ``.ropeproject``, but it can be
changed (you can even tell rope not to create this folder).

Currently it is used for things such as:

* There is a ``config.py`` file in this folder in which you can change
  project configurations.  Have look at the default ``config.py`` file
  (is created when it does not exist) for more information.
* It can be used for saving project history, so that the next time you
  open the project you can undo past changes.
* It can be used for saving object information to help rope object
  inference.
* It can be used for saving global names cache which is used in
  auto-import.

You can change what to save and what not to in the ``config.py`` file.

Key bindings
============

Rope is a library that is used in many IDE and Text Editors to perform
refactoring on Python code. This page documents the details of the refactoring
operations but you would need consult the documentation for your IDE/Text
Editor client integration for the specific key bindings that are used by
those IDE/Text Editors.

Refactorings
============

This section shows some random refactorings that you can perform using
rope.


Renaming Attributes
-------------------

Consider we have:

.. code-block:: python

  class AClass(object):

      def __init__(self):
          self.an_attr = 1

      def a_method(self, arg):
          print(self.an_attr, arg)

  a_var = AClass()
  a_var.a_method(a_var.an_attr)

After renaming ``an_attr`` to ``new_attr`` and ``a_method`` to
``new_method`` we'll have:

.. code-block:: python

  class AClass(object):

      def __init__(self):
          self.new_attr = 1

      def new_method(self, arg):
          print(self.new_attr, arg)

  a_var = AClass()
  a_var.new_method(a_var.new_attr)


Renaming Function Keyword Parameters
------------------------------------

On:

.. code-block:: python

  def a_func(a_param):
      print(a_param)

  a_func(a_param=10)
  a_func(10)

performing rename refactoring on any occurrence of ``a_param`` will
result in:

.. code-block:: python

  def a_func(new_param):
      print(new_param)

  a_func(new_param=10)
  a_func(10)


Renaming modules
----------------

Consider the project tree is something like::

  root/
    mod1.py
    mod2.py

``mod1.py`` contains:

.. code-block:: python

  import mod2
  from mod2 import AClass

  mod2.a_func()
  a_var = AClass()

After performing rename refactoring one of the ``mod2`` occurrences in
`mod1` we'll get:

.. code-block:: python

  import newmod
  from newmod import AClass

  newmod.a_func()
  a_var = AClass()

and the new project tree would be::

  root/
    mod1.py
    newmod.py


Renaming Occurrences In Strings And Comments
--------------------------------------------

You can tell rope to rename all occurrences of a name in comments and
strings.  This can be done by passing ``docs=True`` to
`Rename.get_changes()` method.  Rope renames names in comments and
strings only where the name is visible.  For example in:

.. code-block:: python

  def f():
      a_var = 1
      # INFO: I'm printing `a_var`
      print('a_var = %s' % a_var)

  # f prints a_var

after we rename the `a_var` local variable in `f()` to `new_var` we
would get:

.. code-block:: python

  def f():
      new_var = 1
      # INFO: I'm printing `new_var`
      print('new_var = %s' % new_var)

  # f prints a_var

This makes it safe to assume that this option does not perform wrong
renames most of the time.

This also changes occurrences inside evaluated strings:

.. code-block:: python

  def func():
      print('func() called')

  eval('func()')

After renaming ``func`` to ``newfunc`` we should have:

.. code-block:: python

  def newfunc():
      print('newfunc() called')

  eval('newfunc()')


Rename When Unsure
------------------

This option tells rope to rename when it doesn't know whether it is an
exact match or not.  For example after renaming `C.a_func` when the
'rename when unsure' option is set in:

.. code-block:: python

  class C(object):

      def a_func(self):
          pass

  def a_func(arg):
      arg.a_func()

  C().a_func()

we would have:

.. code-block:: python

  class C(object):

      def new_func(self):
          pass

  def a_func(arg):
      arg.new_func()

  C().new_func()

Note that the global ``a_func`` was not renamed because we are sure that
it is not a match.  But when using this option there might be some
unexpected renames.  So only use this option when the name is almost
unique and is not defined in other places.

Move Method Refactoring
-----------------------

It happens when you perform move refactoring on a method of a class.
In this refactoring, a method of a class is moved to the class of one
of its attributes.  The old method will call the new method.  If you
want to change all of the occurrences of the old method to use the new
method you can inline it afterwards.

For instance if you perform move method on ``a_method`` in:

.. code-block:: python

  class A(object):
      pass

  class B(object):

      def __init__(self):
          self.attr = A()

      def a_method(self):
          pass

  b = B()
  b.a_method()

You will be asked for the destination field and the name of the new
method.  If you use ``attr`` and ``new_method`` in these fields
and press enter, you'll have:

.. code-block:: python

  class A(object):

      def new_method(self):
          pass

  class B(object):

      def __init__(self):
          self.attr = A()

      def a_method(self):
          return self.attr.new_method()


  b = B()
  b.a_method()

Now if you want to change the occurrences of ``B.a_method()`` to use
``A.new_method()``, you can inline ``B.a_method()``:

.. code-block:: python

  class A(object):

      def new_method(self):
          pass

  class B(object):

      def __init__(self):
          self.attr = A()

  b = B()
  b.attr.new_method()


Moving Fields
-------------

Rope does not have a separate refactoring for moving fields.  Rope's
refactorings are very flexible, though.  You can use the rename
refactoring to move fields.  For instance:

.. code-block:: python

  class A(object):
      pass

  class B(object):

      def __init__(self):
          self.a = A()
          self.attr = 1

  b = B()
  print(b.attr)

consider we want to move ``attr`` to ``A``.  We can do that by renaming
``attr`` to ``a.attr``:

.. code-block:: python

  class A(object):
      pass

  class B(object):

      def __init__(self):
          self.a = A()
          self.a.attr = 1

  b = B()
  print(b.a.attr)

You can move the definition of ``attr`` manually.


Moving Global Classes/Functions/Variables
-----------------------------------------

You can move global classes/function/variables to another module by using the
Move refactoring on a global object:

For instance, in this refactoring, if you are moving ``twice()`` to
``pkg1.mod2``:

.. code-block:: python

    # pkg1/mod1.py
    def twice(a):
        return a * 2

    print(twice(4))

.. code-block:: python

    # pkg1/mod3.py
    import pkg1.mod1
    pkg1.mod1.twice(13)


When asked for the destination module, put in ``pkg1.mod2``. Rope will update
all the imports.

.. code-block:: python

    # pkg1/mod1.py
    import pkg1.mod2
    print(pkg1.mod2.twice(4))

.. code-block:: python

    # pkg1/mod2.py
    def twice(a):
        return a * 2

.. code-block:: python

    # pkg1/mod3.py
    import pkg1.mod2
    pkg1.mod2.twice(13)


Extract Method
--------------

In these examples ``${region_start}`` and ``${region_end}`` show the
selected region for extraction:

.. code-block:: python

  def a_func():
      a = 1
      b = 2 * a
      c = ${region_start}a * 2 + b * 3${region_end}

After performing extract method we'll have:

.. code-block:: python

  def a_func():
      a = 1
      b = 2 * a
      c = new_func(a, b)

  def new_func(a, b):
      return a * 2 + b * 3

For multi-line extractions if we have:

.. code-block:: python

  def a_func():
      a = 1
      ${region_start}b = 2 * a
      c = a * 2 + b * 3${region_end}
      print(b, c)

After performing extract method we'll have:

.. code-block:: python

  def a_func():
      a = 1
      b, c = new_func(a)
      print(b, c)

  def new_func(a):
      b = 2 * a
      c = a * 2 + b * 3
      return b, c


Extracting Similar Expressions/Statements
-----------------------------------------

When performing extract method or local variable refactorings you can
tell rope to extract similar expressions/statements.  For instance
in:

.. code-block:: python

  if True:
      x = 2 * 3
  else:
      x = 2 * 3 + 1

Extracting ``2 * 3`` will result in:

.. code-block:: python

  six = 2 * 3
  if True:
      x = six
  else:
      x = six + 1

Extract Regular Method into staticmethod/classmethod
----------------------------------------------------

If you prefix the extracted method name with `@` or `$`, the generated
method will be created as a `classmethod` and `staticmethod` respectively.
For instance in:

.. code-block:: python

  class A(object):

      def f(self, a):
          b = a * 2

if you select ``a * 2`` for method extraction and name the method
``@new_method``, you'll get:

.. code-block:: python

  class A(object):

      def f(self, a):
          b = A.twice(a)

      @classmethod
      def new_method(cls, a):
          return a * 2

Similarly, you can prefix the name with `$` to create a staticmethod instead.


Extract Method In staticmethods/classmethods
--------------------------------------------

The extract method refactoring has been enhanced to handle static and
class methods better.  For instance in:

.. code-block:: python

  class A(object):

      @staticmethod
      def f(a):
          b = a * 2

if you extract ``a * 2`` as a method you'll get:

.. code-block:: python

  class A(object):

      @staticmethod
      def f(a):
          b = A.twice(a)

      @staticmethod
      def twice(a):
          return a * 2


Inline Method Refactoring
-------------------------

Inline method refactoring can add imports when necessary.  For
instance consider ``mod1.py`` is:

.. code-block:: python

  import sys


  class C(object):
      pass

  def do_something():
      print(sys.version)
      return C()

and ``mod2.py`` is:

.. code-block:: python

  import mod1


  c = mod1.do_something()

After inlining ``do_something``, ``mod2.py`` would be:

.. code-block:: python

  import mod1
  import sys


  print(sys.version)
  c = mod1.C()

Rope can inline methods, too:

.. code-block:: python

  class C(object):

      var = 1

      def f(self, p):
          result = self.var + pn
          return result


  c = C()
  x = c.f(1)

After inlining ``C.f()``, we'll have:

.. code-block:: python

  class C(object):

      var = 1

  c = C()
  result = c.var + pn
  x = result

As another example we will inline a ``classmethod``:

.. code-block:: python

  class C(object):
      @classmethod
      def say_hello(cls, name):
          return 'Saying hello to %s from %s' % (name, cls.__name__)
  hello = C.say_hello('Rope')

Inlining ``say_hello`` will result in:

.. code-block:: python

  class C(object):
      pass
  hello = 'Saying hello to %s from %s' % ('Rope', C.__name__)


Inlining Parameters
-------------------

``rope.refactor.inline.create_inline()`` creates an ``InlineParameter``
object when performed on a parameter.  It passes the default value of
the parameter wherever its function is called without passing it.  For
instance in:

.. code-block:: python

  def f(p1=1, p2=1):
      pass

  f(3)
  f()
  f(3, 4)

after inlining p2 parameter will have:

.. code-block:: python

  def f(p1=1, p2=2):
      pass

  f(3, 2)
  f(p2=2)
  f(3, 4)


Use Function Refactoring
------------------------

It tries to find the places in which a function can be used and
changes the code to call it instead.  For instance if mod1 is:

.. code-block:: python

  def square(p):
      return p ** 2

  my_var = 3 ** 2


and mod2 is:

.. code-block:: python

  another_var = 4 ** 2

if we perform "use function" on square function, mod1 will be:

.. code-block:: python

  def square(p):
      return p ** 2

  my_var = square(3)

and mod2 will be:

.. code-block:: python

  import mod1
  another_var = mod1.square(4)


Automatic Default Insertion In Change Signature
-----------------------------------------------

The ``rope.refactor.change_signature.ArgumentReorderer`` signature
changer takes a parameter called ``autodef``.  If not ``None``, its
value is used whenever rope needs to insert a default for a parameter
(that happens when an argument without default is moved after another
that has a default value).  For instance in:

.. code-block:: python

  def f(p1, p2=2):
      pass

if we reorder using:

.. code-block:: python

  changers = [ArgumentReorderer([1, 0], autodef='1')]

will result in:

.. code-block:: python

  def f(p2=2, p1=1):
      pass


Sorting Imports
---------------

Organize imports sorts imports, too.  It does that according to
:PEP:`8`::

  [__future__ imports]

  [standard imports]

  [third-party imports]

  [project imports]


  [the rest of module]


Handling Long Imports
---------------------

``Handle long imports`` command tries to make long imports look better by
transforming ``import pkg1.pkg2.pkg3.pkg4.mod1`` to ``from
pkg1.pkg2.pkg3.pkg4 import mod1``.  Long imports can be identified
either by having lots of dots or being very long.  The default
configuration considers imported modules with more than 2 dots or with
more than 27 characters to be long.


Stoppable Refactorings
----------------------

Some refactorings might take a long time to finish (based on the size of
your project).  The ``get_changes()`` method of these refactorings take
a parameter called ``task_handle``.  If you want to monitor or stop
these refactoring you can pass a ``rope.refactor.taskhandle.TaskHandle``
to this method.  See ``rope.refactor.taskhandle`` module for more
information.


Basic Implicit Interfaces
-------------------------

Implicit interfaces are the interfaces that you don't explicitly
define; But you expect a group of classes to have some common
attributes.  These interfaces are very common in dynamic languages;
Since we only have implementation inheritance and not interface
inheritance.  For instance:

.. code-block:: python

  class A(object):

      def count(self):
          pass

  class B(object):

      def count(self):
          pass

  def count_for(arg):
      return arg.count()

  count_for(A())
  count_for(B())

Here we know that there is an implicit interface defined by the function
``count_for`` that provides ``count()``.  Here when we rename
``A.count()`` we expect ``B.count()`` to be renamed, too.  Currently
rope supports a basic form of implicit interfaces.  When you try to
rename an attribute of a parameter, rope renames that attribute for all
objects that have been passed to that function in different call sites.
That is renaming the occurrence of ``count`` in ``count_for`` function
to ``newcount`` will result in:

.. code-block:: python

  class A(object):

      def newcount(self):
          pass

  class B(object):

      def newcount(self):
          pass

  def count_for(arg):
      return arg.newcount()

  count_for(A())
  count_for(B())

This also works for change method signature.  Note that this feature
relies on rope's object analysis mechanisms to find out the parameters
that are passed to a function.


Restructurings
--------------

``rope.refactor.restructure`` can be used for performing restructurings.
A restructuring is a program transformation; not as well defined as
other refactorings like rename.  In this section, we'll see some
examples.  After this example you might like to have a look at:

* ``rope.refactor.restructure`` for more examples and features not
  described here like adding imports to changed modules.
* ``rope.refactor.wildcards`` for an overview of the arguments the
  default wildcard supports.

Finally, restructurings can be improved in many ways (for instance
adding new wildcards).  You might like to discuss your ideas in the
`Github Discussion`_.

.. _`Github Discussion`: https://github.com/python-rope/rope/discussions


Example 1
'''''''''

In its basic form we have a pattern and a goal.  Consider we were not
aware of the ``**`` operator and wrote our own:

.. code-block:: python

  def pow(x, y):
      result = 1
      for i in range(y):
          result *= x
      return result

  print(pow(2, 3))

Now that we know ``**`` exists we want to use it wherever ``pow`` is
used (there might be hundreds of them!).  We can use a pattern like::

  pattern: pow(${param1}, ${param2})

Goal can be something like::

  goal: ${param1} ** ${param2}

Note that ``${...}`` can be used to match expressions.  By default
every expression at that point will match.

You can use the matched names in goal and they will be replaced with
the string that was matched in each occurrence.  So the outcome of our
restructuring will be:

.. code-block:: python

  def pow(x, y):
      result = 1
      for i in range(y):
          result *= x
      return result

  print(2 ** 3)

It seems to be working but what if ``pow`` is imported in some module or
we have some other function defined in some other module that uses the
same name and we don't want to change it.  Wildcard arguments come to
rescue.  Wildcard arguments is a mapping; Its keys are wildcard names
that appear in the pattern (the names inside ``${...}``).

The values are the parameters that are passed to wildcard matchers.
The arguments a wildcard takes is based on its type.

For checking the type of a wildcard, we can pass ``type=value`` as an
argument; ``value`` should be resolved to a python variable (or
reference).  For instance for specifying ``pow`` in this example we can
use ``mod.pow``.  As you see, this string should start from module name.
For referencing python builtin types and functions you can use
``__builtin__`` module (for instance ``__builtin__.int``).

For solving the mentioned problem, we change our ``pattern``.  But
``goal`` remains the same::

  pattern: ${pow_func}(${param1}, ${param2})
  goal: ${param1} ** ${param2}

Consider the name of the module containing our ``pow`` function is
``mod``.  ``args`` can be::

  pow_func: name=mod.pow

If we need to pass more arguments to a wildcard matcher we can use
``,`` to separate them.  Such as ``name: type=mod.MyClass,exact``.

This restructuring handles aliases like in:

.. code-block:: python

  mypow = pow
  result = mypow(2, 3)

Transforms into:

.. code-block:: python

  mypow = pow
  result = 2 ** 3

If we want to ignore aliases we can pass ``exact`` as another wildcard
argument::

  pattern: ${pow}(${param1}, ${param2})
  goal: ${param1} ** ${param2}
  args: pow: name=mod.pow, exact

``${name}``, by default, matches every expression at that point; if
``exact`` argument is passed to a wildcard only the specified name
will match (for instance, if ``exact`` is specified , ``${name}``
matches ``name`` and ``x.name`` but not ``var`` nor ``(1 + 2)`` while
a normal ``${name}`` can match all of them).

For performing this refactoring using rope library see
:ref:`library:Restructuring`.


Example 2
'''''''''

As another example consider:

.. code-block:: python

  class A(object):

      def f(self, p1, p2):
          print(p1)
          print(p2)


  a = A()
  a.f(1, 2)

Later we decide that ``A.f()`` is doing too much and we want to divide
it to ``A.f1()`` and ``A.f2()``:

.. code-block:: python

  class A(object):

      def f(self, p1, p2):
          print(p1)
          print(p2)

      def f1(self, p):
          print(p)

      def f2(self, p):
          print(p)


  a = A()
  a.f(1, 2)

But who's going to fix all those nasty occurrences (actually this
situation can be handled using inline method refactoring but this is
just an example; consider inline refactoring is not implemented yet!).
Restructurings come to rescue::

  pattern: ${inst}.f(${p1}, ${p2})
  goal:
   ${inst}.f1(${p1})
   ${inst}.f2(${p2})

  args:
   inst: type=mod.A

After performing we will have:

.. code-block:: python

  class A(object):

      def f(self, p1, p2):
          print(p1)
          print(p2)

      def f1(self, p):
          print(p)

      def f2(self, p):
          print(p)


  a = A()
  a.f1(1)
  a.f2(2)


Example 3
'''''''''

If you like to replace every occurrences of ``x.set(y)`` with ``x =
y`` when x is an instance of ``mod.A`` in:

.. code-block:: python

  from mod import A

  a = A()
  b = A()
  a.set(b)

We can perform a restructuring with these information::

  pattern: ${x}.set(${y})
  goal: ${x} = ${y}

  args: x: type=mod.A

After performing the above restructuring we'll have:

.. code-block:: python

  from mod import A

  a = A()
  b = A()
  a = b

Note that ``mod.py`` contains something like:

.. code-block:: python

  class A(object):

      def set(self, arg):
          pass

Issues
''''''

Pattern names can appear only at the start of an expression.  For
instance ``var.${name}`` is invalid.  These situations can usually be
fixed by specifying good checks, for example on the type of `var` and
using a ``${var}.name``.


Object Inference
================

This section is a bit out of date.  Static object inference can do
more than described here (see unittests).  Hope to update this
someday!


Static Object Inference
-----------------------

.. code-block:: python

  class AClass(object):

      def __init__(self):
          self.an_attr = 1

      def call_a_func(self):
          return a_func()

  def a_func():
      return AClass()

  a_var = a_func()
  #a_var.${codeassist}

  another_var = a_var
  #another_var.${codeassist}
  #another_var.call_a_func().${codeassist}


Basic support for builtin types:

.. code-block:: python

  a_list = [AClass(), AClass()]
  for x in a_list:
      pass
      #x.${codeassist}
  #a_list.pop().${codeassist}

  a_dict = ['text': AClass()]
  for key, value in a_dict.items():
      pass
      #key.${codeassist}
      #value.${codeassist}

Enhanced static returned object inference:

.. code-block:: python

    class C(object):

        def c_func(self):
            return ['']

    def a_func(arg):
        return arg.c_func()

    a_var = a_func(C())

Here rope knows that the type of a_var is a ``list`` that holds
``str``\s.

Supporting generator functions:

.. code-block:: python

  class C(object):
      pass

  def a_generator():
      yield C()


  for c in a_generator():
      a_var = c

Here the objects ``a_var`` and ``c`` hold are known.

Rope collects different types of data during SOA, like per name data
for builtin container types:

.. code-block:: python

  l1 = [C()]
  var1 = l1.pop()

  l2 = []
  l2.append(C())
  var2 = l2.pop()

Here rope can easily infer the type of ``var1``.  But for knowing the
type of ``var2``, it needs to analyze the items inserted into ``l2``
which might happen in other modules.  Rope can do that by running SOA on
that module.

You might be wondering is there any reason for using DOA instead of
SOA.  The answer is that DOA might be more accurate and handles
complex and dynamic situations.  For example in:

.. code-block:: python

  def f(arg):
      return eval(arg)

  a_var = f('C')

SOA can no way conclude the object ``a_var`` holds but it is really
trivial for DOA.  What's more SOA only analyzes calls in one module
while DOA analyzes any call that happens when running a module.  That
is, for achieving the same result as DOA you might need to run SOA on
more than one module and more than once (not considering dynamic
situations.) One advantage of SOA is that it is much faster than DOA.


Dynamic Object Analysis
-----------------------

``PyCore.run_module()`` runs a module and collects object information if
``perform_doa`` project config is set.  Since as the program runs rope
gathers type information, the program runs much slower.  After the
program is run, you can get better code assists and some of the
refactorings perform much better.

``mod1.py``:

.. code-block:: python

  def f1(param):
      pass
      #param.${codeassist}
      #f2(param).${codeassist}

  def f2(param):
      #param.${codeassist}
      return param

Using code assist in specified places does not give any information and
there is actually no information about the return type of ``f2`` or
``param`` parameter of ``f1``.

``mod2.py``:

.. code-block:: python

  import mod1

  class A(object):

      def a_method(self):
          pass

  a_var = A()
  mod1.f1(a_var)

Retry those code assists after performing DOA on ``mod2`` module.


Builtin Container Types
'''''''''''''''''''''''

Builtin types can be handled in a limited way, too:

.. code-block:: python

  class A(object):

      def a_method(self):
          pass

  def f1():
      result = []
      result.append(A())
      return result

  returned = f()
  #returned[0].${codeassist}

Test the the proposed completions after running this module.


Guessing Function Returned Value Based On Parameters
----------------------------------------------------

``mod1.py``:

.. code-block:: python

  class C1(object):

      def c1_func(self):
          pass

  class C2(object):

      def c2_func(self):
          pass


  def func(arg):
      if isinstance(arg, C1):
          return C2()
      else:
          return C1()

  func(C1())
  func(C2())

After running ``mod1`` either SOA or DOA on this module you can test:

``mod2.py``:

.. code-block:: python

  import mod1

  arg = mod1.C1()
  a_var = mod1.func(arg)
  a_var.${codeassist}
  mod1.func(mod1.C2()).${codeassist}


Automatic SOA
-------------

When turned on, it analyzes the changed scopes of a file when saving
for obtaining object information; So this might make saving files a
bit more time consuming.  By default, this feature is turned on, but
you can turn it off by editing your project ``config.py`` file, though
that is not recommended.


Validating Object DB
--------------------

Since files on disk change over time project objectdb might hold
invalid information.  Currently there is a basic incremental objectdb
validation that can be used to remove or fix out of date information.
Rope uses this feature by default but you can disable it by editing
``config.py``.


Type Hinting
------------

Currently supported type hinting for:

- function parameter type, using function doctring (:type or @type)
- function return type, using function doctring (:rtype or @rtype)
- class attribute type, using class docstring (:type or @type). Attribute should by set to None or NotImplemented in class.
- any assignment, using type comments of PEP 0484 (in limited form).

If rope cannot detect the type of a function argument correctly (due to the
dynamic nature of Python), you can help it by hinting the type using
one of the following docstring syntax styles.


**Sphinx style**

http://sphinx-doc.org/domains.html#info-field-lists

::

    def myfunction(node, foo):
        """Do something with a ``node``.

        :type node: ProgramNode
        :param str foo: foo parameter description

        """
        node.| # complete here


**Epydoc**

http://epydoc.sourceforge.net/manual-fields.html

::

    def myfunction(node):
        """Do something with a ``node``.

        @type node: ProgramNode

        """
        node.| # complete here


**Numpydoc**

https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt

In order to support the numpydoc format, you need to install the `numpydoc
<https://pypi.python.org/pypi/numpydoc>`__ package.

::

    def foo(var1, var2, long_var_name='hi'):
        r"""A one-line summary that does not use variable names or the
        function name.

        ...

        Parameters
        ----------
        var1 : array_like
            Array_like means all those objects -- lists, nested lists,
            etc. -- that can be converted to an array. We can also
            refer to variables like `var1`.
        var2 : int
            The type above can either refer to an actual Python type
            (e.g. ``int``), or describe the type of the variable in more
            detail, e.g. ``(N,) ndarray`` or ``array_like``.
        long_variable_name : {'hi', 'ho'}, optional
            Choices in brackets, default first when optional.

        ...

        """
        var2.| # complete here


**PEP 0484**

https://www.python.org/dev/peps/pep-0484/#type-comments

::

   class Sample(object):
       def __init__(self):
           self.x = None  # type: random.Random
           self.x.| # complete here


Supported syntax of type hinting
''''''''''''''''''''''''''''''''

Currently rope supports the following syntax of type-hinting.

Parametrized objects:

- Foo
- foo.bar.Baz
- list[Foo] or list[foo.bar.Baz] etc.
- set[Foo]
- tuple[Foo]
- dict[Foo, Bar]
- collections.Iterable[Foo]
- collections.Iterator[Foo]

Nested expressions also allowed:

- collections.Iterable[list[Foo]]

TODO:

Callable objects:

- (Foo, Bar) -> Baz

Multiple interfaces implementation:

- Foo | Bar


Custom Source Folders
=====================

By default rope searches the project for finding source folders
(folders that should be searched for finding modules).  You can add
paths to that list using ``source_folders`` project config.  Note that
rope guesses project source folders correctly most of the time.  You
can also extend python path using ``python_path`` config.


Version Control Systems Support
===============================

When performing refactorings some files might need to be moved (when
renaming a module) or new files might be created.  When using a VCS,
rope detects and uses it to perform file system actions.

Currently Mercurial_, GIT_, Darcs_ and SVN (using pysvn_ library) are
supported.  They are selected based on dot files in project root
directory.  For instance, Mercurial will be used if `mercurial` module
is available and there is a ``.hg`` folder in project root.  Rope
assumes either all files are under version control in a project or
there is no version control at all.  Also don't forget to commit your
changes yourself, rope doesn't do that.

Adding support for other VCSs is easy; have a look at
:ref:`library:Writing A \`FileSystemCommands\``.

.. _pysvn: http://pysvn.tigris.org
.. _Mercurial: http://selenic.com/mercurial
.. _GIT: http://git.or.cz
.. _darcs: http://darcs.net
