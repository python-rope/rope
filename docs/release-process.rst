Release Process
===============

1. Ensure tickets assigned to Milestones are up to date 
2. Update CHANGELOG.md
3. Increment version number in ``pyproject.toml``
4. `git commit && git push`
5. Tag the release with the tag annotation containing the release information, 
   ``python bin/tag-release.py``
6. ``python3 -m build``
7. ``twine upload -s dist/rope-$VERSION.{tar.gz,whl}``
8. Publish to Discussions Announcement
9. Close milestone
