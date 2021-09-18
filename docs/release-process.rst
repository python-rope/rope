1. Increment version number in ``rope/__init__.py``
2. Tag the release with the tag annotation containing the release information, e.g. ``git tag -s 0.21.0``
3. ``python3 setup.py sdist``
4. ``twine upload -s dist/rope-$VERSION.tar.gz*``
