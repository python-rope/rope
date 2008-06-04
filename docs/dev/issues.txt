=============
 Rope Issues
=============


Unresolved Issues
=================

* purging out less accurate callinfos when better ones appear?
* using properties without calling its get?
* global variable inlines
* transform and extension modules
* merging extract and usefunction
* caching instances of PyObject
* moving a group of elements together
* temps might be read after body in usefunction or extract
* usefunction and function returns
* usefunction on methods
* extracted functions should be inserted before using class bodies
* adding "referenced later" wildcard argument to restructurings?
* adding "change references" wildcard argument to restructurings?
* ideas for more custom wildcards
* adapting future python 2.6 ast changes
* custom wildcards and recursive patterns
* custom restructuring wildcard patterns and replacements
* not reimporting back imports after moving
* importing compressed objectdb/history data?
* not applying all commenting mechanisms always in codeassist
* fixing try blocks before current line in code_assist
* better tests for patchedast
* import actions with more that one phase and filtering problems
* handle long imports should work on filtered imports unconditionally?
* extracting subexpressions; look at `extracttest` for more info
* switching to gplv3?
* unignored files that are not under version control
* inline fails when there is an arg mismatch
* evaluate function parameter defaults in staticoi?
* saving diffs instead of old contents in ChangeContents?
* handling tuple parameters
* extract class
* analyzing function decorators
* generate ... and implicit interfaces
* generate method and class hierarchies
* lambdas as functions; consider their parameters
* renaming similarly named variables
* handling the return type of ``yield`` keyword
* not writing unchanged objectdb and history?


To Be Reviewed
==============

* review patchedast; make it faster
* lots of estimations in codeanalyze in WordRangeFinder
* review objectdb modules
* how concluded data are held for star imports


Insert Before In Restructurings
===============================

Consider a restructuring like this::

  pattern: ${a} if ${b} else ${c}
  goal: replacement
  before: if ${b}:\n    replacement = ${a}\nelse:\n    replacement = ${c}


Memory Management
=================

These are the places in which rope spends most of the memory it
consumes:

* PyCore: for storing PyModules
* ObjectInfo: for storing object information
* History: for storing changes

We should measure the amount of memory each of them use to make
decisions.


Custom Restructuring Wildcards
==============================

There is a need to add more custom wildcards in restructuring
patterns.  But adding all such needs to `similarfinder` module makes
it really complex.  So I think adding the ability to extend them is
useful.

Sometimes wildcards can be customized.  For instance one might want to
match the function calls only if ``p1`` is passed in the arguments.
They can be specified in wildcard arguments.

Since matched wildcards can appear in the goal pattern, each wildcard
should have a corresponding replacement wildcard.  Each replacement
might be customized in each place it appears; for instance
``${mycall:-p1}`` might mean to remove ``p1`` argument.


Wildcard Format
---------------

All wildcards should appear as ``${name}``.  The type of wildcards and
their parameters can be specified using the ``args`` argument of
``Restructuring()``.

Ideas:

* Maybe we can put checks inside args, too::

    pattern: ${project:type=rope.base.project.Project}.pycore

  But what should be done when a variable appears twice::

    pattern: ${a:type=__builtin__.int} + ${a}


Examples
--------

.. ...


Possible Module Renamings
=========================

*First level*:

These module names are somehow inconsistent.

* change -> changes
* method_object -> methodobject
* default_config -> defaultconfig

*Second level*

Many modules use long names.  They can be shortened without loss of
readability.

* methodobject -> methobj or funcobj
* usefunction -> usefunc
* multiproject -> mulprj
* functionutils -> funcutils
* importutils -> imputils
* introduce_factory -> factory
* change_signature -> signature
* encapsulate_field -> encapsulate
* sourceutils -> srcutils
* resourceobserver -> observer


Getting Ready For Python 3.0
============================

This has been moved to a separate branch.
