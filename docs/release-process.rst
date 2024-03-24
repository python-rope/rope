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
3. Close milestone
4. Increment version number in ``pyproject.toml``
5. `git commit && git push`
6. Tag the release with the tag annotation containing the release information,
   ``python bin/tag-release.py``
7. Create Github Release
8. Publish release announcements to GitHub Discussions


Release Schedule
================

Rope has a release schedule once a month, usually sometime close to the 15th of
each month. However, this schedule is not a guaranteed date, if there is a
particularly urgent change or if there's not enough pull requests for the
month, there may be additional releases or the release window may be skipped.
