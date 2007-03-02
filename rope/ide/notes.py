import re


class Codetags(object):

    def __init__(self):
        self.pattern = re.compile('# ([A-Z!?]{2,10}):')

    def tags(self, source):
        result = []
        for lineno, line in enumerate(source.splitlines(False)):
            match = self.pattern.search(line)
            if match:
                result.append((lineno + 1, line[match.start() + 2:]))
        return result
