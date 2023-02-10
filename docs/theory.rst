.. rst3: filename: docs/theory

.. _`python's ast module`: https://docs.python.org/3/library/ast.html

=====================
How Rope infers types
=====================

This is the Theory of Operation for Rope's type inference,
the most complex part of Rope.

Only Rope's core devs need to understand this material.

Some familiarity with `Python's ast module`_ is recommended, but not essential.

.. contents:: Table of Contents

Why Rope must infer types
-------------------------

.. To do.

Overview of Rope's code base
----------------------------

- Startup code.
- Type inference code.
- Utility code.
- Refactoring code.
- Code completion.

Overview of type inference
--------------------------


First principles:
- Traversers do most of the work.
- Local inference is easy; global inference is hard.

Learning what to ignore is important.
- @saveit is part of Rope's startup code. It has no direct part in type inference.

What *not* to ignore:
- @prevent_recursion prevents endless inference loops.

What is an inference?
+++++++++++++++++++++

Further study
-------------

Deep study of a few unit tests is recommended.

`ObjectInferTest.test_simple_type_inferencing` is a good place to start.

.. --- Insert traces here ---

