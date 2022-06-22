Release Process
===============

1. Ensure tickets assigned to Milestones are up to date 
2. Update CHANGELOG.md
3. Increment version number in ``pyproject.toml``
4. Tag the release with the tag annotation containing the release information, 
   ``python bin/tag-release.py``
5. ``python3 -m build``
6. ``twine upload -s dist/rope-$VERSION.{tar.gz,whl}``
7. Publish to Discussions Announcement
8. Close milestone
