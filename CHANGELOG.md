# **Upcoming release**

- ...

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
