=========================
 Using Rope As A Library
=========================

If you need other features, send a feature request.  Have a look at
:ref:`contributing:Contributing to Rope`.


.. contents:: Table of Contents


Quick Start
===========

This section will help you get started as soon as possible.

Formatted string expressions infer the native ``str`` instance type without
evaluating their formatted values. Their nested expressions remain visible to
the existing reference, call and reflection analysis.

Semantic match capture regions
------------------------------

Matches returned by ``rope.refactor.similarfinder.SimilarFinder.get_matches``
provide ``get_capture_region(name)``.  It returns the captured variable's
half-open character range in the original source, for both expression and
statement patterns.  An unknown capture raises ``ValueError``.  Clients can
therefore use source regions without depending on Rope's syntax nodes.

The module's existing ``get_source_binding_index().absolute_import_roots()``
returns a frozen set of absolute top-level import names from its indexed
declarations, including guarded and nested imports.  Relative imports are
excluded.  This query neither imports the declared packages nor resolves their
classes, and it preserves declarations whose local bindings are overwritten.
Occurrence import roles use the same native import-declaration spans. A
``yield from`` before a later import must not classify an intervening function
declaration as imported and silently omit its signature change.

``assignment_string_sequence(name, scope=None, *, class_metadata=False)`` reads the first direct
assignment in the indexed module or an explicitly supplied class scope.  It
returns a tuple for a literal string list, tuple or set, and follows module
name references and single-name ``tuple``/``list``/``set``/``frozenset`` wrappers.
Missing declarations return ``None``; present empty or unsupported values return
an empty tuple.  Cyclic references raise ``ValueError``.  It uses the module's
existing parse without evaluating authored code or resolving class ancestry.
A supplied scope must belong to that same indexed module; another module's
scope raises ``ValueError`` instead of mixing its declarations with local names.
With ``class_metadata=True``, an absent module declaration may be read from a
single directly declared class.  Module declarations still take precedence,
including empty or unsupported values.  This mode does not resolve class scopes
or superclasses and cannot be combined with an explicit scope.

Class headers use the binding that exists before the new class replaces its
name. In particular, importing ``Foo`` and then declaring ``class Foo(Foo)``
inherits the imported class; it does not declare a self-inheritance cycle.
For a generic class, a same-named native type parameter takes precedence over
that earlier binding, as it does for the other names in the generic header.
This source-binding requirement does not waive rejection of an inconsistent
hierarchy or introduce a second method-resolution-order implementation.

``get_source_binding_index().class_layout(scope)`` exposes the source layout of
a class in that same module. Its immutable result contains the declaration,
header and body regions, the offset immediately after the declaration colon,
the name region and base-list insertion offset, optional
parenthesized argument-content region, direct keyword/base/decorator regions,
original base bindings, named type-parameter regions,
and direct annotated
bindings. Each annotated binding retains its complete statement region, the
native binding of its annotation qualifier and whether a value is present.
Qualifier resolution uses the annotation's original source context, including
aliases and generic header bindings. An unresolved qualifier remains ``None``;
it is not replaced by a guessed name. Regions are half-open character offsets
into the indexed module, not lines or a copy of its syntax tree. A scope from
another module, or a non-class scope, is rejected. Consumers can use these facts
and the existing ``context_at``/native class queries without inspecting syntax
nodes, reconstructing a header or opening a second project.
The argument region distinguishes ``class A:`` from ``class A():`` and preserves
keyword-only headers such as ``class A(metaclass=M):``. Header tokens are read by
Rope's existing lexical reader over the bounded header, so Unicode identifier
spelling, comments, generic bounds and explicit line continuations keep their
original character offsets. A leading decorated member belongs to the body,
including its decorator lines.

``assignment_layouts(scope=None, *, name=None)`` returns immutable metadata for
direct assignments and type-alias declarations in the supplied scope (the module
by default). Each record carries its native statement kind, complete statement
region, named target regions, optional value/annotation regions and the native
value binding resolved in its original source context. ``root_binding`` is the
binding of a bare-name root below attribute access, or ``None`` for other
expressions. ``string_sequence`` is the exact tuple of a direct literal string
list, tuple or set, or ``None`` for another value. ``type_parameters`` retains
named parameter regions of generic type aliases. Value inference is explicit:
``resolve_values=True`` resolves ``value_binding`` and ``root_binding``; the
default returns layout only. A name selection is applied before this inference,
so a query for one binding does not infer unrelated declarations. Multiple writes remain separate ordered records;
clients retain responsibility for admitting ambiguous or augmented writes.
Like ``class_layout``, this query uses only the existing indexed source and
rejects a scope from another module.

The existing ``SourceContext.access`` query distinguishes expression reads,
writes and deletions (``"read"``, ``"write"`` and ``"delete"``), returning
``None`` for a context that is not a name/attribute/subscript access. Clients
can combine this with the original context environment and semantic match
regions without interpreting a syntax node.

``decorator_bindings(scope)`` returns the ordered native callee bindings of a
source declaration's decorators. A called decorator resolves its callable in
the original header environment rather than evaluating its factory result.
Declarations without decorators return an empty tuple. Unknown callees retain
``None`` and native resolution errors propagate; no decorator is imported or
executed by this query.

``string_mapping_arguments(callee, position)`` locates a named call's positional
mapping argument in the existing index.

``import_layouts()`` exposes imports from that same index, including guarded and
local imports. Each immutable record retains the statement region, optional
from-provider region, module name, relative level and original imported names,
aliases and their source regions. It never hoists imports or resolves unrelated
providers. Native lexical offsets preserve the original importing boundary.
Alias-separator regions identify the existing commas between indexed aliases;
consumers can retain intervening comments when removing selected names.

The string-mapping query follows a single native assignment
for a referenced lexical name and retains native bindings of the selected callee
and single-argument wrappers. Each result carries the mapping region and literal string keys with
string-or-string-tuple values and the original value-token regions. Unsupported
or ambiguous shapes have ``entries=None``; clients decide whether that is an
expected refusal. The query neither evaluates a wrapper nor assigns it mapping
semantics. It opens no project, parses no new source and keeps unrelated strings
out of the selected mapping.

Subscription analysis must distinguish instance ``__getitem__`` from class
``__class_getitem__`` and retain the actual subscription argument. A metaclass's
``__getitem__`` has precedence over the class hook. An unresolved subscription
remains unresolved; substituting its origin class without proving the hook's
result is not an ancestry contract. Native support for these cases is being
qualified against source-derived regressions before consumers rely on it.

