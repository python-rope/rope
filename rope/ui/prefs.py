class Prefs(object):

    def __init__(self):
        self.prefs = {}

    def set(self, key, value):
        """Set the value of `key` preference to `value`."""
        self.prefs[key] = value

    def add(self, key, value):
        """Add an entry to a list preference

        Add `value` to the list of entries for the `key` preference.

        """
        if not key in self.prefs:
            self.prefs[key] = []
        self.prefs[key].append(value)

    def get(self, key, default=None):
        """Get the value of the key preference"""
        return self.prefs.get(key, default)
