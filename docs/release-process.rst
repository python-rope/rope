1. Increment version number in ``rope/__init__.py``
2. Tag the release with the tag annotation containing the release information
3. ``python3 setup.py sdist``
4. ``twine upload -s dist/rope-$VERSION.tar.gz*``
