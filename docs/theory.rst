.. rst3: filename: docs/theory

.. _`python's ast module`: https://docs.python.org/3/library/ast.html

==========================
Rope's Theory of Operation
==========================

This document describes how Rope does type inference.

Only Rope's devs need understand this material.

Some familiarity with `Python's ast module`_ is recommended, but not essential.

.. contents:: Table of Contents

Overview of Rope's code base
----------------------------

- Startup code.
- Type inference code.
- Utility code.
- Refactoring code.

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

--- Insert traces here ---

