# __Upcoming release__

- Branch-sensitive assignment inference takes the body of
  `if typing.TYPE_CHECKING:` (PEP 484), followed through import aliases and
  re-exports. Names assigned only there, such as class-body `TypeAlias`
  re-exports, resolve, and class bases read through them enter the MRO.

# Release 1.15.2+dc.7

- Integrate the latest upstream master while retaining upstream 1.15.2 as the
  published base. Preserve typed project APIs, UTF-8 function signatures, star
  imports during inlining, and native try-statement regions.
- Bind a PEP 613 TypeAlias assignment to its value.
- Reject class method transfers when the destination exposes a mutable
  builtins namespace during class construction.
- Resolve references in string-sequence declarations before later rebindings
  or extensions of the referenced name.
- Moving a global rewrites a consumer's relative import of the moved name
  (`from .origin import Name`, `from . import origin`) like the absolute form;
  the stale relative import no longer survives the move. Imports through a
  package initializer and aliased from-imports follow the move as well.
- `Project(..., config_files=False)` takes preferences only from the supplied
  `prefs` over the defaults, without reading `pyproject.toml`, the ropefolder
  `config.py` or the global configuration.
- `SourceBindingIndex.assignment_string_sequence` reads the binding Python
  keeps: the last direct assignment of the name, extended by every later
  `name += [...]` of literal strings. A bare annotation never rebinds it, and a
  non-literal extension yields `()`. It previously returned the first
  assignment, which diverged from the module's effective `__all__`.
- #859 Fix `find_definition`/Rename not resolving `async def` methods called via `self` (@gadievron)
- #895 patchedast Starred and keyword now consumes their syntactically expected and ** (@lieryan)
- #896 patchedast cleanup and refactoring (@lieryan)
- #905 Ignore `node_modules` directories by default when scanning project files and source folders. (@marcoeangeli)
- #922 Classify autoimport project sources by path containment (@marlon-costa-dc)
- #926, #929 Raise RefactoringError instead of IndexError/ModuleSyntaxError when extracting an empty or whitespace-only region (@aliassar)
- #933 Add type annotations to project.py (@lieryan)
- #119, #928 Fix IndexError in rename and find occurrences when a `from` import is the last thing in a module without a trailing newline (@mcepl)
- #921 Patch the else suite of try statements that also have a finally (@marlon-costa-dc)
- #937 Preserve non-ASCII argument expressions and default values when changing function signatures (@Jinyong-Li)
- #826, #940 Keep star imports in other modules when inlining a function or method (@chinghar)
- #948, #949 Don't treat string prefixes such as the `f` in `f"..."` as occurrences when renaming a variable named `f`, `b`, `u`, `rf`, etc. (@aliassar)

# Release 1.15.2+dc.6

- A compound class base (`s[T]`, `pkg.Base`) resolves its root name as it is
  bound at the class statement. A later facade alias (`s = Derived`) no longer
  makes the class its own base, which recursed until `RecursionError`.

# Release 1.15.2+dc.5

- Module-identity planning skips the write scan of function and class scopes
  that declare no `global` names, whose writes cannot reach module identity:
  26% less time in `externaldata._plan_context` on large modules.

# Release 1.15.2+dc.4

- `AutoImport.generate_cache` and `generate_modules_cache` start their worker
  processes with `forkserver` (or `spawn` where it is unavailable) instead of
  the platform default. Forking a process that runs other threads can
  deadlock the child, and Python 3.12+ warns on every such fork.

# Release 1.15.2+dc.3

- `MoveMethod.get_class_changes` proves that a class transfer keeps program
  behaviour. Defaults, and annotations still evaluated eagerly, must be
  literals. The destination's metaclass must be `type`. Its import-time code
  must not rebind names through `globals()`, `vars()`, `locals()`, `exec`,
  `eval` or the builtins module. A reference that runs before the destination
  class exists is refused.
- A same-module transfer to an enclosing class now keeps module-level
  bindings it reads, when the binding's single declaration is unchanged and
  the method does not declare the name global or nonlocal.

# Release 1.15.2+dc.2

- `SourceBindingIndex.context_for_node` spans only nodes of its own module's
  AST. A node from another AST gets no context without reading this source;
  before, its columns could fall inside a UTF-8 code point and raise
  `UnicodeDecodeError` (non-ASCII modules, through `evaluate.eval_node`).