The standard-library ``Generic`` and ``Protocol`` alias model applies to builtin
and source implementations across supported Python versions. Source declarations retain
their native class identity: admission authenticates the top-level declaration
against the runtime library's name and physical module resource. A project-local
``typing.py`` or a same-named class does not select this model. The shared alias
factory retains every argument and recognizes only the type-variable capabilities
available in that interpreter; unavailable APIs do not become substitutes or skips.
When that authenticated owner is ``Generic`` or ``Protocol``, invalid parameters
raise the original ``TypeError`` before an alias is constructed. Concrete aliases
such as ``Mapping[str, str]`` have a different owner and do not justify admitting
invalid ``Generic`` or ``Protocol`` arguments. This preserves the
`typing specification's parameter contract
<https://typing.python.org/en/latest/spec/generics.html#user-defined-generic-types>`_;
an inference failure must be diagnosed at its actual source rather than bypassing
this validation. The rejecting exception retains native object and type identities
for the supplied arguments, including their declaring module resources when known.
Unknown objects are reported by their native kind without assuming a class name;
the diagnostic reads the values already supplied to the alias factory and does not
resolve another namespace. Diagnostic failures remain secondary notes on the same
``TypeError``. Restoring the validation alone does not qualify a consumer.
Source ``Generic`` bases use the same native C3 machinery and runtime-library base
identities as their builtin counterpart. This contract does not authorize importing
application targets or replacing an unresolved custom hook with its origin.

Variadic generic parameters use the authenticated standard-library ``Unpack``
operation and retain their inner ``TypeVarTuple`` by reference. A raw
``TypeVarTuple`` is not itself a valid ``Generic`` or ``Protocol`` parameter.
Interpreters lacking these APIs retain their real missing-import and unresolved
binding contracts; an alternate provider or a skipped positive case does not
qualify this capability.

The one-argument builtin ``type(value)`` operation is distinct from Rope's
``PyObject.get_type()`` kind markers. Class operands select their actual native
metaclass; instance operands select their known native class. Unresolved operands
and metaclass witnesses remain unresolved. This does not change the existing
three-argument class-construction analysis or make a metaclass instance into a
source-defined class.

Method-transfer declaration reads authenticate the native receiver getter and
the member's descriptor behavior. Plain scalar members are recognized by their
native builtin class identity; absent literal-value metadata is not a known
``None`` value and cannot admit an arbitrary descriptor. Inherited class members,
direct module declarations and their existing binding checks remain unchanged.
The instance-transfer ``resolve_binding`` dependency defaults to native
``evaluate.eval_node``. A caller may supply its existing source-view resolver;
the same dependency resolves original and proposed expressions, while native
getter, descriptor and binding-identity checks remain mandatory.

Native class-construction analysis must retain the supplied class name, ordered
bases, explicit metaclass and known namespace bindings in the existing
``AbstractClass`` model. Empty bases select the native ``object`` class;
ancestry and inherited attributes use native C3. Literal values must retain
their payload through ordinary argument inference while preserving their
builtin type identity. An unresolved name, base or namespace must not become an
invented class. Construction uses source inference without importing the
application or executing a runtime class factory. This contract includes
``type.__new__``, three-argument ``type`` and source metaclass calls whose
constructor resolves to native ``type.__new__``; qualification against real
consumers is pending.

Calling a class whose ``__new__`` is a source Python function with implicit or
explicit staticmethod semantics supplies the requested class exactly once through
the existing native argument binder. Simple names and qualified class calls use
the same path. Its inferred return is retained, including an unresolved return;
the source constructor does not manufacture an instance of its declaring proxy.
The native ``type.__new__`` path remains unchanged. This cut does not alter the
existing classmethod or lambda constructor paths and does not establish complete
constructor qualification. The original public consumer remains the runtime
acceptance boundary before SDK regression tests and integration.

While an assignment's right-hand side is inferred, a recursive read of that same
``AssignedName`` observes only its preceding assignments on a compatible control
path. The existing source-binding index records nested ``if`` arms while visiting the
condition and both suites in source order. Literal conditions select their
reachable arm; opaque conditions retain both outcomes, including a path without
a binding. Only outcomes referring to the same object join as that object;
different or unresolved outcomes remain unknown. A join of distinct outcomes
remains unknown before annotation inference; an ordinary unresolved right-hand
side retains the existing annotation contract. Recursive prefix inference retains
an ambiguous witness when its active right-hand side or a preceding candidate
depends on loop, exception or pattern-selection control that has not been modeled.
Nonrecursive inference retains the existing treatment of those controls.
Ambiguity propagates through recursive reads of that same binding during the
current inference, so a surrounding assignment cannot hide it with an annotation.
Dependent names use the active expression's explicit ``SourceValueScope`` branch
context, rather than a cached result that joins the entire scope. Contextual
values retain a reference to the canonical source name and its definition.
Branch facts belong to that expression and structural owner; another function
call starts from its own native parameter epoch, without ambient transport.
Decorators, headers and defaults retain their creator's branch context; function
and lambda bodies begin a separate control context. Assignment metadata comes
from that same source-index pass, including header, walrus and comprehension
bindings. An assignment without source-index provenance, such as one in an
independently parsed expression, carries no branch facts and keeps Rope's
existing unconditional inference. A recorded loop, exception or
pattern-selection context likewise keeps its existing nonrecursive inference
semantics. This dependency-context
capability is under qualification and does not yet establish consumer acceptance.

Reassigning a formal parameter retains its original ``ParameterName`` in function
scope, headers and keyword bindings. Source assignments are separate value facts
holding that parameter by reference; raw parameter values, passed-object queries
and definition locations keep their original contracts. ``SourceValueScope``
looks up those facts at the exact source ``Name`` node and returns a
``SourceValueName`` whose source identity is the original parameter. A read sees
only writes whose real right-hand side ends before the read starts; its own
right-hand side and future writes are excluded. An annotation without a value is
not a parameter write. Header and walrus writes join the same ordered facts
without replacing the formal binder. Only a proven path with no preceding write reads the
current argument value; missing provenance, unresolved writes and ambiguous
paths stay unknown. These contextual values are inferred without populating the
full-binding cache, and another native call supplies its own argument epoch.
For a generic function or a method of a generic class, the source context's
structural scope authenticates the owning function. Its lexical environment is
retained separately so type parameters remain visible during contextual reads.
Occurrence discovery unwraps only native ``SourceValueName`` instance views,
including nested views, before querying the original parameter's passed objects.
The original parameter identity and ordinary instance inputs remain unchanged.
The inference boundary, arm context and ambiguity state are restored on exit,
including failures; a prefix value never replaces
the full binding's cached object. This preserves native name and definition
identity, the existing treatment of unknown values and cycles, and annotation
inference. It does not select a convenient known branch or invalidate other module
facts.

