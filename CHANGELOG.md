# **Upcoming release**

# Syntax support

- #392 Add extract method refactoring of code containing `global` (@climbus)

## Bug fixes
- #391, #396 Extract method similar no longer replace the left-hand side of assignment (@climbus)
- #303 Fix inlining into f-string containing quote characters (@lieryan)
- Added scopes for comprehension expressions as part of #293 (@climbus)
- Added support for checking scopes by offset as part of #293 (@climbus)
- #423 Fix `AttributeError: '_ExpressionVisitor' object has no attribute 'defineds'` (@lieryan)


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
