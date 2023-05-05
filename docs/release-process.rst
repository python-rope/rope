Release Process
===============

Pre-Release
-----------

1. Update :ref:`gha-cache-key.txt <gha-cache-key>`:
   ``pip-compile --extra dev --generate-hashes -o gha-cache-key.txt --resolver=backtracking``

Release
-------

1. Ensure tickets assigned to Milestones are up to date
2. Update ``CHANGELOG.md``
3. Increment version number in ``pyproject.toml``
4. `git commit && git push`
5. Tag the release with the tag annotation containing the release information,
   ``python bin/tag-release.py``
6. ``python3 -m build``
7. ``twine upload -s dist/rope-$VERSION.{tar.gz,whl}``
8. Publish to Discussions Announcement
9. Close milestone


Release Schedule
================

Rope has a release schedule once a month, usually sometime close to the 15th of
each month. However, this schedule is not a guaranteed date, if there is a
particularly urgent change or if there's not enough pull requests for the
month, there may be additional releases or the release window may be skipped.
