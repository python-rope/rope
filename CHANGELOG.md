# **Upcoming release**

# Release 1.2.0

Date: 2022-04-22

# New feature

- #473 Pyproject.toml support (@bageljrkhanofemus)
- #489 Rope now publishes documentations to readthedocs.org (@bageljrkhanofemus)
- #490 Migrate from setup.py to pyproject.toml (@bageljrkhanofemus)

# Improvement

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