# Release 1.15.2+dc.1

- Move the fork base to upstream release 1.15.2 (integrated by merge commit),
  which carries the 1.15.1 DOA channel credential hardening in `runmod.py`.
  The local suffix restarts at 1 for the new upstream base.
- Add `MoveMethod.get_instance_class_changes()` to transfer an
  identity-decorated instance handler into a source class, rewriting
  `self.member` accesses through explicit `receiver_rewrites`.
- Materialize function bodies of definition bindings on native query demand.
- Include the `annotations` type-hinting provider in the package.

# Release 1.15.0+dc.12

- Never offer the literal pieces or format specs of an f-string as similar
  finder matches: patchedast gives them no region, so a literal pattern equal
  to one of them raised `AttributeError`. Expressions inside the replacement
  fields still match.

# Release 1.15.0+dc.11

- Memoize `Scope.get_region()` like `get_end()` and `get_logical_end()`, so
  offset lookups stop re-scanning decorator tokens for every subscope. Scopes
  are rebuilt with their module, so a changed source never sees a stale region.

# Release 1.15.0+dc.10

- Tokenize a module once however many names are searched in it, caching the
  name index by source text.

# Release 1.15.0+dc.9

- Memoize offset resolution on each module until the project data changes,
  so repeated occurrence searches no longer re-resolve the same offset. Any
  change to a loaded resource retires every memo.

# Release 1.15.0+dc.8

- Type `rope.base.utils.saveit` so decorated methods and properties, such
  as `Project.pycore`, keep their return type for type checkers.
- Keep analysing classes whose hierarchy Python refuses to create, as upstream
  does: their attributes, `super()`, `type()` and type hints follow the
  declared bases. Only `AbstractClass.get_mro()` raises
  `InconsistentHierarchyError`; the new `get_consistent_mro()` returns `None`
  for such classes instead.
- Restore `rope.base.oi.type_hinting.utils.get_mro()`.
- Infer `super()` along the method resolution order and bind the real
  receiver of calls made through it.
- Restore the upstream source form of lines that a linter had rewritten
  without changing behavior, and keep comments in English.
- Infer assignments without source-index provenance, such as those of an
  independently parsed expression, as unconditional assignments again.
- Store literal values in the object database the way their builtin base
  class is stored, by resolving textual transformations along the MRO.
- Keep static object information for names read through a branch context that
  does not select any of their assignments, and for value overlays of a
  source name.
- Classify evaluated bases by the native `AbstractClass` contract rather than
  equality with metatype markers. An unresolved base must retain its source
  witness without being treated as a class supporting method resolution order.

# Release 1.15.0+dc.7

- Resolve class attributes in C3 method resolution order instead of a
  depth-first walk of the bases, so diamond hierarchies inherit the member
  Python's `__mro__` selects. `AbstractClass.get_mro()` exposes that order.
- Model builtin classes with their runtime bases and `__mro__`, so `object`
  sorts last and a builtin ancestor contributes only the attributes it
  defines itself.
- Select inherited docstring and assignment type hints along the same
  method resolution order instead of a breadth-first walk.
- Keep bases rope cannot evaluate to a class as `UnresolvedBase` markers in
  `AbstractClass.get_bases()` and in the method resolution order instead of
  dropping them; `get_superclasses()` still returns only the classes.
- Raise `InconsistentHierarchyError` for cyclic, repeated, and unmergeable
  bases, which Python refuses to create.

# Release 1.15.0+dc.6

- Classify evaluated bases by the native `AbstractClass` contract rather than
  equality with metatype markers. An unresolved base must retain its source
  witness without being treated as a class supporting method resolution order.

- Infer `super(cls, obj)` along the method resolution order of `cls` past
  `cls` itself instead of as an instance of its first base. Methods and
  classmethods called through it bind the real receiver.

# Release 1.15.0+dc.7

- Resolve class attributes in C3 method resolution order instead of a
  depth-first walk of the bases, so diamond hierarchies inherit the member
  Python's `__mro__` selects. `AbstractClass.get_mro()` exposes that order.
- Model builtin classes with their runtime bases and `__mro__`, so `object`
  sorts last and a builtin ancestor contributes only the attributes it
  defines itself.