Module-level assignments to source-function attributes belong to the existing
native module event pass. Their receiver and value must use the bindings in
effect at that event, retaining object identity through aliases, later shadowing
and reassignment. An attributed function remains a function: protocols such as
``__mro_entries__`` consume its assigned attribute rather than a substituted class.
During module construction, unresolved lexical lookups reach the native builtin
namespace without reopening the module's still-in-progress attribute inventory.
Conditional or ambiguous writes retain an explicit unresolved witness; a missing
attribute cannot be manufactured to hide an unproved write. This capability must
reuse the native module and binding lifecycle, without a second source scan,
attribute index or persistent cache. Qualification against real consumers is
pending; the declaration of this contract does not attest implementation.
The current event capture covers a single direct, unconditional assignment to an
attribute of a directly declared module function. Alias receivers, conditional
writes and chained targets still require the temporal binding capability and
separate qualification; this initial cut does not establish their acceptance.
If a known function's attribute is overwritten by an unsupported conditional or
chained event, that event replaces the previous value with an existing native
``EvaluatedName`` carrying its module and line. Consuming it raises ``RopeError``
with that event's origin instead of publishing the old value as definitive.
A later supported unconditional write can replace this unresolved event.

When evaluating a declared base raises, Rope re-raises that same exception
with its original traceback. Its ``__notes__`` metadata identifies the source
module, declaring class, base line and base expression; nested failures retain
each declaring context. The metadata is stored on Python 3.10 as well, without
requiring ``BaseException.add_note``. Python 3.11 and later render these notes
with the traceback. This diagnostic neither substitutes a base nor establishes
that the ancestry or a consuming refactoring succeeded. If formatting the source
context itself fails, that secondary failure is recorded as a note without
replacing the original exception.

To diagnose a real source graph without importing its application, run
``make source-ancestry REQUEST=/absolute/request.json``. The request provides
``root``, ``python_path`` (a list of source search directories), and ``targets``
(a list of objects with ``module`` and ``attributes``). The native project reports
its elected resources, bases and unresolved expression witnesses as JSON. For
unresolved bases it identifies the inferred source binding and whether that
object exposes the native ``__mro_entries__`` protocol. For source subscription
hooks it also reports native parameters, local assignments,
return expressions and directly assigned source-callable frames. These frames
describe inferred values; they do not execute the analyzed package.
Subscription-hook frames also compare recorded writes to formal parameters with
the effective native binder and the inferred right-hand-side value, using the
existing source index rather than another traversal.
They report individual source-position reads separately from raw formal values,
so retaining a parameter's identity cannot be mistaken for losing its writes.
An optional ``frames`` list, with the same module/attributes addressing, reports
selected source-function frames after ancestry inference in that same project,
including each local assignment expression's inferred value.
For a selected frame, ``preassignment_names`` optionally compares the original
binding, its individually invalidated inference, and the last assignment under
a native temporary scope containing only earlier assignments of that name.
This controlled diagnostic supplies no expected object and changes no source;
its result is separate from the unmodified ancestry witness.
Search directories are analysis inputs, not additions to the diagnostic interpreter's
``sys.path``. Native errors propagate instead of substituting another provider.
An optional ``bindings`` list addresses native symbols in the same way, without
requiring class ancestry. Assigned call expressions report their receiver,
callable, arguments and inferred result, allowing an unresolved factory boundary
to be inspected without swallowing the failing ancestry operation.

``make source-fixture`` executes only the maintained diagnostic example
``ropetest.source_ancestry_fixtures`` with this checkout's interpreter. It
reports the CPython identities and ancestry of its assignment-flow examples.
Analyze that same module separately with ``source-ancestry`` to compare native
inference with the language runtime. This distinct command never imports an
application supplied through an ancestry request.


Making A Project
----------------

The first thing you should do is make a project:

.. code-block:: python

  import rope.base.project


  myproject = rope.base.project.Project('/path/to/myproject')

It's good to know that:

* A project is a folder in the file-system.
* It can contain anything.
* Rope searches for python modules and packages inside a project when
  needed.
* Refactorings only change files and folders inside the project that
  has been passed to them.
* Out of project modules that are imported from a module inside a
  project are handled but never changed by refactorings.
* Rope makes a rope folder inside projects.  By default the name of this
  folder is ``.ropeproject``, but that can be changed using the
  constructor's ``ropefolder`` parameter. Passing ``None`` prevents rope
  from making this folder.
* Rope uses the ``.ropeproject`` folder for things like saving object
  information and loading project configurations.
* Project preferences can be configured by passing options to the
  constructor or in ``.ropeproject/config.py``.  See the default
  ``config.py``, ``rope.base.default_config`` module, for more
  information.
* All configurations that are available in the ``config.py`` file can
  be specified as keyword parameters to the ``Project`` constructor.
  These parameters override the ones in the ``config.py`` file.
* Each project has a set of ignored resource patterns. You can use it
  to tell rope to ignore files and folders matching certain patterns.
* The ``.ropeproject`` folder can be safely copied in other clones of
  a project if you don't want to lose your objectdb and history.


Library Utilities
-----------------

The `rope.base.libutils`_ module provides tools that make using rope as a
library easier.  We'll talk more about this module later.


What Are These `Resource`\s?
----------------------------

