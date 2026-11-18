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

Downstream Fork Releases
------------------------

Local-version releases (a ``+`` label) are distributed as GitHub Release wheel and
source-distribution assets, not uploaded to PyPI. The `version specification`_
prohibits local version identifiers on PyPI. Public upstream releases retain the
existing trusted-publisher workflow.

Run ``make setup fmt check test build`` on the release candidate. The native
``build`` target invokes ``artifact-check`` to verify typed markers and exercise
the installed wheel outside the checkout. After merging and creating the signed,
annotated version tag, create the GitHub Release with both validated artifacts.
The artifact check prints the SHA-256 of each built distribution so a development
candidate can be reviewed by content identity before installation or publication.
The selected artifact version comes from the producer's ``pyproject.toml``,
never from a previously installed distribution in the build environment.
The artifact checker reads that manifest with ``toml``, declared in the development
extra as well as the release extra. Both the producer and the isolated
``wheel[dev]`` consumer install it.
The release workflow downloads those published assets and runs the same
``make artifact-check`` against them; a locally rebuilt wheel is not a substitute
for that published-artifact receipt.

To repeat validation without changing an existing tag or its assets, dispatch the
maintained controller with ``gh workflow run python-publish.yml --ref dc-use
-f release_tag=<version> -f release_commit=<tag-target-sha>``. In this downstream
fork, ``dc-use`` owns the maintained release controller; use the maintained
controller branch when applying this flow in another repository. The recorded full
producer commit pins the checkout, and the job rejects a tag pointing elsewhere.
It reports downloaded asset hashes and validates the published distributions,
rather than building replacements. Setup uses the installed
``uv`` executable: invoking ``python -m uv`` while Make exports a bytecode cache
inside the future virtualenv would create that directory before its safety check.
Native interpreter discovery uses ``uv python find --no-project`` so an ambient
workspace selection cannot impose an unrelated project's Python constraint.

.. _version specification: https://packaging.python.org/en/latest/specifications/version-specifiers/#local-version-identifiers


Release Schedule
================

Rope has a release schedule once a month, usually sometime close to the 15th of
each month. However, this schedule is not a guaranteed date, if there is a
particularly urgent change or if there's not enough pull requests for the
month, there may be additional releases or the release window may be skipped.