- Select inherited docstring and assignment type hints along the same
  method resolution order instead of a breadth-first walk.
- Keep bases rope cannot evaluate to a class as `UnresolvedBase` markers in
  `AbstractClass.get_bases()` and in the method resolution order instead of
  dropping them; `get_superclasses()` still returns only the classes.
- Raise `InconsistentHierarchyError` for cyclic, repeated, and unmergeable
  bases, which Python refuses to create.

# Release 1.15.0+dc.6

- Resolve class-owned PEP 695 aliases from other lazy aliases in the same class,
  including forward declarations and names shadowing module aliases. Conditional
  declarations retain their ambiguous source identity.
- Resolve opaque annotation references through their captured source contexts
  when refactoring checks request them, avoiding duplicate binding resolution
  while constructing the source index.
- Add `match_filter` and `import_filter` to `Restructure`: callables consulted
  for every match found in a module and for the imports added to a changed
  module, so clients select both without overriding private methods.

# Release 1.15.0+dc.5

- Record PEP 695 type-alias declaration locations in module, function, and class
  scopes without evaluating or substituting the lazy alias value.
- Preserve first-binding locations across ordinary assignments, repeated aliases,
  imports, and native renames; verify these contracts against the installed wheel.
- Keep constructor and method aliases local to their declaration scope, without
  polluting instance attributes collected by the target-only visitor.
- Select native setup interpreters independently of ancestor project constraints.

# Release 1.15.0+dc.4

- Patch expressions in the `else` suite before `finally` for both `try` and
  `try`/`except*`, preserving source regions and semantic matching.
- Verify source round-tripping and parenthesized attribute matching against the
  installed wheel as well as the source checkout.
- Initialize the documented source-folder configuration without invoking a
  deprecated private helper, preserving explicit folder selection without warnings.
- Preserve f-string references across supported Python tokenizers and expression
  coordinates for escaped braces and Unicode, adopting the reviewed native fixes.
- Keep autoimport project-relative paths and nested installation roots separate on
  Windows, and scope the metadata task check to its required checks permission.
- Validate published downstream GitHub Release assets through the native installed
  wheel contract, without sending local-version builds to the upstream PyPI publisher.
- Isolate installed-wheel pytest configuration from ancestor projects and inherited
  pytest options while retaining the native test configuration and contracts.

# Release 1.15.0+dc.3

Flext-ecosystem compatibility and robustness over 1.15.0+dc.2:

