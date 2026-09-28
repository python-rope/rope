# Report: DeprecationWarning at `rope/base/project.py:230`

## The warning

```
rope/base/project.py:230: DeprecationWarning: Delete once deprecated functions are gone
```

## What the decoration means

`_init_source_folders()` carries a `@utils.deprecated("Delete once deprecated functions are gone")`
decorator. It was added in 2014 by this commit:

```
2ee332a2 Have deprecated functions in pycore call replacement functions.
  +    @utils.deprecated('Delete once deprecated functions are gone')
   def _init_source_folders(self):
```

This was **not** a deprecation of a user-facing API — `_init_source_folders` is a
private method called from `Project.__init__` (line 230), so the warning fires on
*every* `Project()` construction. It is a self-reminder left in the code: "once the
deprecated wrapper methods in pycore are removed, delete *this decorator*."

## Has the condition been met?

The "deprecated functions" it refers to are the pycore wrappers, e.g.:

- `pycore.py:67` — `get_module` → use `project.get_module`
- `pycore.py:129` — `get_source_folders` → use `project.get_source_folders`
- `pycore.py:220` — `modname` → use `libutils.modname`
- plus `taskhandle.py`, `change_signature.py`, `history.py`, `memorydb.py`

Those **still all exist in this tree** (`git grep "utils.deprecated"`). So by the
original author's own criterion, "the time" hasn't come yet — *unless* removing all
of those pycore wrappers is now part of the plan.

## What can safely be done

**Do not delete `_init_source_folders` itself.** It is live functionality: it reads
the still-documented `source_folders` preference (`prefs.py:92`) and feeds
`_custom_source_folders`, which `project.get_source_folders()` (line 88) returns —
and that is used by `oi/doa.py:61` and `rope/refactor/multiproject.py:34`. Removing
the function would break a supported feature; removing only the decorator costs zero.

Practical options:

1. **Just delete the `@utils.deprecated(...)` decorator** and keep the function.
   It is a private helper with no deprecation story; the decorator only produces
   noise (and it's noise for users: every `Project()` construction warns).
2. **If the deprecated pycore wrappers are also being removed in the same pass** —
   which is what "delete once deprecated functions are gone" literally asks — then
   do both: drop the ~20 `@utils.deprecated` wrappers in `pycore.py`,
   `taskhandle.py`, etc., *and* drop this decorator. But that is an API-breaking
   change for rope consumers and deserves a major bump / changelog entry.

## Recommendation

Option 1 now: remove the decorator, keep the function. That removes the warning
with no behavior change. Treat the pycore wrapper cleanup as a separate
deliberate breaking-change release if it is ever intended.

## Side note

`DeprecationWarning` is ignored by default outside `__main__`. Anyone seeing this
is running with `-W default`, a pytest warning config, or importing rope from
`__main__` — worth keeping in mind when judging whether it is "user-visible"
noise at all.
