.. rst3: filename: docs/theory

.. _`python's ast module`: https://docs.python.org/3/library/ast.html
.. |br| raw:: html

   <br />

=====================
How Rope infers types
=====================

This is the Theory of Operation for Rope's type inference,
the most complex part of Rope.

Are you sure you should be reading this chapter?
Only Rope's core devs need to understand this material.

Rope infers the types of objects to:

- suggest appropriate code completions.
- limit refactorings to the appropriate class.

Some familiarity with `Python's ast module`_ is recommended, but not essential.

.. contents:: Table of Contents

Overview of type inference
--------------------------


.. _`mypy`: https://mypy-lang.org/

Type inference is hard because the types of objects may depend on the type
of objects in other methods, functions or modules.

In particular, the return type of a function f may depend on the type of
its arguments, and the types of those arguments may depend on all the
various calls to f throughout the program.

The necessary chains of inference can be bewilderingly complex. The
`@prevent_recursion` decorator prevents endless inference loops, but this
decorator is only one part of the puzzle.

Unlike `mypy`_, Rope:

- Infers types only as needed.
- Does no type checking: Rope does not check that the types of all objects are consistent.

Questions to be answered
------------------------


.. Answer these questions in the study branch!

- Startup: What inference data (if any) does it create?
- Preprocessing: does it exist? What does it do?
- What is a `PyObject`? It clearly has a central role in soi.
- What is `_Inferred`'s role?
- What do all the data in `PyDefinedObject` mean?

Overview of Rope's code base
----------------------------

Inference code:

- Traversers are where everything happens.
  To the first approximation, *only the visitors matter*.
- Several kinds of traversers, one for each "query": |br|
  startup, inference, refactoring, error reporting, etc.
- There are many "queries" because results are computed as needed.
- Some traverser classes may be artifacts of unit tests, but this is unlikely.

As far as type inference goes, we can mostly ignore everything else:

- Startup code
- @saveit and @prevent_recursion decorators.
- Refactoring code.
- Code completion code.
- Utility code.

**Important**: as far as type inference is concerned, devs can most ignore the following:

- The `saveit/cacheit decorator` is part of startup. |br|
  It has no direct effect on type inference.
- Despite its name, the `codeanalyze module` is not directly involved in making inferences.

In-depth study: test_simple_type_inferencing
--------------------------------------------

`ObjectInferTest.test_simple_type_inferencing` is one of Rope's simplest
unit test. Studying this test deeply is a good way of learning how Rope
works.

**Note**: `pdb` shows file/module names in addition to line numbers.
Several of Rope's classes have the same names, so this extra info is
crucial!

The original test
+++++++++++++++++


Here is the original unit test:

.. code-block:: python

    def test_simple_type_inferencing(self):
        code = dedent("""\
            class Sample(object):
                pass
            a_var = Sample()
        """)
        scope = libutils.get_string_scope(self.project, code)
        sample_class = scope["Sample"].get_object()
        a_var = scope["a_var"].get_object()
        self.assertEqual(sample_class, a_var.get_type())

The annotated test
++++++++++++++++++


And here is the same test, with added trace statements and comments:

.. code-block:: python

    def test_simple_type_inferencing(self):
        code = dedent("""\
            class Sample(object):
                pass
            a_var = Sample()
        """)

        trace = True

        def banner(s):
            if trace:
                print(f"\n{g._caller_name(2)}: ===== {s}")


        banner('after setUp')

        # 1. setUp creates self.project.

            # setUp instantiates self.project to a Project instance.
            # self.project = testutils.sample_project()

        # 2. get_string_scope sets self.scope to the scope of the test string.

            # Sets self.scope to pyobjectsdef.PyModule(project.pycore, code, ...)
            # (code is the test string, defined above.)

        # ??? Instantiating the pyobjectsdef.PyModule does all the work ???

            # PyDefinedObject.__init__ calls:

                # self.concluded_attributes = self.get_module()._get_concluded_data()
                # self.attributes = self.get_module()._get_concluded_data()

            # But all attributes are empty for this test.

        scope = libutils.get_string_scope(self.project, code)

        banner('after get_string_scope\n')

            # scope is a GlobalScope.  It might be any subclass of Scope.
            # scope.pyobject is a pyobjectsdef.PyModule.

        # if trace: g.trace('*** scope.pyobject', scope.pyobject)

        # *** Calling scope["Sample"] (via _ScopeVisitor._ClassDef)
        #     instantiates pyobjects.PyClass *and* pyobjectsdef.PyClass.
        #     (Because pyobjectsDef.PyClass is a subclass of pyobjects.PyClass.)
        # scope["Sample"] is a pynamesdef.DefinedName.

        sample_class = scope["Sample"].get_object()

        banner('after sample_class = scope["Sample"].get_object()\n')


            # sample_class is a pyobjectsdef.PyClass ("::Sample" at ...)
            # scope["Sample"] is a DefinedName.
            # scope["Sample"].pyobject is a pyobjectsdef.PyClass.

        a_var = scope["a_var"].get_object()

            # a_var is a pyobjects.PyObject
            # a_var.get_type() is a pyobjectsdef.PyClass ("::Sample" at ...)

            # scope["a_var"] is an pynamesdef.AssignedName.
            # scope["a_var"].pyobject is a pynames._Inferred.
            # scope["a_var"].get_object() is a pyobjects.PyObject.

        if trace:
            print('')
            print(f"sample_class: {sample_class}")

        self.assertEqual(sample_class, a_var.get_type())

setUp simulates Rope's startup logic
++++++++++++++++++++++++++++++++++++


`ObjectInferTest.setUp` executes a simplified version of Rope's startup logic:

.. code-block:: python

    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()

sample_project() just creates a `Project` instance.

Rope's actual startup code is more complex, but for now I think it's safe to ignore these details.

This code falls into `pdb` only for our test:

.. code-block:: python

    def setUp(self):
        super().setUp()
        if self.id().endswith('test_simple_type_inferencing'):
            g.pdb()
        self.project = testutils.sample_project()

Looking at the *results* of the call to `testutils.sample_project()` was good enough at first.

Summary of initial study
++++++++++++++++++++++++

**Hello-world unit test**

ObjectInferTest.test_simple_type_inferencing` is my "Hello World" unit test. This test:

- makes a simple (easily understood!) inference.
- executes much of Rope's startup and soi code.

**Startup**

Rope's startup logic creates Project and PyCore objects. Most classes can
access these objects directly (through their ivars) or indirectly (through
the ivars of other classes).

**Data**

Afaik, the `Scope` class contains all (most?) of the computed type inferences.

If `scope` is a `Scope`, statements of the form `scope[name]`, where `name`
(a string) is a member of the scope, provide access to all inferences!