- Expose a module scope over builtin modules (`BuiltinModule.get_scope` + `BuiltinModuleScope`), so semantic-module consumers recognize C/builtin modules
- Do not require callers to preseed `ignored_resources` when a python path folder inside the root contains site-packages (#756 follow-up); both behaviors carry regression tests

# Release 1.15.0+dc.2

Performance and inference cycle on the 1.15.0+dc.1 line:

- Fix property inference regression from the parameter-bindings adoption: record function calls without resolving the function from its own text, restoring typed attributes on properties (rename no longer misses subclass call sites)
- Resolve external class-data plans once per module entry: single shared plan store, per-owner lazy resolution, attribute readers grouped in one pass, class-binding scan memoized
- Cut the source-binding index build cost (typed node dispatch, slotted contexts, ASCII fast paths in ASTLinesAdapter)
- Skip the opaque-reference scan for modules that never spell the renamed name and modules without class-attribute writes

# Release 1.15.0+dc.1

Fork of upstream rope 1.15.0: adopts the upstream open pull requests
below and adds the datacosmos feature branches.

Upstream pull requests adopted:

- #756 Fix import paths with `site-packages` as part of package name (@last-partizan)
- #790 Fix multiline empty tuple with comment (@apmorton)
- #808 Handle the edge case where an f-string looks like `f"#{some_var}"` (@rlbr)
- #814 Treat packages in `ignored_resources` as non-project files for autoimport (@smheidrich)
- #836, #837 Correct `_const_node_type_names` fallback for Python 3.14+ (@EhteshamSid)
- #848 Fix autoimport.sqlite deriving module names from non-package folders (@deepakganesh78)
- #858 Don't fold source after an f-string with an unmatched literal bracket, Python 3.12+ (@gadievron)
- #859 Recognise `async def` method headers in worder (@gadievron)
- #861, #865 Recognize match pattern captures as assignments (@yangfan-yf-yf)
- #862, #874 Treat type alias statements as name assignments and refuse inlining them (@TanbirRamim)
- #867 patchedast: raise MismatchedTokenError instead of AttributeError (@quazardous)
- #868 patchedast: don't match tokens inside string literals (@quazardous)
- #864, #866 Preserve compound assignments when inlining (@onuracar-dev)
- #876 Fix extraction of nested named expressions (@yangfan-yf-yf)
- #877 Preserve used imports during filtered import cleanup (@yangfan-yf-yf)
- #878 Define functions extracted from a class body before the class (@ethanstoner)
- #881 Preserve original names in external from-imports (@ryanchou1994)
- #879, #880 Fix patchedast region for implicitly-concatenated f-strings (@stevemadere)
- #802, #887 Fix source regions for regular argument annotations (@Strohutt)
- #886, #889 autoimport: track and close SQLite connections across worker threads (@mcepl)
- #827, #892 Preserve subscript index reads during method inlining (@SAY-5)
- #893 Resolve function-local constructor names through their scope (@SAY-5)
- #894 Refuse unsafe inlining into deferred annotations and type parameters (@yangfan-yf-yf)
- #897 Refuse unsafe inlining of lambda-local bindings (@yangfan-yf-yf)
- #898 Preserve positional-only and keyword-only parameter bindings (@yangfan-yf-yf)
- #899 Keep unresolved call keyword labels separate from variables (@yangfan-yf-yf)
- #900 Preserve annotation, lambda and comprehension source bindings (@yangfan-yf-yf)
- #901 Fix field renames after external class data writes (@yangfan-yf-yf)
- #902 Fix namespace package directory renames (@yangfan-yf-yf)
- #903 Preserve initializer behavior when removing inlined variables (@yangfan-yf-yf)
- #904 Bind receivers for ordinary functions stored on classes (@yangfan-yf-yf)
- #905 Ignore `node_modules` directories by default (@marcoeangeli)

Fork contributions (also proposed upstream):

- #844 Detect the JoinedStr end quote from the terminating delimiter (@marlon-costa-dc)
- #882 Match MatchSequence delimiters by tokenizing the node segment (@marlon-costa-dc)
- Find textual occurrence offsets through the tokenizer so rename locates names inside PEP 701 f-strings
- Walk positional-only, keyword-only and annotated parameters in patchedast signatures
- Guard type-hint providers against non-AssignedName pynames and infer `X | Y` union annotations
- Compute scope regions from native AST positions, preserving Unicode identifiers, decorators, and LF, CRLF, and CR newlines
- Honor namespace-package precedence when resolving imports across source folders
- Route project, resource, and observer filesystem queries through the fscommands owner (exists/isfile/isdir/listdir/stat/realpath)
- Model namespace packages as empty modules so scope machinery can walk them
- Discover the compiled extension module used by autoimport tests from the import system

Datacosmos internal:

- Project(external_project=...) and NoProject(fscommands=...) share one captured filesystem so native module resolution survives source-tree changes

# Release 1.15.1

- Change runmod.py to pass DOA channel credential in a more secure manner,
  see GHSA-64m2-4gp9-7cqx (@AliAAlMousa, @lieryan)

# Release 1.15.0

- #850 Update and pin black version in pre-commit and Github Actions (@lieryan)
- #851 Bump supported python version to up to Python 3.14 (@lieryan)
- #852 Implement patchedast handlers for TypeAlias (@lieryan)
- #853 Implement patchedast handlers TypeVar (@lieryan)
- #847 Avoid printing autoimport syntax errors (@yangfan-yf-yf)
- #623, #819, #863 Support MatchOr, MatchSequence, MatchStar (@jheld, @lieryan)
- #870 Add default implementation for is_dir() (@lieryan)
- #872 Fix unicode handling in patchedast (@lieryan)
- #845 Support PEP 695 type parameters on class definitions and type aliases in patchedast (@marlon-costa-dc)
- #849 docs: resolve warnings and update Github Actions versions (@mcepl)
- #835 Tear down tests using python from venv (@aeliton)

# Release 1.14.0

- #787 Add type hints to importinfo.py and add repr to ImportInfo (@lieryan)
- #786 Upgrade Actions used in Github Workflows (@lieryan)
- #785 Refactoring movetest.py (@lieryan)
- #788 Introduce the `preferred_import_style` configuration (@nicoolas25, @lieryan)
- #820 Add explicit sphinx.configuration key (@lieryan)
- #805 Update GHA Python versions by (@lieryan)
- #809 Python3.13 compat (@Nowa-Ammerlaan)
- #818 Adapt conditional for Python 3.14 (@penguinpee)

# Release 1.13.0

- #781, #783 Isolate tests that uses external_fixturepkg into a venv (@lieryan)
- #751 Check for ast.Attributes when finding occurrences in fstrings (@sandratsy)
- #777, #698 add validation to refuse Rename refactoring to a python keyword (@lieryan)
- #730 Match on module aliases for autoimport suggestions (@MrBago)
- #755 Remove dependency on `build` package being installed while running tests (@lieryan)
- #780 Improved function parser to use ast parser instead of Worder (@lieryan)
- #752 Update pre-commit (@bagel897)
- #782 Integrate codecov with GHA (@lieryan)
- #754 Minor type hint improvements (@lieryan)

# Release 1.12.0

- #733 skip directories with perm error when building autoimport index (@MrBago)
- #722, #723 Remove site-packages from packages search tree (@tkrabel)
- #738 Implement os.PathLike on Resource (@lieryan)
- #739, #736 Ensure autoimport requests uses indexes (@lieryan)
- #734, #735 raise exception when extracting the start of a block without the end

# Release 1.11.0

- #710, #561 Implement `except*` syntax (@lieryan)
- #711 allow building documentation without having rope module installed (@kloczek)
- #719 Allows the in-memory db to be shared across threads (@tkrabel)
- #720 create one sqlite3.Connection per thread using a thread local (@tkrabel)
- #715 change AutoImport's `get_modules` to be case sensitive (@bagel897)

# Release 1.10.0

- #708, #709 Add support for Python 3.12 (@lieryan)

# Release 1.9.0

- #624, #693 Implement `nonlocal` keyword (@lieryan)
- #697, #565 Automatically purge autoimport.db when there is schema change

# Release 1.8.0

- #650 Install pre-commit hooks on rope repository (@lieryan)
- #655 Remove unused __init__() methods (@edreamleo, @lieryan)
- #656 Reformat using black 23.1.0 (@edreamleo)
- #674 Fix/supress all mypy complaints (@edreamleo)
- #680 Remove a do-nothing statement in soi._handle_first_parameter (@edreamleo)
- #687, #688 Fix autoimport not scanning packages recursively (@lieryan)

# Release 1.7.0

## Feature

- #548 Implement MoveGlobal using string as destination module names (@lieryan)

## Bug

- #627 Fix parsing of octal literal (@lieryan)
- #643, #435 Fix fstrings with mismatched parens (@apmorton)
- #646 Fix renaming kwargs when refactoring from imports (@apmorton)
- #648 Remove __init__ from import statement when using sqlite autoimport (@bagel897)

## Improvements

- rope.contrib.generate improvements
  - #640 Remove unnecessary eval in generate.py (@edreamleo)
  - #641 Add type annotations for rope.contrib.generate.create_generate() (@edreamleo)

- call_for_nodes() improvements
  - #634 Remove call_for_nodes(recursive) argument (@edreamleo)
  - #642 Add comments & docstrings related to call_for_nodes (@edreamleo, @lieryan)

- Data storage improvements
  - #604 Fix test that sometimes leaves files behind in the current working directory (@lieryan)
  - #606 Deprecate compress_objectdb and compress_history (@lieryan)
  - #607 Remove importing from legacy files with `.pickle` suffix (@lieryan)
  - #611 Implement JSON DataFile serialization (@lieryan)
  - #630 SQLite models improvements (@lieryan)
  - #631 Implement version hash (@lieryan)

## Tech Debt

- #594 Tidy up patchedast (@Alex-CodeLab)
- #595 Global default DEFAULT_TASK_HANDLE (@Alex-CodeLab)
- #609, #610, #612, #613 Fix pyflakes issues (@edreamleo)
- #615 Remove 'unicode' from builtins dict (@edreamleo)
- #616, #621 Remove `file` builtins (@edreamleo)
- #618 Separate pynames and pynamesdef and remove star-import (@edreamleo, @lieryan)
- #620 Remove unused import in occurrences.py (@edreamleo)
- #625 Remove support for deprecated ast nodes (@lieryan)


## Tests/Dev

- #626 Install pre-commit hooks on rope repository (@lieryan)
- #628 Add isort to pre-commit (@lieryan)
- #638 Add a function to identify ast Constant nodes more granularly (@lieryan)

## Docs

- #636 Update readme to reflect 1.0 has been released. (@maxnoe)


# Release 1.6.0

## New features & Enhancements

- #559, #560 Improve handling of whitespace in import and from-import statements (@lieryan)
- #566, #567, #597 Fix variables in kwonlyargs and posonlyargs not being correctly passed to extracted methods (@lieryan)

## Unit Test

- #589, #596 Fix issue with `sample_project()` creating directories where it shouldn't when running tests (@lieryan)
- #547 Add config file for linters
- #593 Remove `only_for` decorator for all python versions less than 3.7 (@edreamleo)

## Tech Debt

- Code quality
  - #546 Remove unused vars in test (@lieryan, @edreamleo)
  - #551, #552 Numerous flake8 linter complaints (@edreamleo)
  - #558 Fix typos (@kianmeng)
  - #583, #584 More consistent import style (@edreamleo)
- Python 2-related tech debt
  - #533 Refactoring to Remove usage of unicode type (@lieryan)
  - #549, #553 Remove rope.base.utils.pycompat (@dreamleo)
  - #555 Fix some python2-isms (@lieryan)
- Rope's AST Wrapper
  - #536, #578 walk does not return a value (@edreamleo)
  - #537, #538 Remove special case code from walk (@edreamleo)
  - #581 Remove functions in rope.base.ast that has functionally identical implementation in stdlib's ast (@lieryan, @edreamleo)
  - #582 Refactoring rope.base.ast and remove rope.base.astutils (@lieryan, @edreamleo)
- pynames and pyobjects
  - #569, #572 rename pynames to pynamesdef in pyobjectsdef.ph (@edreamleo)


# Release 1.5.1

- #531 Add alternative way to retrieve version number from pyproject.toml

# Release 1.5.0

Date: 2022-11-23

- #492 Feat: Global configuration support (@bagel897)
- #519 Move pytest to pyproject.toml (@gliptak, @bagel897)
- #509 Fix read/write analysis of the left-hand side of an augmented assignment (@lieryan)
- #522 Implement patchedast parsing of MatchMapping (@lieryan)
- #514 Fix inlining dictionary with inline comment (@lieryan)


# Release 1.4.0

Date: 2022-10-22

## Bug fixes

- #506, #507 Fix issue with parsing function call args list
- #411, #505 Fix extracting generator without parens
- #18, #510 When the function is a builtin function, the call parameter's name was sometimes incorrectly identified as an AssignedName. This led to rename refactoring incorrectly renaming these parameters.


# Release 1.3.0

Date: 2022-07-29

## Bug fixes

- #496, #497 Add MatMul operator to patchedast
- #495 Fix autoimport collection for compiled modules

## Improvement

- #501, #502 Autoimport improvements


# Release 1.2.0

Date: 2022-04-22

## New feature

- #473 Pyproject.toml support (@bageljrkhanofemus)
- #489 Rope now publishes documentations to rope.readthedocs.org (@bageljrkhanofemus)
- #490 Migrate from setup.py to pyproject.toml (@bageljrkhanofemus)

## Improvement

- #479 Add ABC and type hints for TaskHandle and JobSet (@bageljrkhanofemus)
- #486 Drop Python 2 support (@bageljrkhanofemus, @lieryan)
- #487 Improved value inference of __all__ declaration (@lieryan)
- #424 Add some basic __repr__ to make it easier for debugging (@lieryan)


# Release 1.1.1

## Bug fixes

- #476 Fix rope.contrib.autoimport package missing from release (@bageljrkhanofemus)


# Release 1.1.0

Date: 2022-05-25

## New feature

- #464 Add new autoimport implementation that uses a sqllite3 database, cache all available modules quickly, search for names and produce import statements, sort import statements. (@bageljrkhanofemus)

## Bug fixes

- #419 Fix bug while moving decorated function (@dryobates)
- #439 Fix bug while moving decorated class (@dryobates)
- #461 Fix bug while extracting method with list comprehension in class method (@dryobates)
- #440 Fix bug while inlining function with type hints in signature (@dryobates)

## Deprecation

- The pickle-based autoimport implementation is still the default, but will be deprecated sometime in the future.


# Release 1.0.0

Date: 2022-04-08

## Syntax support

- #400 Drop Python 2.7 support

## Bug fixes

- #459 Fix bug while extracting method with augmented assignment to subscript in try block (@dryobates)


# Release 0.23.0

## Syntax support

- #451, $456 Implement structural pattern matching (PEP634) (@lieryan)
- #458 Improve the heuristic for joining lines when extracting one line
  expression (@lieryan)

## Bug fixes

- #134, #453 Preserve newline format when writing files  (@lieryan)
- #457 Fix extract info collection for list comprehension with multiple targets
  (@lieryan)

## Documentation

- #455 Fix typo (@Jasha10)


# Release 0.22.0

Date: 2021-11-23

## Syntax support

- #443 Implement `yield from` syntax support to patchedast.py

## Bug fixes

- #445, #446 Improve empty tuple and handling of parentheses around tuple
- #270, #432 Fix rename import statement with dots and as keyword (@climbus)

## Misc

- #447 Add Python 3.10 to tests


# Release 0.21.1

Date: 2021-11-11

## Bug fixes

- #441. Start publishing wheel packages to allow offline installs


# Release 0.21.0

Date: 2021-10-18

## Syntax support

- #392, #316 Handle `global` keyword when extracting method (@climbus)
- context manager:
  - #387, #433 Implement extract refactoring for code containing `async with` (@lieryan)
  - #398, #104 Fix parsing of nested `with` statement/context manager (@climbus)
- list/set/dict/generator comprehension scope issues:
  - #422 Added scopes for comprehension expressions as part of #293 (@climbus)
  - #426, #429 Added support for checking scopes by offset as part of #293 (@climbus)
  - #293, #430 Fix renaming global var affects list comprehension (@climbus)
  - #395, #315 Reuse of variable in comprehensions confuses method extraction (@climbus)
  - #436 Fix error `TypeError: 'PyDefinedObject' object is not subscriptable` (@lieryan)
- f-string:
  - #303, #420 Fix inlining into f-string containing quote characters (@lieryan)
- inline assignment/walrus operator:
  - #423 Fix `AttributeError: '_ExpressionVisitor' object has no attribute 'defineds'` (@lieryan)

## Bug fixes

- #391, #376 Fix improper replacement when extracting attribute access expression with `similar=True` (@climbus)
- #396 Fix improper replacement when extracting index access expression with `similar=True` (@lieryan)

## New feature

- #434 Move read() to FileSystemCommands (@lieryan)

## Misc

- #410 Setup all-contributors bot (@lieryan)
- #404 Blacken source code, rope now follows black code style (@climbus)
- #399 Add Github Actions to enforce black code style (@lieryan)
- #403 Remove plain 'unittest' only runner (@lieryan)


# Release 0.20.1

Date: 2021-09-18

## Bug fixes

- Fix caller of `_namedexpr_last()` throwing exception due to returning unexpected list
  instead of boolean


# Release 0.20.0

Date: 2021-09-18

## New feature

- #377 Added the ability to extract method to @staticmethod/@classmethod (@climbus)
- #374 Changed Organize import to keep variables listed in `__all__`
- Change default .ropeproject/config.py to ignore code in folders named
  .venv and venv (@0x1e02)

## Syntax support

- #372 Add extract method refactoring of code containing `exec` (@ceridwen)
- #389 Add extract method refactoring of code containing `async def`, `async for`, and `await`
- #365, #386 Support extract method of expressions containing inline assignment (walrus operator)

## Bug fixes

- #380 Fix list of variables that are returned and/or turned into argument when extracting method in a loop


# Previous releases

[Changelog from pre-0.10.0](https://github.com/python-rope/rope/blob/595af418e7e7e844dcce600778e1c650c2fc0ba1/docs/done.rst).
