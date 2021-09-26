1. Ensure tickets assigned to Milestones are up to date 
2. Update CHANGELOG.md
3. Increment version number in ``rope/__init__.py``
4. Tag the release with the tag annotation containing the release information, e.g. ``git tag -s 0.21.0``
5. Publish to Discussions Announcement
6. ``python3 setup.py sdist``
7. ``twine upload -s dist/rope-$VERSION.tar.gz*``
