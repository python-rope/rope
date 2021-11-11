1. Ensure tickets assigned to Milestones are up to date 
2. Update CHANGELOG.md
3. Increment version number in ``rope/__init__.py``
4. Tag the release with the tag annotation containing the release information, e.g. ``git tag -s 0.21.0``
5. Push the tag ``git push 0.21.0``
6. ``python3 -m build``
7. ``twine upload -s dist/rope-$VERSION.{tar.gz,whl}``
8. Publish to Discussions Announcement