In rope, files and folders in a project are accessed through
``rope.base.resources.Resource`` objects.  It has two subclasses
``File`` and ``Folder``.  What we care about is that refactorings and
``Change``\s (we'll talk about them later) use resources.

There are two options for creating a ``Resource`` for a path in a project.
The first approach uses the ``Project.get_resource()`` method.

.. code-block:: python

  from rope.base import project


  myresource = myproject.get_resource('/path/to/resource')

However, it's preferable to use the ``libutils.path_to_resource()``
function, because it's more flexible and offers a unified way to create
resources.  It takes a ``project`` and ``path`` as parameters with an
optional ``type``.  The ``type`` parameter, with values ``file`` or
``folder``, can create a resource for an object that doesn't exist yet.

.. code-block:: python

  from rope.base import libutils


  myresource = libutils.path_to_resource(myproject, '/path/to/resource')


Consider we have a resource.  How can we know anything about it? The
answer is to use its ``path`` and ``real_path`` attributes.
``Resource.real_path`` is the absolute path of the resource in the
file-system.  The ``Resource.path`` attribute contains the address of a
resource relative to the project's root.


Performing Refactorings
-----------------------

As a short example of performing refactorings, we'll show how to extract
a variable from a file.  First we need the ``Resource`` object that
points to a file in a project:

.. code-block:: python

  resource = libutils.path_to_resource(myproject, '/path/to/my/module.py')

Now we can make our Refactoring class:

.. code-block:: python

  from rope.refactor.extract import ExtractVariable


  extractor = ExtractVariable(myproject, resource, start, end)

Where ``start`` and ``end`` are the offsets of the region to extract in
``resource``.  Be careful when calculating the offsets.  DOS
line-endings and multi-byte characters are considered to be one
character.  This is actually easier for IDEs, since most GUI libraries
handle those cases for you.

Next, the IDE ask the user to configure refactoring options, like
specifying the name of the extracted variable.

After that, we can calculate the changes:

.. code-block:: python

  changes = extractor.get_changes('extracted_variable')

Each refactoring returns a ``rope.base.change.Change`` object that holds
the changes it made.  Calculating those changes can be time consuming.
See the `rope.base.taskhandle.TaskHandle`_ section for measuring its
progress or interrupting it.


Previewing And Performing Changes
---------------------------------

As mentioned in the last section each refactoring returns a
``rope.base.change.Change`` object.  Now how can we know what it
contains and how to perform it?

*Previewing*:

You can use ``changes.get_description()`` to get a preview. It is useful
when you don't care much about the format.  Otherwise you can use the
``changes`` object directly.  See the documentation in
``rope.base.change`` module.

*Performing*:

The easiest way for performing the refactoring is to use the
`Project.do()`_ method:

.. code-block:: python

  myproject.do(changes)

If you want to perform the changes yourself, you have two options.
Note that the main reason for performing the changes manually is
handling version control systems that are not supported by rope.

1. The first approach is to use `rope.base.fscommands`_ (see `Writing A
   FileSystemCommands`_).  The changes can be performed as before using
   `Project.do()`_.

2. The second approach is to perform the changes manually based on the
   returned ``changes`` object (again see the documentation in
   ``rope.base.change`` module).  If this approach is used you cannot undo
   the refactoring using ``project.history.undo()``.

*Updating Open Buffers In IDEs*:

Usually editors need to reload the files changed by rope.  You can use
``Change.get_changed_resources()`` to get the list of resources that
need to be reloaded.


Validating The Project
----------------------

When using rope as a library, you probably change the files in it in
parallel (for example in IDEs).  To force rope to invalidate cached
information about resources that have been removed or changed outside
rope, you should call the `Project.validate()`_ method.  You can pass a
resource to this method.  For example:

.. code-block:: python

  myproject.validate(resource)

This validates all files and directories in resource.  Call this
function every time you want use rope (i.e., before performing
refactorings).


Performing Static Object Analysis
---------------------------------

One of the greatest strengths of rope is its Static Object Analysis
(SOA). It analyzes function calls and assignments to collect the types
of objects passed to the function. Rope uses the collected data to infer
the type of function parameters, return values, and the objects stored
in built-in containers. The function
``rope.base.libutils.analyze_modules()`` performs SOA on all modules in
the project. It is recommended that you call this function occasionally,
and especially before performing large refactorings. Note that analyzing
all modules of a project may take a long time.

If you have ``automatic_soa`` set, which instructs rope to analyze the
changed scopes of modules, then you should report the changes by calling
``rope.base.libutils.report_change()`` when saving files, as follows:

.. code-block:: python

  # Save the new contents.
  old_contents = resource.read()
  resource.write(new_contents)

  # Inform rope about the change.
  libutils.report_change(myproject, path, old_contents)

Note, however, that the use of ``automatic_soa`` is discouraged, because it may
slow down saving considerably.


Function Parameter Information
------------------------------

For ordinary functions and methods, ``PyFunction.get_parameters()`` includes
positional-only and keyword-only bindings.  A ``ParameterName.index`` is an
object slot, not a position in the source signature.  The regular slots are
ordered as positional-only, positional-or-keyword, then keyword-only;
``*args`` and ``**kwargs`` bindings follow them.  Signature separators do not
occupy slots.

``get_param_names(special_args=False)`` returns the regular names in this
order.  ``get_parameter_layout()`` returns a tuple of ``(kind, name)`` pairs
for all bindings, with kinds ``posonly``, ``positional``, ``kwonly``,
``vararg``, and ``kwarg``.  Use ``get_positional_param_names()`` and
``get_keyword_param_names()`` when matching positional and keyword
arguments.  In particular, a keyword with the same name as a positional-only
parameter can belong to ``**kwargs`` and is not a reference to that parameter.

``get_parameter_defaults()`` maps names to their default-expression AST
nodes.  Required parameters are absent from this mapping; an explicit
``=None`` has an AST node.  Defaults belong to the definition's enclosing
scope.  These APIs describe bindings and do not serialize a modified signature.
They do not provide a general annotation-expression scope model; existing
same-name annotation shadowing remains a separate limitation.

Positional Change Signature operations, Introduce Parameter, Inline Parameter,
and Move Method raise ``RefactoringError`` for signatures containing positional-only
or keyword-only parameters before generating changes. Explicit keyword-only
``ArgumentAdder`` operations preserve modern headers and analyze every resource
the caller selected. Import-connected components classify internal provenance;
they never exclude selected consumers from validation or rewriting.
When a multiline header or call closes on its own line, additions retain that
layout and the existing parameter indentation. A missing separator is inserted
at the preceding argument's syntactic end, preserving its trailing comment;
new keywords before ``**kwargs`` retain their own lines as well.

For disconnected source scopes, an unresolved declared callback parameter has no
target effect to prove; its arguments still require namespace-absence proof.
Unresolved attribute, subscription, factory and dynamic-import consumers remain
fail-closed across the full selected resource boundary.
Import-connected public scopes remain part of that boundary even without a
local invocation; an idle unresolved callback is not an effect contract. Native
integer operators are distinguished by the SDK's actual builtin binding when
analyzing numeric effects, while user-defined/external operators remain checked.
Required additions build the import-connected effect boundary. Defaulted
additions preserve existing call arity and omit unrequested keyword values, so
they retain native occurrence/decorator validation and compilation without an
inactive required-effect inference pass.
The single standard-library ``contextlib.contextmanager`` decorator is
authenticated by its native declaration and forwards the added keywords to
the original generator, including bound methods. Imported aliases retain that
identity; local homonyms and unproved decorator stacks remain refused.

Use Function refuses keyword-only parameters. Existing positional-only Inline Method calls remain
supported, while keyword-only Inline Method calls are refused.  Call inference
keeps unknown ``*args`` and ``**kwargs`` expansions conservative.

Local to Field requires a named positional receiver.  It refuses methods with
no positional parameters and static methods, while retaining instance-method
and class-method field conversions.


Closing The Project
-------------------

`Project.close()`_ closes a project's open resources.  Always call this
function when you don't need a project anymore:

.. code-block:: python

  myproject.close()


``rope.base.libutils``
======================

The ``rope.base.libutils`` module contains functions that make life
easier for building refactoring tools. In some cases, the functions
offer a unified way to access or create objects. You're encouraged to
use ``rope.base.libutils`` functions whenever possible, because the APIs
here may not be as volatile as class methods.


``libutils.analyze_module()``
------------------------------

Perform static object analysis on a Python file in the project. Note,
this may be a very time consuming task.

.. code-block:: python

  libutils.analyze_module(myproject, resource)


``libutils.analyze_modules()``
------------------------------

Perform static object analysis on all Python files in the project. Note
that it might take a long time to finish.

.. code-block:: python

  libutils.analyze_modules(myproject)


``libutils.get_string_module()``
--------------------------------

Returns a ``rope.base.pyobjects.PyModule`` object for the code string.
An optional ``resource`` argument can be specified for the resource this
code is associated with. If ``force_errors`` is ``True``, then
``rope.base.exceptions.ModuleSyntaxError`` is raised when the code has
syntax errors. Otherwise, syntax errors are silently ignored. Note that
``force_errors`` overrides the ``ignore_syntax_errors`` project
configuration flag.

.. code-block:: python

  pymodule = libutils.get_string_module(myproject, source)


``libutils.get_string_scope()``
-------------------------------

Get the ``rope.base.pyscopes.GlobalScope`` object for the code string.
This is the outermost scope of the code encompassing the whole module.

.. code-block:: python

  scope = libutils.get_string_scope(myproject, source)


``libutils.is_python_file()``
-----------------------------

Returns ``True`` if the resource is a Python file.

.. code-block:: python

  libutils.is_python_file(myproject, resource)


``libutils.modname()``
----------------------

Retrieves the dotted path string to the module that contains that given
resource.

.. code-block:: python

  # If resource is 'path/to/resource.py' relative to the project's root
  # directory, this returns the string: 'path.to.resource'.
  module_name = libutils.modname(resource)


``libutils.path_relative_to_project_root()``
--------------------------------------------

Retrieve the path relative to the project's root directory.

.. code-block:: python

  # Get the path relative to the project's root directory.
  relpath = libutils.path_relative_to_project_root(myproject, path)


``libutils.path_to_resource()``
-------------------------------

Get the resource --- a file or folder --- at the given path. An optional
``type`` argument can be used if the resource doesn't yet exist. The
values for ``type`` are the strings ``'file'`` or ``'folder'``.

.. code-block:: python

  # Resource for an existing file.
  myfile = libutils.path_to_resource(myproject, '/path/to/file.py')

  # Resource for a non-existing folder.
  new_folder = libutils.path_to_resource(myproject, '/path/to/folder', type='folder')


``rope.base.project.Project``
=============================

You can create a project by:

.. code-block:: python

  project = Project(root_address)

Where the ``root_address`` is the root folder of your project.

A project has some useful attributes.  ``Project.address`` is the
address of the root folder of a project.  ``Project.root`` is a
``Folder`` object that points to that folder.


`Project.do()`
--------------

Used to commit changes returned by refactorings:

.. code-block:: python

  project.do(changes)


`Project.history`
-----------------

A ``rope.base.history.History`` object.  You can use its ``undo`` and
``redo`` methods for undoing or redoing changes.  Note that you can use
this only if you have committed your changes using rope.


`Project.validate()`
--------------------

When using rope as a library, you will probably change the files in that
project in parallel (for example in IDEs).  To force rope to validate
cached information about resources that have been removed or changed
outside rope, you should call ``Project.validate()``.  You should pass a
resource to this method.  For example:

.. code-block:: python

  project.validate(project.root)

This validates all files and directories in the project and clears the
cache of all recorded changes.


`Project.close()`
-----------------

Closes a project's open resources.  Always call this function when you
don't need a project anymore.  Currently it closes the files used for
storing object information and project history.  Because some parts of
these files are in memory for efficiency, not closing a project might
put them in an inconsistent state.


`rope.base.fscommands`
======================

The ``rope.base.fscommands`` module implements basic file system
operations that rope needs to perform.  The main reason for the
existence of this module is supporting version control systems.  Have a
look at ``FileSystemCommands`` and ``SubversionCommands`` in the same
module.  If you need other version control systems you can write a new
class that provides this interface.  ``rope.base.project.Project``
accepts an ``fscommands`` argument.  You can use this argument to force
rope to use your new class.

The same interface owns resource queries: ``exists``, ``isfile``,
``isdir``, ``listdir``, ``stat``, and ``realpath``.  A captured filesystem can
therefore keep both reads and directory elections independent of later
disk changes.  Resource observers obtain the original modification and size
indicator from this same ``stat`` port.  Directory enumeration and metadata
errors propagate to the caller.

Resources outside the project root are owned by ``NoProject``.
For a closed analysis, construct ``NoProject(fscommands=captured)`` and
pass it as ``external_project`` to ``Project`` together with the same
``fscommands``.  This keeps the project's ordinary module lookup order
and lexical scopes while binding external reads to the captured
filesystem.  It does not modify the process-wide ``get_no_project()``
instance.  Such read-only projects should use ``ropefolder=None``,
``save_objectdb=False``, and ``save_history=False``.


``.ropeproject`` Folder
=======================

Since version ``0.5``, rope makes a ``.ropeproject`` folder in the
project by default for saving project configurations and data.  The name
of this folder is passed to the constructor if you want to change that.
You can force rope not to make such a folder by passing ``None``.

If such a folder exists, rope loads the ``config.py`` file in that
folder.  It might also use it for storing object information and
history.


`rope.base.pycore.PyCore`
=========================

Provides useful methods for managing python modules and packages.  Each
project has a ``PyCore`` that can be accessed using the
``Project.pycore`` attribute.

``PyCore.run_module()`` runs a resource.  When running, it collects type
information to do dynamic object inference.  For this reason modules
run much slower.

Also ``Pycore.analyze_module()`` collects object information for a
module.  The collected information can be used to enhance rope's
static object inference.

For an undecorated module function stored by a single class-body name
assignment, direct and saved instance accesses retain the receiver.  Inherited
slots and imported functions keep the original function, class slot, and
parameter definitions, so field and keyword renames use those definitions.
Call analysis and saved object records also preserve the bound callable and
receiver across closing and reopening a project.

This inference uses the existing ordinary argument protocol and requires a
positional parameter for the receiver, without positional-only or keyword-only
parameters.  Recognized function writes to an instance, including aliases,
remain unbound.  Override checks cover the storage, receiver, and access
modules; arbitrary writes in other modules, decorated storage classes,
metaclasses, and multiple storage assignments are outside this inference.


`rope.base.taskhandle.TaskHandle`
=================================

A TaskHandle can be used for stopping and monitoring the progress of
time consuming tasks, like some refactorings.  The ``Project.do()`` and
``Refactoring.get_changes()`` methods for most refactorings take a
keyword parameter called ``task_handle``.  You can pass a ``TaskHandle``
object to them.  A ``TaskHandle`` can be used for interrupting or
observing a task.

Always pass ``task_handle`` as keyword argument.  It will always be the
last argument, and new arguments of the refactoring are added before it.

A task might consist of a few ``JobSet``\s.  Each ``JobSet`` performs a
few jobs.  For instance calculating the changes for renaming a method in
a class hierarchy has two job sets: one to find the classes for
constructing the class hierarchy and another to change the occurrences.

The ``TaskHandle.current_jobset()`` returns the most recent ``JobSet``
or ``None`` if none has been started.  You can use the methods of
``JobSet`` for obtaining information about the current job.  So you
might want to do something like:

.. code-block:: python

  import rope.base.taskhandle


  handle = rope.base.taskhandle.TaskHandle("Test Task")

  def update_progress():
      jobset = handle.current_jobsets()
      if jobset:
          text = ''
          # getting current job set name
          if jobset.get_name() is not None:
              text += jobset.get_name()
          # getting active job name
          if jobset.get_active_job_name() is not None:
              text += ' : ' + jobset.get_active_job_name()
          # adding done percent
          percent = jobset.get_percent_done()
          if percent is not None:
              text += ' ... %s percent done' % percent
          print(text)

  handle.add_observer(update_progress)

  changes = renamer.get_changes('new_name', task_handle=handle)

Also you can use something like this for stopping the task:

.. code-block:: python

  def stop():
      handle.stop()

After calling ``stop()``, the thread that is executing the task will
be interrupted by a ``rope.base.exceptions.InterruptedTaskError``
exception.


Refactorings
============

Have a look at ``rope.refactor`` package and its sub-modules.  For
example for performing a move refactoring you can create an object
representing this operation (which will be an instance of e.g.
`MoveMethod`, `MoveModule`, ...) like this:

.. code-block:: python

  from rope.refactor.move import create_move

  mover = create_move(project, resource, offset)

For a nested class, ``create_move`` returns ``MoveClass``. Its
``get_changes(destination_resource, destination_offset=None, resources=None)``
transfers the declaration to a module or, when an offset is supplied, an existing
class. Native references and required imports move with the declaration; the
returned ``ChangeSet`` does not change resources until applied. Unresolved
references, occupied destinations and dependencies on an enclosing class are
rejected before publication.
An optional ``match_filter(occurrence)`` predicate can retain references whose
public access path is maintained by the caller's composed destination; direct
source references otherwise follow the native declaration identity.
Quoted type annotations use the native source-binding index, including nested
forward references. Literal values, annotation metadata, executable strings and
docstrings remain outside this semantic type-reference surface.
Package reexports, alias chains and inherited nested classes retain their native
binding identities; C3 chooses overrides rather than matching names. Explicit
namespace roots and class paths have no policy depth limit. Transfers into an
existing holder normalize self-imports through ImportUtils and preserve evaluated
sibling bases in the destination class's lexical scope.

Where ``resource`` and ``offset`` is the location to perform the
refactoring.

Then you can commit the changes by it using the ``get_changes()``
method:

.. code-block:: python

  project.do(mover.get_changes(destination))

Where the ``destination`` module/package is the destination resource for
move refactoring.  Other refactorings classes have a similar interface.

``MoveMethod.get_class_changes`` plans transfers of static and class methods
to an existing source class. When the source and destination share a module,
their existing module bindings remain in place; the planner must not create a
self-import for those bindings. Function-local bindings are resolved through
the function scope's names, including assignments, while native identity and
collision checks still apply to dependencies outside that scope.
Cross-module moves select imports used by the moved fragment. A fragment that
declares export metadata retains that publication dependency set; unrelated
export metadata from the source module is not imported into a moved method.


List Of Refactorings
--------------------

Here is the list of refactorings rope provides.  (Note that this list
might be out of date.)  For more information about these refactoring see
pydocs in their modules and the unit-tests in the ``ropetest/refactor/``
folder.

* ``rope.refactor.rename``:
  Rename something in the project.  See the example below.

* ``rope.refactor.move``:
  Move a python element in the project.

* ``rope.refactor.restructure``:
  Restructure code.  See the example below.

* ``rope.refactor.extract``:
  Extract methods/variables.

* ``rope.refactor.inline``:
  Inline occurrences of a method/variable/parameter.
  Removing a variable definition can raise ``RefactoringError`` when it would
  discard an unused initializer that is not known to be safe, remove a module
  or class annotation, or leave reads outside the selected occurrences.
  ``remove=False`` keeps the definition while replacing selected reads.
  Selecting resources that exclude the defining module also keeps its
  definition.  Function-local annotations, safe literals, and proven bound
  names remain eligible for removal.

* ``rope.refactor.usefunction``:
  Try to use a function wherever possible.

* ``rope.refactor.method_object``:
  Transform a function or a method to a method object.

* ``rope.refactor.change_signature``:
  Change the signature of a function/method.

* ``rope.refactor.introduce_factory``:
  Introduce a factory for a class and changes all constructors to use
  it.

* ``rope.refactor.introduce_parameter``:
  Introduce a parameter in a function.

* ``rope.refactor.encapsulate_field``:
  Generate a getter/setter for a field and changes its occurrences to
  use them.

* ``rope.refactor.localtofield``:
  Change a local variable to field.

* ``rope.refactor.topackage``:
  Transform a module to a package with the same name.

* ``rope.refactor.importutils``:
  Perform actions like organize imports.


Refactoring Resources Parameter
-------------------------------

Some refactorings, restructure and find occurrences accept an argument
called ``resources``.  If it is a list of `File`\s, all other
resources in the project are ignored and the refactoring only analyzes
them. If it is ``None`` all python modules in the project will be
analyzed.  Using this parameter, IDEs can let the user limit the files
on which a refactoring should be applied.

When renaming a namespace package directory without an ``__init__.py``,
the default project-wide operation also moves the directory. With an
explicit resource list, the directory moves only when all of its Python
files are selected and the package has at least one Python file. Selecting
only importing modules updates those files while leaving the directory
in place, as with an ordinary package whose initializer is not selected.


Examples
========

Rename
------

Rope follows a single unconditional assignment such as ``Holder.value = Item()``
when both classes are defined at module level in the same module and the value
has ordinary data lookup behavior. Imported names in a class body retain their
original source identity when the corresponding class attribute is replaced.

Repeated or conditional writes, early or deferred reads, class rebinding,
inheritance, and custom attribute lookup can leave the value uncertain. For
these modeled writes, a potentially affected rename raises
``rope.base.exceptions.RefactoringError`` before producing changes. This
analysis is conservative and may refuse an otherwise safe rename; it does not
infer arbitrary factories, descriptors, or dynamic cross-module assignments.

Using rename refactoring:

.. code-block:: python

  # Creating a project
  >>> from rope.base.project import Project
  >>> project = Project('.')

  # Working with files to create a module
  >>> mod1 = project.root.create_file('mod1.py')
  >>> mod1.write('a_var = 10\n')

  # Alternatively you can use `generate` module.
  # Creating modules and packages using `generate` module
  >>> from rope.contrib import generate
  >>> pkg = generate.create_package(project, 'pkg')
  >>> mod2 = generate.create_module(project, 'mod2', pkg)
  >>> mod2.write('import mod1\nprint(mod1.a_var)\n')

  # We can use `Project.find_module` for finding modules, too
  >>> assert mod2 == project.find_module('pkg.mod2')

  # Performing rename refactoring on `mod1.a_var`
  >>> from rope.refactor.rename import Rename
  >>> changes = Rename(project, mod1, 1).get_changes('new_var')
  >>> project.do(changes)
  >>> mod1.read()
  u'new_var = 10\n'
  >>> mod2.read()
  u'import mod1\nprint(mod1.new_var)\n'

  # Undoing rename refactoring
  >>> project.history.undo()
  ...
  >>> mod1.read()
  u'a_var = 10\n'
  >>> mod2.read()
  u'import mod1\nprint(mod1.a_var)\n'

  # Cleaning up
  >>> pkg.remove()
  >>> mod1.remove()
  >>> project.close()


Restructuring
-------------

The example for replacing occurrences of our ``pow`` function to ``**``
operator (see ref:`overview:Restructurings`):

.. code-block:: python

  # Setting up the project
  >>> from rope.base.project import Project
  >>> project = Project('.')

  >>> mod1 = project.root.create_file('mod1.py')
  >>> mod1.write('def pow(x, y):\n    result = 1\n'
  ...            '    for i in range(y):\n        result *= x\n'
  ...            '    return result\n')
  >>> mod2 = project.root.create_file('mod2.py')
  >>> mod2.write('import mod1\nprint(mod1.pow(2, 3))\n')

  >>> from rope.refactor import restructure

  >>> pattern = '${pow_func}(${param1}, ${param2})'
  >>> goal = '${param1} ** ${param2}'
  >>> args = {'pow_func': 'name=mod1.pow'}

  >>> restructuring = restructure.Restructure(project, pattern, goal, args)

  >>> project.do(restructuring.get_changes())
  >>> mod2.read()
  u'import mod1\nprint(2 ** 3)\n'

  # Cleaning up
  >>> mod1.remove()
  >>> mod2.remove()
  >>> project.close()


See code documentation and test suites for more information.


Other Topics
============


Writing A `FileSystemCommands`
------------------------------

The ``get_changes()`` method of refactoring classes return a
``rope.base.change.Change`` object.  You perform these changes by
calling ``Project.do()``.  But as explained above some IDEs need to
perform the changes themselves.

Every change to the file-system in rope is committed using an object that
provides a ``rope.base.fscommands.FileSystemCommands`` interface.  As
explained above in `rope.base.fscommands`_ section, rope uses this
interface to handle different VCSs.

You can implement your own fscommands object:

.. code-block:: python

  class MyFileSystemCommands(object):

    def create_file(self, path):
        """Create a new file"""
        # ...

    def create_folder(self, path):
        """Create a new folder"""
        # ...

    def move(self, path, new_location):
        """Move resource at `path` to `new_location`"""
        # ...

    def remove(self, path):
        """Remove resource"""
        # ...

    def write(self, path, data):
        """Write `data` to file at `path`"""
        # ...

    def read(self, path):
        """Read `data` from file at `path`"""
        # ...

And you can create a project like this:

.. code-block:: python

  my_fscommands = MyFileSystemCommands()
  project = rope.base.project.Project('~/myproject',
                                      fscommands=my_fscommands)


`rope.contrib.codeassist`
-------------------------

The ``rope.contrib`` package contains modules that use rope base parts
and provide useful features.  ``rope.contrib.codeassist`` module can be
used in IDEs:

.. code-block:: python

  from rope.contrib import codeassist


  # Get the proposals; you might want to pass a Resource
  proposals = codeassist.code_assist(project, source_code, offset)

  # Sorting proposals; for changing the order see pydoc
  proposals = codeassist.sorted_proposals(proposals)

  # Where to insert the completions
  starting_offset = codeassist.starting_offset(source_code, offset)

  # Applying a proposal
  proposal = proposals[x]
  replacement = proposal.name

  new_source_code = (source_code[:starting_offset] +
                     replacement + source_code[offset:])

``maxfixes`` parameter of ``code_assist`` decides how many syntax errors
to fix.  The default value is one.  For instance:

.. code-block:: python

  def f():
      g(my^

  myvariable = None

  def g(p):
      invalid syntax ...

will report ``myvariable``, only if ``maxfixes`` is greater than 1.

``later_locals``, if ``True``, forces rope to propose names that are
defined later in current scope.  It is ``True`` by default.  For
instance:

.. code-block:: python

  def f():
      my^
      myvariable = None

will not report ``myvariable``, if ``later_locals`` is ``False``.

See pydocs and source code for more information (other functions in
this module might be interesting, too; like ``get_doc``,
``get_definition_location``).

For PEP 695 type aliases, ``PyName.get_definition_location()`` retains the
declaring module and first binding line in module, function, and class scopes.
Imported aliases preserve that declaration location. Reading this metadata does
not evaluate the lazy alias value or substitute its right-hand side for the alias.
Aliases declared inside constructors and methods remain local bindings, not
instance attributes.


`rope.contrib.findit`
---------------------

``findit`` module provides ``find_occurrences()`` for finding
occurrences of a name.  Also the ``find_implementations()`` function
finds the places in which a method is overridden.


`rope.contrib.autoimport`
-------------------------

This module can be used to find the modules that provide a name.  IDEs
can use this module to auto-import names.  ``AutoImport.get_modules()``
returns the list of modules with the given global name.
``AutoImport.import_assist()`` tries to find the modules that have a
global name that starts with the given prefix.


There are currently two implementations of autoimport in rope, a deprecated
implementation that uses pickle-based storage
(rope.contrib.autoimport.pickle.AutoImport) and a new, experimental one that
uses sqlite3 database (rope.contrib.autoimport.sqlite.AutoImport). New and
existing integrations should migrate to the sqlite3 storage as the pickle-based
autoimport will be removed in the future.


`rope.contrib.autoimport.sqlite`
--------------------------------

Currently, the sqlite3-based only stores autoimport cache in an in-memory
sqlite3 database, you can make it write the import cache to persistent storage
by passing memory=False to AutoImport constructor. This default will change in
the future, if you want to always store the autoimport cache in-memory, then
you need to explicitly pass memory=True.

It must be closed when done with the ``AutoImport.close()`` method.

AutoImport can search for a name from both modules and statements you can import from them.

.. code-block:: python

  from rope.base.project import Project
  from rope.contrib.autoimport import AutoImport

  project = Project("/path/to/project")
  autoimport = AutoImport(project, memory=False)
  autoimport.generate_resource_cache()  # Generates a cache of the local modules, from the project you're working on
  autoimport.generate_modules_cache()  # Generates a cache of external modules
  print(autoimport.search("Dict"))
  autoimport.close()
  project.close()

It provides two new search methods:
 -  search_full() - returns a list of mostly unsorted tuples. This has itemkind and source information.
 -  search() - simpler wrapper around search_full with a basic sorting algorithm


Source binding environments
---------------------------

The structural scope of an expression and the environment in which its names
are resolved can differ. Function annotations use their declaration or
annotation environment; lambda parameters and comprehension targets have their
own bindings. The existing ``GlobalScope.get_inner_scope_for_offset(offset)``
continues to return the structural scope. Its explicit
``get_structural_scope_for_offset(offset)`` alias has the same behavior.

A module's ``get_source_binding_index()`` provides source identity queries:

The public getter and direct ``SourceBindingIndex`` construction return a complete
index. Internal definition and expression queries share that same module index,
but may defer function bodies until their lexical source is queried. A full public
index request or public binding-scope enumeration completes those bodies before
returning, including nested annotations whose binding parent is the module.
Body demands include decorators on the body's first declaration. Parsing and native C3
resolution are unchanged. Modules containing assignment expressions remain eager:
their nested headers can write bindings into enclosing or global scopes.

.. code-block:: python

  pymodule = project.get_pymodule(resource)
  index = pymodule.get_source_binding_index()
  context = index.context_at(offset)
  environment = context.environment
  structural_scope = context.structural_scope
  binding = index.binding_for_token(offset)

``context_for_node(node)`` resolves a node from that module's AST. Source
queries in ``rope.base.evaluate`` use these environments while keeping source
identities separate from call-time values. A lambda's private argument matcher
handles its own positional, keyword and creation-time default values; it does
not change the ordinary ``Arguments`` or ``PyFunction`` parameter protocols.
Unknown argument expansion or conflicting values remain unknown.

When a directly assigned class attribute and a directly assigned instance
attribute in ``__init__`` hold different lambdas, attribute value views select
the class or initialized instance value independently. This selection does not
replace their source names or change the ordinary class attribute protocol.

Ordinary positional-only and keyword-only parameters are represented by
distinct readable source names, so their bodies do not fall back to same-named
outer variables. Their call inference and signature rewriting are outside this
model's supported range. Rename refuses edits to these parameter bindings, and
introduce-parameter refuses to rewrite such a signature. Queries still return
definition locations and an unknown value. An unresolved generic annotation
binding likewise refuses a potentially affected edit before any source changes.

The model does not provide arbitrary dynamic class namespace inference. For
example, assigning a lambda to ``Owner.callback`` after the class definition
can leave attribute inference unknown; source binding identity is not a promise
of complete dynamic value inference. Inline safety for deferred annotations and
initializer removal is outside the source model's new consumer scope.

Cross-Project Refactorings
--------------------------

``rope.refactor.multiproject`` can be used to perform a refactoring
across multiple projects.

Usually refactorings have a main project.  That is the project that
contains the definition of the changing python name.  Other projects
depend on the main one, and the uses of the changed name in them should
be updated.

Each refactoring changes only one project (the project passed to its
constructor).  But we can use the ``MultiProjectRefactoring`` proxy to
perform a refactoring on other projects, too.

First we need to create a multi-project refactoring constructor.  As
an example consider that we want to perform a rename refactoring:

.. code-block:: python

  from rope.refactor import multiproject, rename


  CrossRename = multiproject.MultiProjectRefactoring(rename.Rename,
                                                     projects)


Here ``projects`` is the list of dependent projects.  It does not
include the main project.  The first argument is the refactoring class
(such as ``Rename``) or factory function (like ``create_move``).

Next we can construct the refactoring:

.. code-block:: python

  renamer = CrossRename(project, resource, offset)

We create the rename refactoring as we do for normal refactoings.  Note
that ``project`` is the main project.

As mentioned above, other projects use the main project. Rope
automatically adds the main project to the python path of other
projects.

Finally we can calculate the changes.  But instead of calling
``get_changes()`` (which returns main project changes only), we can
call ``get_all_changes()`` with the same arguments.  It returns a list
of ``(project, changes)`` tuples.  You can perform them manually by
calling ``project.do(changes)`` for each tuple, or use
``multiproject.perform()``:

.. code-block:: python

  project_and_changes = renamer.get_all_changes('newname')

  multiproject.perform(project_and_changes)


Unchanged source value descriptors
---------------------------------

Native attribute inference preserves the identity of a value returned unchanged
by a source descriptor. This applies when the source constructor stores its
argument directly and ``__get__`` returns that stored attribute, for both class
and instance access. Inherited exports and keyword constructor arguments retain
the same identity. Descriptors whose constructor or getter transforms the value
do not acquire this identity proof.

The existing override guard consumes the source binding index's attribute-write
inventory. That lazy inventory belongs to one immutable parsed module snapshot;
recapturing a changed resource creates a new index rather than reusing previous
write observations. Declaration identities and refactoring safety remain owned
by the native binding and occurrence engines.
