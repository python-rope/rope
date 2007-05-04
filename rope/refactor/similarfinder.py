"""This module can be used for finding similar code"""


class SimilarFinder(object):
    """A class for finding similar expressions and statements"""

    def __init__(self, source, start=0, end=None):
        self.source = source
        self.start = start
        self.end = len(self.source)
        if end is not None:
            self.end = end

    def find(self, expression):
        index = self.start
        while index < self.end:
            try:
                index = self.source.index(expression, index, self.end)
                yield (index, index + len(expression))
                index += len(expression)
            except ValueError:
                break
